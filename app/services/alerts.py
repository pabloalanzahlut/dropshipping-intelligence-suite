"""
alerts — centro de alertas con comprobaciones automáticas (sin IA, deterministas).

`evaluar()` revisa el negocio y la propia herramienta y devuelve qué requiere atención.
Cada alerta tiene una CLAVE estable: si el problema sigue, se actualiza (no se duplica); si
desaparece, se marca como resuelta sola. Así el aviso refleja siempre el estado real.

Comprobaciones:
  caja · ROAS · métricas sin registrar · producto que toca cortar · canales rotos (404) o sin
  verificar · transcripciones sin actualizar · copia de seguridad antigua · IA sin configurar.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services import business_metrics, channel_store, product_catalog

NIVELES = {"info": 1, "aviso": 2, "critico": 3}
_LOCK = threading.Lock()


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _a(clave: str, nivel: str, titulo: str, detalle: str = "", enlace: str = "", origen: str = "") -> Dict[str, str]:
    return {"clave": clave, "nivel": nivel, "titulo": titulo, "detalle": detalle, "enlace": enlace, "origen": origen}


def _horas_desde(iso: Optional[str]) -> Optional[float]:
    try:
        return (datetime.now() - datetime.fromisoformat(str(iso)[:19])).total_seconds() / 3600
    except (TypeError, ValueError):
        return None


# ── comprobaciones ───────────────────────────────────────────────────────────

def _negocio(db_path: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    r = business_metrics.resumen(db_path, 7)
    if r["dias_con_datos"] == 0:
        return out                       # sin actividad registrada no hay nada que vigilar
    dias = r["dias_de_caja"]
    if dias is not None and dias < 2:
        out.append(_a("caja_critica", "critico", f"Caja crítica: {dias} días",
                      "Pausa los anuncios y no hagas pedidos nuevos hasta que la pasarela libere pagos.", "/negocio", "negocio"))
    elif dias is not None and dias < 4:
        out.append(_a("caja_baja", "aviso", f"Caja baja: {dias} días",
                      "No escales. Con 2–3 días: pausa ads hasta liberar pagos; con 4–6: reduce el presupuesto un 20 %.", "/negocio", "negocio"))
    if r["caja"] is None:
        out.append(_a("caja_sin_datos", "aviso", "Falta registrar la caja",
                      "Sin la caja no se pueden calcular los días de caja ni recomendar escalar.", "/negocio", "negocio"))
    else:
        h = _horas_desde(r["caja"]["fecha"] + "T23:59:59")
        if h is not None and h > 72:
            out.append(_a("caja_antigua", "aviso", "La caja registrada tiene más de 3 días",
                          "Actualízala: los días de caja se calculan con el último saldo.", "/negocio", "negocio"))
    roas = r["roas"]
    if roas is not None and roas < 1:
        out.append(_a("roas_sangrado", "critico", f"ROAS {roas}×: pierdes dinero",
                      "Por debajo de 1× el anuncio cuesta más de lo que factura. Pausa y revisa.", "/negocio", "negocio"))
    elif roas is not None and roas < 2:
        out.append(_a("roas_bajo", "aviso", f"ROAS {roas}×: por debajo del mínimo de 2×",
                      "El mínimo del curso es 2× medido real. Revisa CPA, producto y creativo.", "/negocio", "negocio"))
    hoy = date.today().isoformat()
    if datetime.now().hour >= 21 and not any(f["fecha"] == hoy for f in business_metrics.listar_metricas(db_path, 1)):
        out.append(_a("metricas_hoy", "info", "Aún no has registrado las métricas de hoy",
                      "Gasto, ingresos y pedidos del día.", "/negocio", "negocio"))
    return out


def _productos(db_path: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    catalogo = product_catalog.listar(db_path)
    if not catalogo:
        out.append(_a("sin_productos", "info", "El catálogo de productos está vacío",
                      "Empieza por Productos → nuevo candidato; cada paso del recorrido comprueba datos reales.",
                      "/productos", "productos"))
    for p in catalogo:
        if p["estado"] not in ("tienda", "escalado"):
            continue
        dec = business_metrics.evaluar_escalado(db_path, p)
        if dec["decision"] == "CORTAR":
            out.append(_a(f"producto_cortar_{p['id']}", "critico", f"{p['nombre']}: toca cortar la campaña",
                          dec["accion"], "/productos", "productos"))
        elif dec["decision"] == "ESCALAR":
            out.append(_a(f"producto_escalar_{p['id']}", "info", f"{p['nombre']}: puedes escalar",
                          dec["accion"], "/productos", "productos"))
    return out


def _canales(db_path: str, config_path: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    canales = [c for c in channel_store.listar(config_path, db_path) if c["activo"]]
    rotos = [c for c in canales if c["ultimo_estado"] == "no_encontrado"]
    for c in rotos:
        out.append(_a(f"canal_404_{channel_store.normalizar_url(c['url'])}", "aviso", f"Canal no encontrado: {c['nombre']}",
                      f"{c['url']} no responde. Corrige la URL o desactívalo.", "/youtube", "canales"))
    sin_verificar = [c for c in canales if not c["ultimo_estado"]]
    if sin_verificar:
        out.append(_a("canales_sin_verificar", "info", f"{len(sin_verificar)} canales sin verificar",
                      "Pulsa «Verificar todos» en YouTube (el mantenimiento semanal también lo hace).", "/youtube", "canales"))
    return out


def _sistema(db_path: str, config_path: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    # Transcripciones
    ruta = Path(config_path).with_name("last_sync.json")
    try:
        ult = json.loads(ruta.read_text(encoding="utf-8"))
        h = _horas_desde(ult.get("fecha_sincronizacion"))
        if h is not None and h > 72:
            out.append(_a("sync_antigua", "aviso", f"Las transcripciones llevan {int(h // 24)} días sin actualizarse",
                          "La sincronización automática no está funcionando: mira Registros.", "/registros", "sistema"))
        if ult.get("limitado"):
            hora = str(ult.get("reintentar_a") or "")[11:16]
            out.append(_a("sync_limitada", "info", "YouTube ha limitado las descargas",
                          "Se reintentará solo " + (f"a partir de las {hora}." if hora else "en el próximo lote automático."),
                          "/transcripciones", "sistema"))
    except Exception:
        out.append(_a("sync_nunca", "info", "Todavía no se han sincronizado transcripciones",
                      "Pulsa «Sincronizar canales» o espera al próximo lote automático.", "/transcripciones", "sistema"))
    # Copia de seguridad
    copias = sorted((Path(db_path).resolve().parent.parent / "backups").glob(f"{Path(db_path).stem}_auto_*.db"))
    if not copias:
        out.append(_a("backup_ninguno", "aviso", "No hay copias de seguridad automáticas",
                      "Se crea una al arrancar el servidor y otra cada noche a las 03:30.", "/registros", "sistema"))
    else:
        h = (datetime.now().timestamp() - copias[-1].stat().st_mtime) / 3600
        if h > 36:
            out.append(_a("backup_antiguo", "aviso", f"La última copia de seguridad tiene {int(h)} horas",
                          "Debería hacerse cada noche: ¿está el servidor encendido por la noche?", "/registros", "sistema"))
    # IA
    estado = {i["id"]: i for i in business_metrics.estado_integraciones()}
    if not estado["openrouter"]["configurada"]:
        out.append(_a("ia_sin_clave", "aviso", "La IA no está configurada",
                      "Falta OPENROUTER_API_KEY en .env: el agente, los copys y la ingesta de la KB no funcionarán.", "/negocio", "sistema"))
    return out


# ── motor ────────────────────────────────────────────────────────────────────

def calcular(db_path: str, config_path: str) -> List[Dict[str, str]]:
    """Alertas que existen AHORA (sin tocar la base de datos)."""
    alertas: List[Dict[str, str]] = []
    for comprobacion in (lambda: _negocio(db_path), lambda: _productos(db_path),
                         lambda: _canales(db_path, config_path), lambda: _sistema(db_path, config_path)):
        try:
            alertas += comprobacion()
        except Exception as exc:       # una comprobación rota no debe tumbar las demás
            alertas.append(_a(f"fallo_comprobacion_{len(alertas)}", "info", "No se pudo hacer una comprobación", str(exc)[:200], "", "sistema"))
    return alertas


def evaluar(db_path: str, config_path: str) -> Dict[str, Any]:
    """Recalcula, guarda las nuevas/vigentes y resuelve las que ya no aplican."""
    with _LOCK:                          # el planificador y la API pueden coincidir
        return _evaluar(db_path, config_path)


def _evaluar(db_path: str, config_path: str) -> Dict[str, Any]:
    ahora = datetime.now().isoformat(timespec="seconds")
    vigentes = calcular(db_path, config_path)
    claves = {a["clave"] for a in vigentes}
    nuevas = 0
    with _db(db_path) as conn:
        for a in vigentes:
            previa = conn.execute("SELECT id, resuelta_at, nivel FROM alertas WHERE clave = ?", (a["clave"],)).fetchone()
            if previa is None:
                conn.execute("INSERT INTO alertas (clave, nivel, titulo, detalle, enlace, origen, creado_at, actualizado_at) "
                             "VALUES (?,?,?,?,?,?,?,?)",
                             (a["clave"], a["nivel"], a["titulo"], a["detalle"], a["enlace"], a["origen"], ahora, ahora))
                nuevas += 1
            else:
                # si reaparece tras estar resuelta, vuelve a ser "no vista"
                reabre = previa["resuelta_at"] is not None or NIVELES[a["nivel"]] > NIVELES.get(previa["nivel"], 1)
                conn.execute("UPDATE alertas SET nivel=?, titulo=?, detalle=?, enlace=?, origen=?, actualizado_at=?, "
                             "resuelta_at=NULL" + (", vista_at=NULL, creado_at=?" if reabre else "") + " WHERE id=?",
                             (a["nivel"], a["titulo"], a["detalle"], a["enlace"], a["origen"], ahora)
                             + ((ahora,) if reabre else ()) + (previa["id"],))
                nuevas += 1 if reabre else 0
        activas = [r["clave"] for r in conn.execute("SELECT clave FROM alertas WHERE resuelta_at IS NULL")]
        for clave in activas:
            if clave not in claves:
                conn.execute("UPDATE alertas SET resuelta_at = ? WHERE clave = ?", (ahora, clave))
        conn.commit()
    return {"vigentes": len(vigentes), "nuevas": nuevas}


def listar(db_path: str, incluir_resueltas: bool = False, limite: int = 50) -> Dict[str, Any]:
    sql = "SELECT * FROM alertas" + ("" if incluir_resueltas else " WHERE resuelta_at IS NULL")
    sql += " ORDER BY CASE nivel WHEN 'critico' THEN 3 WHEN 'aviso' THEN 2 ELSE 1 END DESC, actualizado_at DESC LIMIT ?"
    with _db(db_path) as conn:
        items = [dict(r) for r in conn.execute(sql, (limite,))]
    activas = [a for a in items if not a["resuelta_at"]]
    return {"items": items,
            "sin_ver": sum(1 for a in activas if not a["vista_at"]),
            "criticas": sum(1 for a in activas if a["nivel"] == "critico"),
            "total_activas": len(activas)}


def marcar_vista(db_path: str, alerta_id: Optional[int] = None) -> int:
    """Marca como vista una alerta (o todas). Seguirá activa mientras el problema exista."""
    ahora = datetime.now().isoformat(timespec="seconds")
    with _db(db_path) as conn:
        if alerta_id is None:
            n = conn.execute("UPDATE alertas SET vista_at = ? WHERE resuelta_at IS NULL AND vista_at IS NULL", (ahora,)).rowcount
        else:
            n = conn.execute("UPDATE alertas SET vista_at = ? WHERE id = ? AND vista_at IS NULL", (ahora, alerta_id)).rowcount
        conn.commit()
    return n
