"""
BulkUrlImporter — Importación masiva de productos desde URLs
=============================================================
Flujo por producto: datos de coste → validación sobre coste LANDED (producto + envío, convertido a la
divisa de la tienda) → precio psicológico (,99) → verificación determinista → borrador en Shopify con
imágenes y variantes → registro en BD → fila en la hoja Pipeline de Google Sheets.

Regla suprema: no se inventan datos. Cada producto trae SU coste y SU envío; si falta cualquiera de
los dos el producto queda `skipped` con DATA_GAP_REQUEST y no se crea nada en Shopify.

Imágenes: las que indique el usuario (`img=URL`) o, si no hay, las de la página (og:image / JSON-LD).
Variantes: solo las que indique el usuario (`var=Color:Rojo/Azul`). AliExpress y Temu sirven captcha a
los scripts, así que no se intenta deducir variantes de su HTML (sería inventar datos).
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
import urllib.error
import urllib.request
import uuid
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from app.database.connection import DatabaseConnection
from app.services.deterministic_gate import verificar_copy, verificar_validacion_financiera
from app.services.financial_validator import FinancialValidator
from app.services.shopify_client import ShopifyClient

logger = logging.getLogger(__name__)

DOMINIOS = {"aliexpress": "aliexpress.com", "cjdropshipping": "cjdropshipping.com", "temu": "temu.com"}

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
_TITULO_BASURA = re.compile(r"captcha|robot|access denied|verify|just a moment|404|not found", re.I)
_MAX_HTML = 512 * 1024
MAX_IMAGENES = 10
MAX_PRODUCTOS_POR_LOTE = 50

# Descripción neutra: el borrador puede acabar publicado, así que no lleva proveedor, URL de origen
# ni cálculos internos. La ficha real se redacta después con /redactar-ficha-shopify.
DESCRIPCION_BORRADOR = "<p>Borrador pendiente de ficha de producto.</p>"


# ── plataforma ───────────────────────────────────────────────────────────────

def _host(url: str) -> str:
    try:
        p = urlparse(url)
    except ValueError:
        return ""
    return (p.hostname or "").lower() if p.scheme in ("http", "https") else ""


def detectar_plataforma(url: str) -> str:
    """Plataforma por el HOST real de la URL (no por texto: «evil.net/aliexpress.com» no cuenta)."""
    h = _host(url)
    for nombre, dominio in DOMINIOS.items():
        if h == dominio or h.endswith("." + dominio):
            return nombre
    return "desconocida"


def extraer_product_id(url: str, plataforma: str) -> str:
    """Extrae el ID del producto de la URL según la plataforma."""
    if plataforma == "aliexpress":
        m = re.search(r"/item/(\d+)", url)
        return m.group(1) if m else ""
    if plataforma == "cjdropshipping":
        m = re.search(r"[?&]id=([A-Za-z0-9\-]+)", url)
        return m.group(1) if m else ""
    if plataforma == "temu":
        m = re.search(r"-(\d+)\.html", url)
        return m.group(1) if m else ""
    return ""


# ── precio ───────────────────────────────────────────────────────────────────

def precio_psicologico(pvp: float) -> float:
    """Sube al siguiente ,99 sin bajar nunca del PVP calculado (32,40 → 32,99; 33,00 → 33,99)."""
    candidato = math.floor(pvp + 1e-9) + 0.99
    if candidato < pvp - 1e-9:
        candidato += 1
    return round(candidato, 2)


# ── página del producto ──────────────────────────────────────────────────────

class _RedirectSeguro(urllib.request.HTTPRedirectHandler):
    """Solo sigue redirecciones dentro de las plataformas conocidas (evita SSRF por redirección)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if detectar_plataforma(newurl) == "desconocida":
            raise urllib.error.URLError(f"redirección a un host no permitido: {_host(newurl) or newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def obtener_html(url: str) -> str:
    """Descarga la página, solo de plataformas conocidas. '' si no se puede (captcha, red, host ajeno)."""
    if detectar_plataforma(url) == "desconocida":
        return ""
    try:
        opener = urllib.request.build_opener(_RedirectSeguro)
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with opener.open(req, timeout=10) as resp:
            return resp.read(_MAX_HTML).decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"[SCRAPE] No se pudo leer {url}: {e}")
        return ""


class _Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.metas, self.ld = "", {}, []
        self._en_title = self._en_ld = False
        self._buf: List[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._en_title = True
        elif tag == "meta":
            clave = (a.get("property") or a.get("name") or "").lower()
            if clave and a.get("content"):
                self.metas.setdefault(clave, []).append(a["content"].strip())
        elif tag == "script" and "ld+json" in a.get("type", "").lower():
            self._en_ld, self._buf = True, []

    def handle_endtag(self, tag):
        if tag == "title":
            self._en_title = False
        elif tag == "script" and self._en_ld:
            self._en_ld = False
            try:
                self.ld.append(json.loads("".join(self._buf)))
            except ValueError:
                pass

    def handle_data(self, data):
        if self._en_title:
            self.title += data
        elif self._en_ld:
            self._buf.append(data)


def _productos_ld(nodo: Any) -> List[Dict]:
    if isinstance(nodo, list):
        return [p for n in nodo for p in _productos_ld(n)]
    if isinstance(nodo, dict):
        tipos = nodo.get("@type")
        tipos = tipos if isinstance(tipos, list) else [tipos]
        encontrados = [nodo] if "Product" in tipos else []
        return encontrados + _productos_ld(nodo.get("@graph", []))
    return []


def _urls_imagen(valor: Any) -> List[str]:
    if isinstance(valor, str):
        return [valor]
    if isinstance(valor, dict):
        return _urls_imagen(valor.get("url", ""))
    if isinstance(valor, list):
        return [u for v in valor for u in _urls_imagen(v)]
    return []


def imagenes_validas(candidatas: List[str], base: str = "") -> List[str]:
    """Solo http(s), sin duplicados, máximo 10. Resuelve rutas relativas y «//cdn…» contra `base`."""
    salida: List[str] = []
    for c in candidatas:
        u = urljoin(base, (c or "").strip()) if base else (c or "").strip()
        if _host(u) and u not in salida:
            salida.append(u)
    return salida[:MAX_IMAGENES]


def extraer_datos_pagina(html: str, base_url: str = "") -> Dict[str, Any]:
    """{'titulo', 'imagenes'} de una página (JSON-LD Product > og:*). Vacío si es un captcha."""
    if not html:
        return {"titulo": "", "imagenes": []}
    ex = _Extractor()
    try:
        ex.feed(html)
    except Exception as e:                                       # HTML roto: nos quedamos con lo leído
        logger.warning(f"[SCRAPE] HTML mal formado: {e}")
    producto = next(iter(_productos_ld(ex.ld)), {})
    titulo = (str(producto.get("name") or "") or (ex.metas.get("og:title") or [""])[0] or ex.title)
    titulo = re.sub(r"\s+", " ", titulo).strip()
    titulo = re.sub(r"\s*[\|–\-]\s*(AliExpress|Temu|CJDropshipping).*$", "", titulo, flags=re.I)[:200]
    if not titulo or _TITULO_BASURA.search(titulo):
        return {"titulo": "", "imagenes": []}
    imagenes = _urls_imagen(producto.get("image", [])) + ex.metas.get("og:image", []) + ex.metas.get("twitter:image", [])
    return {"titulo": titulo, "imagenes": imagenes_validas(imagenes, base_url)}


def obtener_datos_pagina(url: str) -> Dict[str, Any]:
    return extraer_datos_pagina(obtener_html(url), url)


# ── entrada ──────────────────────────────────────────────────────────────────

def _numero(valor: str) -> Optional[float]:
    try:
        return float(valor.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def _parsear_var(token: str) -> Optional[Tuple[str, List[str]]]:
    nombre, sep, valores = token[4:].partition(":")
    vals = [v.replace("_", " ").strip() for v in valores.split("/") if v.strip()]
    nombre = nombre.replace("_", " ").strip()
    return (nombre, vals) if sep and nombre and vals else None


def parsear_lineas(texto: str) -> List[Dict[str, Any]]:
    """
    Una línea por producto:  URL  coste  envío  [img=URL …]  [var=Opción:valor/valor …]
    Separado por espacios o tabuladores; admite coma decimal. El envío puede ser 0 si el proveedor lo da
    gratis, pero debe escribirse. En `var=` usa «_» para los espacios (`var=Color:Rojo/Azul_marino`).
    Lo que falte queda en None y el importador lo marca como DATA_GAP_REQUEST.
    """
    items: List[Dict[str, Any]] = []
    for linea in texto.splitlines():
        partes = linea.split()
        if not partes:
            continue
        numeros: List[Optional[float]] = []
        imagenes: List[str] = []
        opciones: Dict[str, List[str]] = {}
        error = ""
        for tok in partes[1:]:
            bajo = tok.lower()
            if bajo.startswith("img="):
                imagenes.append(tok[4:])
            elif bajo.startswith("var="):
                var = _parsear_var(tok)
                if var:
                    opciones.setdefault(var[0], []).extend(var[1])
                else:
                    error = f"«{tok}» no es válido: usa var=Color:Rojo/Azul"
            else:
                numeros.append(_numero(tok))
        numeros += [None, None]
        item: Dict[str, Any] = {"url": partes[0], "costo_origen": numeros[0], "costo_envio": numeros[1]}
        if imagenes:
            item["imagenes"] = imagenes
        if opciones:
            item["opciones"] = opciones
        if error:
            item["error_formato"] = error
        items.append(item)
    return items


# ── importador ───────────────────────────────────────────────────────────────

def _subir_a_hoja(producto: Dict[str, Any]) -> None:
    from app.services import google_sheets_live
    google_sheets_live.upsert_producto_pipeline(producto)


class BulkUrlImporter:
    """Importa productos como borradores en Shopify con validación financiera y gate determinista."""

    def __init__(self, db: Optional[DatabaseConnection] = None, shopify: Any = None,
                 pagina_fn: Callable[[str], Dict[str, Any]] = obtener_datos_pagina,
                 hoja_fn: Optional[Callable[[Dict[str, Any]], None]] = None, pausa: float = 0.5):
        self.db = db or DatabaseConnection()
        self.validator = FinancialValidator(self.db)
        self._shopify = shopify
        self._moneda: Optional[str] = None
        self._pagina_fn = pagina_fn
        self._hoja_fn = hoja_fn
        self._pausa = pausa

    # ── API pública ──────────────────────────────────────────────────────────

    def previsualizar(self, items: List[Dict[str, Any]], moneda_costo: str = "USD",
                      precio_psico: bool = True) -> List[Dict]:
        """Valida y calcula el precio de cada producto sin crear nada (ni Shopify, ni BD, ni Sheets)."""
        return self._lote(items, moneda_costo, "", precio_psico, False, False)

    def importar_lote(self, items: List[Dict[str, Any]], moneda_costo: str = "USD", etiqueta_lote: str = "",
                      precio_psico: bool = True, sincronizar_hoja: bool = False) -> List[Dict]:
        """
        Args:
            items: dicts con `url`, `costo_origen`, `costo_envio` y opcionalmente `peso_kg`, `imagenes`, `opciones`.
            moneda_costo: divisa en la que el proveedor da coste y envío (AliExpress/CJ: USD).
            etiqueta_lote: etiqueta Shopify común (p. ej. «test-2026-11») para filtrar o borrar el lote.
            precio_psico: redondea el PVP al siguiente ,99 (nunca por debajo del calculado).
            sincronizar_hoja: escribe cada borrador creado en la pestaña Pipeline de Google Sheets.
        """
        return self._lote(items, moneda_costo, etiqueta_lote, precio_psico, True, sincronizar_hoja)

    # ── interno ──────────────────────────────────────────────────────────────

    def _lote(self, items, moneda_costo, etiqueta_lote, precio_psico, crear, sincronizar_hoja) -> List[Dict]:
        if len(items) > MAX_PRODUCTOS_POR_LOTE:
            raise ValueError(f"Máximo {MAX_PRODUCTOS_POR_LOTE} productos por lote (recibidos {len(items)})")
        resultados = []
        for item in items:
            url = (item.get("url") or "").strip()
            if not url:
                continue
            r = self._importar_uno(url, item, moneda_costo, etiqueta_lote, precio_psico, crear, sincronizar_hoja)
            resultados.append(r)
            if crear and (r["status"] != "skipped" or r.get("guardar")):
                self._guardar_en_bd(r)
            if crear and r["status"] == "success" and self._pausa:
                time.sleep(self._pausa)
        if crear:
            exitosos = sum(1 for r in resultados if r["status"] == "success")
            logger.info(f"[BULK] Lote finalizado: {exitosos}/{len(resultados)} borradores creados")
        return resultados

    def _resultado(self, url: str, plataforma: str, pid: str, status: str, error: Optional[str] = None,
                   draft: Optional[str] = None, validacion: Optional[Dict] = None, guardar: bool = True,
                   **extra: Any) -> Dict:
        validacion = validacion or {}
        return {"url": url, "plataforma": plataforma, "product_id": pid, "status": status,
                "shopify_draft_id": draft, "error": error, "validacion": validacion,
                "pvp": validacion.get("pvp_calculado"), "guardar": guardar, **extra}

    def _cliente(self):
        if self._shopify is None:
            self._shopify = ShopifyClient()
        return self._shopify

    def _moneda_tienda(self) -> str:
        """Divisa real de la tienda; si Shopify no la da, no se asume ninguna."""
        if self._moneda is None:
            moneda = (self._cliente().shop_info() or {}).get("moneda")
            if not moneda:
                raise RuntimeError("No se pudo leer la divisa de la tienda en Shopify")
            self._moneda = str(moneda).upper()
        return self._moneda

    def _ya_importada(self, url: str) -> bool:
        try:
            with self.db.get_connection() as conn:
                return conn.execute(
                    "SELECT 1 FROM importaciones_masivas WHERE url_origen = ? AND status = 'success' LIMIT 1",
                    (url,)).fetchone() is not None
        except Exception as e:
            logger.warning(f"[BULK] No se pudo comprobar duplicados: {e}")
            return False

    def _validar(self, sku: str, item: Dict, costo: float, envio: float, moneda_costo: str,
                 moneda_pvp: str, precio_psico: bool) -> Dict:
        peso = float(item.get("peso_kg") or 0.0)
        v = self.validator.validar_producto(sku, costo, peso, costo_envio=envio,
                                            moneda_costo=moneda_costo, moneda_pvp=moneda_pvp)
        if precio_psico and v.get("validado"):
            # Se revalida con el PVP final: el gate y el multiplicador reflejan lo que se publica
            v = self.validator.validar_producto(sku, costo, peso, pvp_sugerido=precio_psicologico(v["pvp_calculado"]),
                                                costo_envio=envio, moneda_costo=moneda_costo, moneda_pvp=moneda_pvp)
        return v

    def _importar_uno(self, url, item, moneda_costo, etiqueta_lote, precio_psico, crear, sincronizar_hoja) -> Dict:
        plataforma = detectar_plataforma(url)
        pid = extraer_product_id(url, plataforma)
        costo, envio = item.get("costo_origen"), item.get("costo_envio")
        opciones = item.get("opciones") or {}

        def omitir(msg: str, **kw) -> Dict:
            return self._resultado(url, plataforma, pid, "skipped", error=msg, guardar=False, **kw)

        if item.get("error_formato"):
            return omitir(item["error_formato"])
        faltan = [n for n, v in (("coste del producto", costo), ("coste de envío", envio)) if v is None]
        if faltan:
            return omitir(f"DATA_GAP_REQUEST: falta {' y '.join(faltan)} (el multiplicador se mide sobre "
                          f"coste landed; escribe 0 si el envío es gratis)")
        if costo <= 0 or envio < 0:
            return omitir("Coste debe ser > 0 y envío ≥ 0")
        try:
            ShopifyClient.construir_variantes(1.0, opciones)
        except ValueError as e:
            return omitir(str(e))
        if self._ya_importada(url):
            return omitir("Duplicado: esta URL ya tiene un borrador creado")

        try:
            moneda_pvp = self._moneda_tienda()
        except Exception as e:
            return self._resultado(url, plataforma, pid, "error", error=str(e))

        sku = pid or hashlib.md5(url.encode()).hexdigest()[:12]
        validacion = self._validar(sku, item, costo, envio, moneda_costo, moneda_pvp, precio_psico)
        if not validacion.get("validado"):
            return self._resultado(url, plataforma, pid, "skipped", validacion=validacion,
                                   error=validacion.get("nota_auditoria", "No cumple el multiplicador mínimo x2"))
        gate = verificar_validacion_financiera(validacion)
        if not gate["passed"]:
            return self._resultado(url, plataforma, pid, "error", validacion=validacion,
                                   error="Gate determinista: " + "; ".join(gate["violations"]))
        if not crear:
            return self._resultado(url, plataforma, pid, "preview", validacion=validacion, guardar=False,
                                   imagenes=len(item.get("imagenes") or []), variantes=_n_variantes(opciones))

        pagina = self._pagina_fn(url) if plataforma != "desconocida" else {}
        imagenes = imagenes_validas(item.get("imagenes") or []) or (pagina.get("imagenes") or [])
        titulo = pagina.get("titulo") or f"Producto {pid or sku} (revisar título)"
        if not verificar_copy(f"{titulo} {DESCRIPCION_BORRADOR}")["passed"]:
            titulo = f"Producto {pid or sku} (revisar título)"

        tags = ",".join(t for t in ("gem-os", f"origen-{plataforma}", etiqueta_lote.strip()) if t)
        try:
            draft_id = self._cliente().create_draft_product(
                titulo=titulo, descripcion=DESCRIPCION_BORRADOR, precio=validacion["pvp_calculado"],
                imagenes=imagenes, tags=tags, opciones=opciones or None)
        except Exception as e:
            logger.error(f"[BULK] Error creando borrador para {url}: {e}")
            return self._resultado(url, plataforma, pid, "error", error=str(e), validacion=validacion)

        r = self._resultado(url, plataforma, pid, "success", draft=draft_id, validacion=validacion,
                            titulo=titulo, imagenes=len(imagenes), variantes=_n_variantes(opciones),
                            hoja="omitida")
        if sincronizar_hoja:
            r["hoja"] = self._escribir_hoja(r, sku, validacion, item)
        return r

    def _escribir_hoja(self, r: Dict, sku: str, validacion: Dict, item: Dict) -> str:
        """Fila en Pipeline. Un fallo de Sheets no deshace el borrador: se informa y ya."""
        producto = {"sku": sku, "nombre": r["titulo"], "costo_origen": validacion["costo_landed"],
                    "pvp": validacion["pvp_calculado"], "peso_kg": validacion.get("peso_kg", 0),
                    "categoria": f"importación · {r['plataforma']} · borrador {r['shopify_draft_id']}"}
        try:
            (self._hoja_fn or _subir_a_hoja)(producto)
            return "ok"
        except Exception as e:
            logger.warning(f"[BULK] Sheets no actualizado para {sku}: {e}")
            return f"error: {e}"

    def _guardar_en_bd(self, r: Dict):
        try:
            with self.db.get_connection() as conn:
                conn.execute(
                    """INSERT INTO importaciones_masivas
                           (correlation_id, url_origen, plataforma, product_id_externo,
                            shopify_draft_id, status, validacion_financiera, error_msg)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), r["url"], r["plataforma"], r.get("product_id", ""),
                     r.get("shopify_draft_id"), r["status"], json.dumps(r.get("validacion", {})), r.get("error")))
                conn.commit()
        except Exception as e:
            logger.error(f"[BULK] Error guardando en BD: {e}")


def _n_variantes(opciones: Dict[str, List[str]]) -> int:
    n = 1
    for vals in opciones.values():
        n *= len(dict.fromkeys(vals))
    return n
