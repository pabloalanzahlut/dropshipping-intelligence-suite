"""
ShopifyClient — Cliente de la Admin API de Shopify para GEM OS
==============================================================

Dos usos:
  · LECTURA (estadísticas y contexto del agente): pedidos, variantes con su coste y datos de la
    tienda, por la GraphQL Admin API. Solo necesita scopes de lectura.
  · ESCRITURA (borradores): create_draft_product, por REST /products.json (necesita write_products).

Autenticación — según lo que haya en .env:
  A) SHOPIFY_CLIENT_ID + secreto de la app → «client credentials grant»: el cliente canjea el par
     por un token de 24 h y lo renueva solo. El secreto puede ir en SHOPIFY_CLIENT_SECRET o, como
     hasta ahora, en SHOPIFY_ACCESS_TOKEN cuando empieza por «shpss_» (eso ES un secreto de app,
     no un token de Admin API: enviado como token, Shopify lo rechaza con 401).
  B) SHOPIFY_ACCESS_TOKEN «shpat_…» (app personalizada clásica) → se usa tal cual.

El cliente nunca devuelve ni registra el secreto ni el token. Para pruebas se inyecta `transporte`
(sin red); para uso real se usa urllib.
"""
from __future__ import annotations

import json
import logging
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Tuple

logger = logging.getLogger(__name__)

API_VERSION_POR_DEFECTO = "2026-10"
SCOPES_NECESARIOS = ("read_orders", "read_products")
SCOPES_OPCIONALES = {
    "read_inventory": "coste unitario de las variantes (margen real por producto)",
    "read_all_orders": "pedidos de más de 60 días",
}

Transporte = Callable[[str, str, Dict[str, str], Optional[bytes], int], Tuple[int, Dict[str, str], str]]


class ShopifyError(RuntimeError):
    """Error de Shopify con un código estable (para la UI) y un mensaje en español."""

    def __init__(self, codigo: str, mensaje: str, http: Optional[int] = None):
        super().__init__(mensaje)
        self.codigo = codigo
        self.http = http


# ── credenciales ─────────────────────────────────────────────────────────────

def normalizar_tienda(valor: str) -> str:
    """«https://Mi-Tienda.myshopify.com/admin» o «mi-tienda» → «mi-tienda.myshopify.com»."""
    t = re.sub(r"^https?://", "", (valor or "").strip(), flags=re.I)
    t = t.split("/")[0].strip().lower()
    if t and "." not in t:
        t += ".myshopify.com"
    return t


def credenciales(env: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    """Qué credenciales hay y cómo se usarán. Uso interno: incluye el secreto."""
    env = os.environ if env is None else env
    tienda = normalizar_tienda(env.get("SHOPIFY_STORE_URL", ""))
    client_id = (env.get("SHOPIFY_CLIENT_ID") or "").strip()
    secreto = (env.get("SHOPIFY_CLIENT_SECRET") or "").strip()
    acceso = (env.get("SHOPIFY_ACCESS_TOKEN") or "").strip()
    token = ""
    if acceso.startswith("shpss_"):
        secreto = secreto or acceso
    elif acceso and not acceso.upper().startswith("PENDIENTE"):
        token = acceso

    faltan: List[str] = []
    problema = ""
    if not tienda:
        faltan.append("SHOPIFY_STORE_URL")
    elif not tienda.endswith(".myshopify.com"):
        problema = (f"SHOPIFY_STORE_URL debe ser el dominio «.myshopify.com» de la tienda "
                    f"(no el dominio propio «{tienda}»).")
    if token:
        modo = "token"
    elif secreto:
        modo = "client_credentials"
        if not client_id:
            faltan.append("SHOPIFY_CLIENT_ID")
            if acceso.startswith("shpss_"):
                problema = ("SHOPIFY_ACCESS_TOKEN contiene el secreto de la app («shpss_…»), no un token de "
                            "Admin API. Añade SHOPIFY_CLIENT_ID (Dev Dashboard → tu app → Configuración) y "
                            "GEM OS canjeará el par por un token automáticamente.")
    else:
        modo = None
        faltan += ["SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET"]
    return {"tienda": tienda, "modo": modo, "client_id": client_id, "secreto": secreto, "token": token,
            "faltan": faltan, "problema": problema, "configurada": not faltan and not problema}


def estado_credenciales(env: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    """Versión pública de credenciales(): nunca incluye secretos ni tokens."""
    c = credenciales(env)
    return {"tienda": c["tienda"], "modo": c["modo"], "faltan": c["faltan"], "aviso": c["problema"],
            "configurada": c["configurada"]}


# ── transporte ───────────────────────────────────────────────────────────────

def _transporte_urllib(metodo: str, url: str, cabeceras: Dict[str, str], cuerpo: Optional[bytes],
                       timeout: int) -> Tuple[int, Dict[str, str], str]:
    req = urllib.request.Request(url, data=cuerpo, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
        motivo = getattr(e, "reason", e)
        raise ShopifyError("red", f"No se pudo conectar con Shopify: {motivo}") from e


def _json(texto: str) -> Dict[str, Any]:
    try:
        d = json.loads(texto or "{}")
        return d if isinstance(d, dict) else {}
    except ValueError:
        return {}


def _numero_gid(gid: Optional[str]) -> str:
    """«gid://shopify/Order/123» → «123»."""
    return str(gid or "").rsplit("/", 1)[-1]


def _importe(conj: Optional[Dict[str, Any]]) -> float:
    try:
        return float(((conj or {}).get("shopMoney") or {}).get("amount") or 0)
    except (TypeError, ValueError):
        return 0.0


# ── consultas GraphQL ────────────────────────────────────────────────────────

_Q_PEDIDOS = """
query Pedidos($cursor: String, $n: Int!, $q: String) {
  orders(first: $n, after: $cursor, query: $q, sortKey: CREATED_AT) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id name createdAt cancelledAt sourceName
      displayFinancialStatus displayFulfillmentStatus
      totalPriceSet { shopMoney { amount currencyCode } }
      subtotalPriceSet { shopMoney { amount } }
      totalDiscountsSet { shopMoney { amount } }
      totalShippingPriceSet { shopMoney { amount } }
      totalTaxSet { shopMoney { amount } }
      totalRefundedSet { shopMoney { amount } }
      shippingAddress { countryCodeV2 }
      lineItems(first: 10) {
        pageInfo { hasNextPage }
        nodes {
          id title sku quantity
          originalUnitPriceSet { shopMoney { amount } }
          variant { id }
        }
      }
    }
  }
}
"""

_Q_VARIANTES = """
query Variantes($cursor: String, $n: Int!) {
  productVariants(first: $n, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id sku title price inventoryQuantity
      product { id title status vendor }
      %s
    }
  }
}
"""
_CAMPO_COSTE = "inventoryItem { unitCost { amount currencyCode } }"


class ShopifyClient:
    """Cliente de la Admin API de Shopify (lectura GraphQL + borradores REST)."""

    def __init__(self, env: Optional[Mapping[str, str]] = None, transporte: Optional[Transporte] = None,
                 dormir: Callable[[float], None] = time.sleep):
        self._cred = credenciales(env)
        if not self._cred["configurada"]:
            detalle = self._cred["problema"] or ("Faltan en .env: " + ", ".join(self._cred["faltan"]))
            raise EnvironmentError(f"Shopify no está configurado. {detalle}")
        self.tienda: str = self._cred["tienda"]
        version = (env or os.environ).get("SHOPIFY_API_VERSION") or API_VERSION_POR_DEFECTO
        self.version: str = version.strip()
        self._base = f"https://{self.tienda}/admin/api/{self.version}"
        self._tx: Transporte = transporte or _transporte_urllib
        self._dormir = dormir
        self._lock = threading.Lock()
        self._tok = self._cred["token"]
        self._tok_exp = float("inf") if self._tok else 0.0
        self._scope_token: List[str] = []
        self.avisos: List[str] = []

    # ── token ────────────────────────────────────────────────────────────────

    def _token(self, forzar: bool = False) -> str:
        if self._cred["modo"] == "token":
            return self._tok
        with self._lock:
            if not forzar and self._tok and time.time() < self._tok_exp - 300:
                return self._tok
            cuerpo = urllib.parse.urlencode({
                "grant_type": "client_credentials", "client_id": self._cred["client_id"],
                "client_secret": self._cred["secreto"]}).encode()
            st, _, txt = self._tx(
                "POST", f"https://{self.tienda}/admin/oauth/access_token",
                {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}, cuerpo, 20)
            datos = _json(txt)
            if st != 200 or not datos.get("access_token"):
                raise self._error_oauth(st, datos)
            self._tok = datos["access_token"]
            self._tok_exp = time.time() + int(datos.get("expires_in") or 86399)
            self._scope_token = [s.strip() for s in str(datos.get("scope") or "").split(",") if s.strip()]
            return self._tok

    @staticmethod
    def _error_oauth(http: int, datos: Dict[str, Any]) -> ShopifyError:
        codigo = str(datos.get("error") or "")
        if codigo == "shop_not_permitted":
            return ShopifyError(
                "organizacion", "Shopify no permite este método en esta tienda: la app (Dev Dashboard) y la "
                "tienda deben pertenecer a la misma organización, y la app debe estar instalada en la tienda.", http)
        if codigo in ("invalid_client", "unauthorized_client") or http in (400, 401, 403):
            return ShopifyError("auth", "Shopify rechazó el Client ID / secreto. Revisa SHOPIFY_CLIENT_ID y el "
                                "secreto de la app (Dev Dashboard → tu app → Configuración).", http)
        if http == 404:
            return ShopifyError("tienda", "Shopify no encuentra esa tienda. Revisa SHOPIFY_STORE_URL.", http)
        return ShopifyError("http", f"Shopify respondió HTTP {http} al pedir el token.", http)

    # ── peticiones ───────────────────────────────────────────────────────────

    def _llamar(self, metodo: str, url: str, payload: Optional[dict] = None) -> str:
        cuerpo = json.dumps(payload).encode() if payload is not None else None
        refrescado = False
        st, hdr, txt = 0, {}, ""
        for intento in range(5):
            cab = {"X-Shopify-Access-Token": self._token(), "Content-Type": "application/json",
                   "Accept": "application/json"}
            st, hdr, txt = self._tx(metodo, url, cab, cuerpo, 30)
            if st == 401 and self._cred["modo"] == "client_credentials" and not refrescado:
                self._token(forzar=True)
                refrescado = True
                continue
            if st == 429 or st in (502, 503, 504):
                try:
                    espera = float({k.lower(): v for k, v in hdr.items()}.get("retry-after", 1.5 * (intento + 1)))
                except ValueError:
                    espera = 1.5 * (intento + 1)
                self._dormir(min(espera, 20))
                continue
            break
        if st >= 400:
            raise self._error_http(st, txt)
        return txt

    @staticmethod
    def _error_http(st: int, txt: str) -> ShopifyError:
        if st == 401:
            return ShopifyError("auth", "Shopify rechazó el token (HTTP 401). Si usas SHOPIFY_ACCESS_TOKEN, debe "
                                "ser un token de Admin API («shpat_…»).", st)
        if st == 402:
            return ShopifyError("plan", "La tienda tiene el plan vencido o congelado (HTTP 402): Shopify no "
                                "permite usar la API hasta reactivar el plan.", st)
        if st == 403:
            return ShopifyError("permiso", "La app no tiene permiso para esto (HTTP 403). Revisa los scopes de la "
                                "app y que esté instalada en la tienda.", st)
        if st == 404:
            return ShopifyError("tienda", "Shopify no encuentra la tienda o el recurso (HTTP 404).", st)
        return ShopifyError("http", f"Shopify respondió HTTP {st}: {(txt or '')[:200]}", st)

    def graphql(self, consulta: str, variables: Optional[dict] = None) -> Dict[str, Any]:
        url = f"{self._base}/graphql.json"
        for intento in range(6):
            datos = _json(self._llamar("POST", url, {"query": consulta, "variables": variables or {}}))
            errores = [e for e in (datos.get("errors") or []) if isinstance(e, dict)]
            if not errores:
                return datos.get("data") or {}
            codigos = {(e.get("extensions") or {}).get("code") for e in errores}
            if "THROTTLED" in codigos:
                self._dormir(1.5 * (intento + 1))
                continue
            mensaje = "; ".join(str(e.get("message", "")) for e in errores)[:300]
            if "MAX_COST_EXCEEDED" in codigos:
                raise ShopifyError("coste", f"La consulta es demasiado costosa para Shopify: {mensaje}")
            if "ACCESS_DENIED" in codigos:
                raise ShopifyError("acceso", f"Falta un scope de la app: {mensaje}")
            raise ShopifyError("graphql", f"Shopify devolvió un error: {mensaje}")
        raise ShopifyError("throttle", "Shopify limita la velocidad de las peticiones; reintenta en un minuto.")

    # ── lectura ──────────────────────────────────────────────────────────────

    def shop_info(self) -> Dict[str, Any]:
        d = self.graphql("{ shop { name myshopifyDomain currencyCode ianaTimezone plan { displayName } } }")
        s = d.get("shop") or {}
        return {"nombre": s.get("name"), "dominio": s.get("myshopifyDomain"), "moneda": s.get("currencyCode"),
                "zona_horaria": s.get("ianaTimezone"), "plan": (s.get("plan") or {}).get("displayName")}

    def scopes(self) -> List[str]:
        try:
            d = self.graphql("{ currentAppInstallation { accessScopes { handle } } }")
            return sorted(s["handle"] for s in (d.get("currentAppInstallation") or {}).get("accessScopes", []))
        except ShopifyError:
            return sorted(self._scope_token)

    def iter_pedidos(self, desde_iso: str) -> Iterator[Dict[str, Any]]:
        """Pedidos creados desde `desde_iso` (UTC), más antiguos primero, normalizados."""
        n, cursor = 20, None
        filtro = f"created_at:>='{desde_iso}' status:any"
        while True:
            try:
                d = self.graphql(_Q_PEDIDOS, {"cursor": cursor, "n": n, "q": filtro})
            except ShopifyError as e:
                if e.codigo == "coste" and n > 5:
                    n = max(5, n // 2)
                    continue
                raise
            conj = d.get("orders") or {}
            for nodo in conj.get("nodes", []):
                yield self._pedido(nodo)
            info = conj.get("pageInfo") or {}
            if not info.get("hasNextPage"):
                return
            cursor = info.get("endCursor")

    def iter_variantes(self) -> Iterator[Dict[str, Any]]:
        """Todas las variantes con su producto y, si el scope lo permite, su coste unitario."""
        con_coste, n, cursor = True, 100, None
        while True:
            consulta = _Q_VARIANTES % (_CAMPO_COSTE if con_coste else "")
            try:
                d = self.graphql(consulta, {"cursor": cursor, "n": n})
            except ShopifyError as e:
                if e.codigo == "acceso" and con_coste:
                    con_coste = False
                    self.avisos.append("La app no tiene el scope read_inventory: no se puede leer el coste "
                                       "unitario de las variantes, así que el margen real no se calcula con Shopify.")
                    continue
                if e.codigo == "coste" and n > 10:
                    n = max(10, n // 2)
                    continue
                raise
            conj = d.get("productVariants") or {}
            for v in conj.get("nodes", []):
                prod = v.get("product") or {}
                coste = (((v.get("inventoryItem") or {}).get("unitCost")) or {}).get("amount")
                yield {
                    "variante_id": _numero_gid(v.get("id")), "producto_id": _numero_gid(prod.get("id")),
                    "producto": prod.get("title") or "", "estado": (prod.get("status") or "").lower(),
                    "vendor": prod.get("vendor") or "", "sku": v.get("sku") or "", "titulo": v.get("title") or "",
                    "precio": float(v.get("price") or 0), "stock": v.get("inventoryQuantity"),
                    "coste": float(coste) if coste not in (None, "") else None,
                }
            info = conj.get("pageInfo") or {}
            if not info.get("hasNextPage"):
                return
            cursor = info.get("endCursor")

    @staticmethod
    def _pedido(n: Dict[str, Any]) -> Dict[str, Any]:
        lineas_conj = n.get("lineItems") or {}
        lineas = []
        for i, li in enumerate(lineas_conj.get("nodes", [])):
            lineas.append({
                "idx": i, "titulo": li.get("title") or "", "sku": li.get("sku") or "",
                "cantidad": int(li.get("quantity") or 0), "precio_unit": _importe(li.get("originalUnitPriceSet")),
                "variante_id": _numero_gid((li.get("variant") or {}).get("id")) if li.get("variant") else "",
            })
        total = (n.get("totalPriceSet") or {}).get("shopMoney") or {}
        return {
            "pedido_id": _numero_gid(n.get("id")), "nombre": n.get("name") or "",
            "creado_at": n.get("createdAt") or "", "cancelado_at": n.get("cancelledAt"),
            "moneda": total.get("currencyCode") or "", "total": _importe(n.get("totalPriceSet")),
            "subtotal": _importe(n.get("subtotalPriceSet")), "descuentos": _importe(n.get("totalDiscountsSet")),
            "envio": _importe(n.get("totalShippingPriceSet")), "impuestos": _importe(n.get("totalTaxSet")),
            "reembolsado": _importe(n.get("totalRefundedSet")),
            "estado_pago": n.get("displayFinancialStatus") or "", "estado_envio": n.get("displayFulfillmentStatus") or "",
            "pais": (n.get("shippingAddress") or {}).get("countryCodeV2") or "", "canal": n.get("sourceName") or "",
            "unidades": sum(l["cantidad"] for l in lineas), "lineas": lineas,
            "lineas_incompletas": bool((lineas_conj.get("pageInfo") or {}).get("hasNextPage")),
        }

    # ── escritura (borradores) ───────────────────────────────────────────────

    def _rest(self, metodo: str, ruta: str, payload: Optional[dict] = None) -> dict:
        return _json(self._llamar(metodo, f"{self._base}{ruta}", payload))

    MAX_OPCIONES = 3
    MAX_VARIANTES = 100

    @classmethod
    def _variantes(cls, precio: float, opciones: Optional[Dict[str, List[str]]]) -> Tuple[List[dict], List[dict]]:
        """(options, variants) del payload. Sin opciones: una única variante «Default Title»."""
        base = {"price": f"{precio:.2f}", "inventory_management": None}
        if not opciones:
            return [], [base]
        if len(opciones) > cls.MAX_OPCIONES:
            raise ValueError(f"Shopify admite como máximo {cls.MAX_OPCIONES} opciones por producto")
        nombres = list(opciones)
        combinaciones: List[Tuple[str, ...]] = [()]
        for n in nombres:
            valores = list(dict.fromkeys(v for v in opciones[n] if v))
            if not valores:
                raise ValueError(f"La opción «{n}» no tiene valores")
            combinaciones = [c + (v,) for c in combinaciones for v in valores]
        if len(combinaciones) > cls.MAX_VARIANTES:
            raise ValueError(f"{len(combinaciones)} variantes: el máximo por importación es {cls.MAX_VARIANTES}")
        options = [{"name": n} for n in nombres]
        variants = [{**base, **{f"option{i + 1}": v for i, v in enumerate(c)}} for c in combinaciones]
        return options, variants

    def create_draft_product(self, titulo: str, descripcion: str, precio: float,
                             imagenes: list[str] | None = None,
                             vendor: str = "GEM OS Import",
                             tags: str = "",
                             opciones: Optional[Dict[str, List[str]]] = None) -> str:
        """Crea un producto como borrador en Shopify (necesita el scope write_products).

        `opciones`: {«Color»: [«Rojo», «Azul»], …}, hasta 3 opciones; se crea una variante por combinación,
        todas al mismo precio. Las imágenes las descarga Shopify desde la URL (máximo 10).

        Returns:
            ID del producto creado (string)
        """
        options, variants = self._variantes(precio, opciones)
        payload = {
            "product": {
                "title": titulo,
                "body_html": descripcion,
                "vendor": vendor,
                "tags": tags,
                "status": "draft",
                "variants": variants,
            }
        }
        if options:
            payload["product"]["options"] = options
        if imagenes:
            payload["product"]["images"] = [{"src": url} for url in imagenes[:10]]

        resp = self._rest("POST", "/products.json", payload)
        product_id = str(resp["product"]["id"])
        logger.info(f"[SHOPIFY] Borrador creado: id={product_id} titulo='{titulo}' variantes={len(variants)}")
        return product_id

    def eliminar_producto(self, product_id: str) -> None:
        """Borra un producto (necesita write_products). Úsalo solo con productos creados por GEM OS."""
        self._rest("DELETE", f"/products/{product_id}.json")

    def get_product(self, product_id: str) -> dict:
        """Obtiene metadatos de un producto existente."""
        return self._rest("GET", f"/products/{product_id}.json").get("product", {})
