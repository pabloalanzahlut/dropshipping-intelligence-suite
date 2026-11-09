"""
SettingsPanel — Configuración: claves de tus agentes e integraciones, avisos y carpeta de datos.

Las claves se guardan con `app.config.secrets_store` en `%APPDATA%\\GEM_OS_Suite\\.env` (en el .exe)
o en el `.env` del proyecto (desarrollo): nunca dentro del .exe ni de git. Aquí solo se muestran
«configurada / falta» y los 4 últimos caracteres; el valor completo no se vuelve a enseñar.
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional

from app.config import runtime_setup, secrets_store
from app.config.path_manager import PathManager
from app.services import business_metrics
from app.ui.components.panel_kit import (
    BG_CARD, BG_TERTIARY, COLOR_ERROR, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS, COLOR_WARNING,
    FONT_BODY, FONT_SECTION, FONT_SM, PanelBase, TXT, TXT_2, TXT_3, boton, etiqueta, tarjeta,
)

# Variables útiles que no están en la lista de integraciones
_EXTRA = [
    ("GEM_OS_PASSWORD", "Contraseña de la web (opcional)", "Si la defines, el panel web pide contraseña."),
    ("FREELLM_API_KEY", "FreeLLMAPI (opcional)", "Pasarela alternativa de modelos."),
    ("ANTHROPIC_API_KEY", "Anthropic directa (opcional)", "Solo si has comprado créditos de API."),
]
_VERSION = "GEM OS 3.7"


class SettingsPanel(PanelBase):
    def __init__(self, parent, db_manager=None, al_cambiar_claves: Optional[Callable[[], None]] = None,
                 primer_arranque: bool = False, **kw):
        super().__init__(parent, db_manager=db_manager, titulo="⚙️ Configuración",
                         subtitulo="Claves de tus agentes, avisos y dónde se guardan tus datos. "
                                   "Los cambios se aplican al momento, sin reiniciar.", **kw)
        self._al_cambiar = al_cambiar_claves
        self._campos: Dict[str, tk.StringVar] = {}
        self._entradas: List[ttk.Entry] = []
        self._estado_vars: Dict[str, tk.Label] = {}
        self._mostrar = tk.BooleanVar(value=False)
        if primer_arranque:
            self._banner()
        self._construir_claves()
        self._construir_avisos()
        self._construir_datos()
        self._construir_acerca()
        self._refrescar_estado()

    # ── bloques ──────────────────────────────────────────────────────────────

    def _banner(self) -> None:
        caja = tk.Frame(self.cuerpo, bg="#2a2410", highlightthickness=1, highlightbackground=COLOR_WARNING)
        caja.pack(fill=tk.X, pady=(0, 12))
        tk.Label(caja, text="👋 Primer arranque: pega tu clave de OpenRouter para activar tus agentes.",
                 font=FONT_BODY, fg=COLOR_WARNING, bg="#2a2410", anchor="w", justify=tk.LEFT,
                 wraplength=760).pack(fill=tk.X, padx=12, pady=(10, 2))
        tk.Label(caja, text="Sin clave el programa funciona en modo offline (plantillas locales, caché de la KB). "
                            "La clave se guarda solo en tu carpeta de usuario, fuera del programa.",
                 font=FONT_SM, fg=TXT_2, bg="#2a2410", anchor="w", justify=tk.LEFT,
                 wraplength=760).pack(fill=tk.X, padx=12, pady=(0, 10))

    def _construir_claves(self) -> None:
        c = tarjeta(self.cuerpo, "🔑 Claves e integraciones", COLOR_PRIMARY)
        etiqueta(c, f"Se guardan en: {secrets_store.ruta_env_escritura()}", "tenue", wrap=760).pack(fill=tk.X, pady=(0, 8))
        grupos = [(n, p, v, para) for _id, n, v, para in business_metrics._INTEGRACIONES for p in [_id]]
        for nombre, ident, variables, para in grupos:
            self._fila_grupo(c, nombre, para, variables, ident)
        for var, nombre, para in _EXTRA:
            self._fila_grupo(c, nombre, para, [var], var.lower())

        barra = tk.Frame(c, bg=BG_CARD)
        barra.pack(fill=tk.X, pady=(10, 0))
        boton(barra, "💾 Guardar cambios", self._guardar, COLOR_SUCCESS).pack(side=tk.LEFT)
        ttk.Checkbutton(barra, text="Mostrar lo que escribo", variable=self._mostrar,
                        command=self._alternar_visibilidad).pack(side=tk.LEFT, padx=12)
        self._probar_btn = boton(barra, "🔌 Probar OpenRouter", self._probar_openrouter, COLOR_SECONDARY)
        self._probar_btn.pack(side=tk.RIGHT)
        self._resultado = etiqueta(c, "", "suave", wrap=760)
        self._resultado.pack(fill=tk.X, pady=(6, 0))

        # Otra variable (p. ej. SHOPIFY_CLIENT_ID) sin tocar archivos
        tk.Frame(c, height=1, bg=BG_TERTIARY).pack(fill=tk.X, pady=10)
        etiqueta(c, "Otra variable de entorno (avanzado)", "suave").pack(fill=tk.X)
        fila = tk.Frame(c, bg=BG_CARD)
        fila.pack(fill=tk.X, pady=4)
        self._otra_nombre = tk.StringVar()
        self._otra_valor = tk.StringVar()
        ttk.Entry(fila, textvariable=self._otra_nombre, width=28).pack(side=tk.LEFT)
        tk.Label(fila, text="=", fg=TXT_3, bg=BG_CARD).pack(side=tk.LEFT, padx=4)
        e = ttk.Entry(fila, textvariable=self._otra_valor, width=36, show="•")
        e.pack(side=tk.LEFT)
        self._entradas.append(e)
        boton(fila, "Añadir", self._guardar_otra, COLOR_PRIMARY).pack(side=tk.LEFT, padx=8)

    def _fila_grupo(self, padre, nombre: str, para: str, variables: List[str], ident: str) -> None:
        marco = tk.Frame(padre, bg=BG_CARD, highlightthickness=1, highlightbackground=BG_TERTIARY)
        marco.pack(fill=tk.X, pady=3)
        cab = tk.Frame(marco, bg=BG_CARD)
        cab.pack(fill=tk.X, padx=10, pady=(6, 0))
        tk.Label(cab, text=nombre, font=FONT_SECTION, fg=TXT, bg=BG_CARD).pack(side=tk.LEFT)
        estado = tk.Label(cab, text="", font=FONT_SM, bg=BG_CARD)
        estado.pack(side=tk.RIGHT)
        self._estado_vars[ident] = estado
        etiqueta(marco, para, "tenue", wrap=740).pack(fill=tk.X, padx=10)
        for var in variables:
            f = tk.Frame(marco, bg=BG_CARD)
            f.pack(fill=tk.X, padx=10, pady=3)
            tk.Label(f, text=var, font=("Consolas", 9), fg=TXT_2, bg=BG_CARD, width=30, anchor="w").pack(side=tk.LEFT)
            v = tk.StringVar()
            self._campos[var] = v
            ent = ttk.Entry(f, textvariable=v, width=44, show="•")
            ent.pack(side=tk.LEFT, padx=(0, 8))
            self._entradas.append(ent)
            actual = tk.Label(f, text="", font=FONT_SM, fg=TXT_3, bg=BG_CARD, width=16, anchor="w")
            actual.pack(side=tk.LEFT)
            setattr(self, f"_act_{var}", actual)
            boton(f, "Quitar", lambda n=var: self._quitar(n), BG_TERTIARY, TXT_2).pack(side=tk.LEFT)
        marco._variables = variables

    def _construir_avisos(self) -> None:
        c = tarjeta(self.cuerpo, "🔔 Avisos fuera de la app", COLOR_WARNING)
        etiqueta(c, "Notificación de Windows y, si defines MAKE_WEBHOOK_ALERTAS arriba, email/Telegram "
                    "por Make. Solo avisa el servidor (este programa lo arranca por ti).", "suave", wrap=760).pack(fill=tk.X)
        fila = tk.Frame(c, bg=BG_CARD)
        fila.pack(fill=tk.X, pady=8)
        self._av_on = tk.BooleanVar(value=os.getenv("GEM_OS_AVISOS", "1") != "0")
        ttk.Checkbutton(fila, text="Avisos activados", variable=self._av_on).pack(side=tk.LEFT)
        tk.Label(fila, text="Nivel mínimo:", fg=TXT_2, bg=BG_CARD, font=FONT_SM).pack(side=tk.LEFT, padx=(16, 4))
        self._av_nivel = tk.StringVar(value=os.getenv("GEM_OS_AVISOS_NIVEL", "aviso"))
        ttk.Combobox(fila, textvariable=self._av_nivel, values=["info", "aviso", "critico"], width=9,
                     state="readonly").pack(side=tk.LEFT)
        tk.Label(fila, text="Silencio (inicio-fin):", fg=TXT_2, bg=BG_CARD, font=FONT_SM).pack(side=tk.LEFT, padx=(16, 4))
        self._av_silencio = tk.StringVar(value=os.getenv("GEM_OS_AVISOS_SILENCIO", "23-7"))
        ttk.Entry(fila, textvariable=self._av_silencio, width=7).pack(side=tk.LEFT)
        botones = tk.Frame(c, bg=BG_CARD)
        botones.pack(fill=tk.X)
        boton(botones, "💾 Guardar avisos", self._guardar_avisos, COLOR_SUCCESS).pack(side=tk.LEFT)
        boton(botones, "📨 Enviar aviso de prueba", self._probar_avisos, COLOR_SECONDARY).pack(side=tk.LEFT, padx=8)
        self._av_res = etiqueta(c, "", "suave", wrap=760)
        self._av_res.pack(fill=tk.X, pady=(6, 0))

    def _construir_datos(self) -> None:
        c = tarjeta(self.cuerpo, "🗂 Tus datos", COLOR_SECONDARY)
        rutas = PathManager.get_paths()
        for nombre, ruta in (("Datos y base de datos", rutas["data"]), ("Copias de seguridad", rutas["backups"]),
                             ("Registros", rutas["logs"]), ("Claves (.env)", secrets_store.ruta_env_escritura().parent)):
            fila = tk.Frame(c, bg=BG_CARD)
            fila.pack(fill=tk.X, pady=2)
            tk.Label(fila, text=nombre, font=FONT_SM, fg=TXT_2, bg=BG_CARD, width=22, anchor="w").pack(side=tk.LEFT)
            tk.Label(fila, text=str(ruta), font=("Consolas", 9), fg=TXT, bg=BG_CARD, anchor="w").pack(side=tk.LEFT)
            boton(fila, "Abrir", lambda r=ruta: self._abrir(r), BG_TERTIARY, TXT_2).pack(side=tk.RIGHT)
        tk.Frame(c, height=1, bg=BG_TERTIARY).pack(fill=tk.X, pady=8)
        etiqueta(c, "¿Vienes de la versión del proyecto o de otro PC? Trae tu base de datos (KB, transcripciones, "
                    "canales) a esta instalación. Se comprueba antes y se guarda copia de lo que hubiera.",
                 "suave", wrap=760).pack(fill=tk.X)
        boton(c, "📥 Traer mis datos desde…", self._importar, COLOR_PRIMARY).pack(anchor="w", pady=6)
        self._datos_res = etiqueta(c, "", "suave", wrap=760)
        self._datos_res.pack(fill=tk.X)

    def _construir_acerca(self) -> None:
        c = tarjeta(self.cuerpo, "ℹ️ Acerca de", TXT_3)
        modo = "programa instalado (.exe)" if PathManager._is_executable() else "desarrollo"
        etiqueta(c, f"{_VERSION} · modo: {modo} · Python {sys.version.split()[0]}", "suave").pack(fill=tk.X)
        etiqueta(c, "Las reglas financieras (mínimo 2×, objetivo 3× sobre coste landed) son las de Adrián Sáenz y "
                    "no se pueden cambiar desde aquí.", "tenue", wrap=760).pack(fill=tk.X, pady=(4, 0))

    # ── acciones ─────────────────────────────────────────────────────────────

    def _alternar_visibilidad(self) -> None:
        for e in self._entradas:
            e.config(show="" if self._mostrar.get() else "•")

    def _refrescar_estado(self) -> None:
        for ident, lbl in self._estado_vars.items():
            vars_ = [v for v in self._campos if lbl.master.master._variables.count(v)] if hasattr(lbl.master.master, "_variables") else []
            ok = bool(vars_) and all(os.environ.get(v, "").strip() for v in vars_)
            lbl.config(text="✔ Configurada" if ok else "✖ Falta", fg=COLOR_SUCCESS if ok else COLOR_WARNING)
        for var in self._campos:
            lbl = getattr(self, f"_act_{var}", None)
            if lbl is not None:
                lbl.config(text=("Actual: " + secrets_store.enmascarar(os.environ.get(var))) if os.environ.get(var) else "")

    def _notificar_cambio(self) -> None:
        self._refrescar_estado()
        if self._al_cambiar:
            try:
                self._al_cambiar()
            except Exception:
                pass

    def _guardar(self) -> None:
        nuevos = {n: v.get().strip() for n, v in self._campos.items() if v.get().strip()}
        if not nuevos:
            self.aviso("No has escrito ninguna clave nueva.", "aviso")
            return
        try:
            ruta = secrets_store.guardar_valores(nuevos)
        except (ValueError, OSError) as exc:
            self.aviso(f"No se pudo guardar: {exc}", "error")
            return
        for n in nuevos:
            self._campos[n].set("")
        self.aviso(f"Guardado ({len(nuevos)} valor/es) en {ruta}. Ya está activo.", "ok")
        self._notificar_cambio()

    def _guardar_otra(self) -> None:
        nombre, valor = self._otra_nombre.get().strip().upper(), self._otra_valor.get().strip()
        if not nombre or not valor:
            self.aviso("Escribe el nombre y el valor de la variable.", "aviso")
            return
        try:
            secrets_store.guardar_valores({nombre: valor})
        except (ValueError, OSError) as exc:
            self.aviso(f"No se pudo guardar: {exc}", "error")
            return
        self._otra_nombre.set("")
        self._otra_valor.set("")
        self.aviso(f"{nombre} guardada.", "ok")
        self._notificar_cambio()

    def _quitar(self, nombre: str) -> None:
        if not os.environ.get(nombre):
            self.aviso(f"{nombre} no estaba definida.", "info")
            return
        if not messagebox.askyesno("Quitar clave", f"¿Quitar {nombre}? Los agentes que la necesiten dejarán de funcionar."):
            return
        try:
            secrets_store.guardar_valores({nombre: ""})
        except (ValueError, OSError) as exc:
            self.aviso(f"No se pudo quitar: {exc}", "error")
            return
        self.aviso(f"{nombre} quitada.", "ok")
        self._notificar_cambio()

    def _probar_openrouter(self) -> None:
        clave = self._campos["OPENROUTER_API_KEY"].get().strip() or os.environ.get("OPENROUTER_API_KEY", "")
        if not clave:
            self._resultado.config(text="Escribe o guarda primero la clave de OpenRouter.", fg=COLOR_WARNING)
            return
        self._probar_btn.config(state="disabled")
        self._resultado.config(text="Comprobando con OpenRouter…", fg=TXT_2)

        def trabajo():
            import requests
            r = requests.get("https://openrouter.ai/api/v1/auth/key",
                             headers={"Authorization": f"Bearer {clave}"}, timeout=12)
            return r.status_code, (r.json().get("data") if r.headers.get("content-type", "").startswith("application/json") else None)

        def listo(res):
            self._probar_btn.config(state="normal")
            codigo, datos = res
            if codigo == 200:
                extra = ""
                if isinstance(datos, dict):
                    restante = datos.get("limit_remaining")
                    extra = f" Crédito restante: {restante:.2f}." if isinstance(restante, (int, float)) else ""
                self._resultado.config(text="✔ La clave es válida y OpenRouter responde." + extra, fg=COLOR_SUCCESS)
            elif codigo in (401, 403):
                self._resultado.config(text="✖ OpenRouter rechaza esa clave (revisa que esté completa).", fg=COLOR_ERROR)
            else:
                self._resultado.config(text=f"OpenRouter respondió HTTP {codigo}; inténtalo de nuevo.", fg=COLOR_WARNING)

        def fallo(exc):
            self._probar_btn.config(state="normal")
            self._resultado.config(text=f"No se pudo contactar con OpenRouter: {type(exc).__name__}. ¿Hay internet?", fg=COLOR_ERROR)

        self.en_hilo(trabajo, listo, fallo)

    def _guardar_avisos(self) -> None:
        silencio = self._av_silencio.get().strip()
        try:
            a, b = (int(x) for x in silencio.split("-"))
            if not (0 <= a <= 24 and 0 <= b <= 24):
                raise ValueError
        except ValueError:
            self._av_res.config(text="El silencio debe ser «inicio-fin» en horas, p. ej. 23-7 (o 0-0 para ninguno).", fg=COLOR_ERROR)
            return
        try:
            secrets_store.guardar_valores({"GEM_OS_AVISOS": "1" if self._av_on.get() else "0",
                                           "GEM_OS_AVISOS_NIVEL": self._av_nivel.get(),
                                           "GEM_OS_AVISOS_SILENCIO": silencio})
        except (ValueError, OSError) as exc:
            self._av_res.config(text=f"No se pudo guardar: {exc}", fg=COLOR_ERROR)
            return
        self._av_res.config(text="Ajustes de avisos guardados.", fg=COLOR_SUCCESS)

    def _probar_avisos(self) -> None:
        from app.services import notifier
        self._av_res.config(text="Enviando aviso de prueba…", fg=TXT_2)

        def listo(r):
            canales = ", ".join(f"{k}: {'enviado' if v['ok'] else 'falló (' + str(v.get('motivo')) + ')'}"
                                for k, v in (r.get("canales") or {}).items())
            self._av_res.config(text=(("✔ " if r.get("ok") else "✖ ") + (r.get("motivo") or "") + " " + canales).strip(),
                                fg=COLOR_SUCCESS if r.get("ok") else COLOR_WARNING)
        self.en_hilo(notifier.enviar_prueba, listo)

    def _abrir(self, ruta) -> None:
        try:
            os.makedirs(ruta, exist_ok=True)
            os.startfile(str(ruta))          # type: ignore[attr-defined]  (solo Windows)
        except (OSError, AttributeError) as exc:
            self.aviso(f"No se pudo abrir la carpeta: {exc}", "error")

    def _importar(self) -> None:
        carpeta = filedialog.askdirectory(title="Carpeta «data» con dropshipping_suite.db")
        if not carpeta:
            return
        if not messagebox.askyesno("Traer mis datos", "Se copiará la base de datos de esa carpeta a esta instalación.\n"
                                   "Si ya hay datos aquí, se guardará una copia antes.\n\n¿Continuar?"):
            return
        self._datos_res.config(text="Copiando…", fg=TXT_2)

        def listo(r):
            extra = f" Copia previa: {r['respaldo']}" if r.get("respaldo") else ""
            self._datos_res.config(text=f"✔ Datos traídos ({len(r['json'])} archivos de configuración).{extra} "
                                        "Reinicia el programa para ver todo actualizado.", fg=COLOR_SUCCESS)

        def fallo(exc):
            self._datos_res.config(text=f"✖ {exc}", fg=COLOR_ERROR)

        self.en_hilo(lambda: runtime_setup.importar_datos(carpeta), listo, fallo)
