"""
YouTubeMonitorPanel - UI para Monitor de Canales YouTube
Muestra canales favoritos, videos bookmarked y playlists en tabs separados.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime

from app.services.youtube_channel_monitor import YouTubeChannelMonitor


class YouTubeMonitorPanel(ttk.Frame):
    """Panel UI para monitoreo de canales YouTube con tabs extendidos."""

    def __init__(self, parent, db_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.db_manager = db_manager
        self.monitor = YouTubeChannelMonitor(db_manager=db_manager)
        self.syncing = False
        self._build_ui()

    # ─────────────────────────── Layout principal ────────────────────────────

    def _build_ui(self):
        # Barra superior: controles de sync
        ctrl = ttk.Frame(self, padding=(8, 6))
        ctrl.pack(fill=tk.X)

        ttk.Button(ctrl, text="⟳  Sincronizar Ahora", command=self._sincronizar).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(ctrl, text="＋  Agregar Canal",    command=self._agregar_canal).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(ctrl, text="↺  Recargar",          command=self._recargar_todo).pack(side=tk.LEFT)

        self.lbl_estado = ttk.Label(ctrl, text="●  Listo", foreground="#4CAF50")
        self.lbl_estado.pack(side=tk.RIGHT, padx=8)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # Notebook con 3 tabs
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._tab_canales  = ttk.Frame(self.nb)
        self._tab_videos   = ttk.Frame(self.nb)
        self._tab_playlist = ttk.Frame(self.nb)

        self.nb.add(self._tab_canales,  text="  📡  Canales  ")
        self.nb.add(self._tab_videos,   text="  🎬  Videos Favoritos  ")
        self.nb.add(self._tab_playlist, text="  📋  Playlists  ")

        self._build_tab_canales()
        self._build_tab_videos()
        self._build_tab_playlists()

        # Área de stats debajo del notebook
        sf = ttk.LabelFrame(self, text="Última Sincronización", padding=6)
        sf.pack(fill=tk.X, padx=6, pady=(0, 6))
        self.stats_text = tk.Text(sf, height=4, state=tk.DISABLED, wrap=tk.WORD)
        self.stats_text.pack(fill=tk.X)

        self._recargar_todo()

    # ──────────────────────────── Tab: Canales ───────────────────────────────

    def _build_tab_canales(self):
        f = self._tab_canales

        cols = ("Nombre", "Handle", "Tags", "Idioma", "Prio", "Videos", "Último video")
        self.tree_canales = ttk.Treeview(f, columns=cols, show="headings", height=14)

        widths = {"Nombre": 160, "Handle": 140, "Tags": 180, "Idioma": 55,
                  "Prio": 40, "Videos": 55, "Último video": 145}
        for col in cols:
            self.tree_canales.heading(col, text=col)
            self.tree_canales.column(col, width=widths.get(col, 120), anchor=tk.W)

        sb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self.tree_canales.yview)
        self.tree_canales.configure(yscrollcommand=sb.set)
        self.tree_canales.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        # Etiqueta conteo
        self.lbl_canales_count = ttk.Label(f, text="")
        self.lbl_canales_count.pack(side=tk.BOTTOM, anchor=tk.W, padx=4, pady=2)

    def _cargar_canales(self):
        for item in self.tree_canales.get_children():
            self.tree_canales.delete(item)
        datos = self.monitor.obtener_resumen_canales()
        for r in datos:
            ultimo = (r.get("ultimo_video_procesado") or "—")[:16]
            self.tree_canales.insert("", "end", values=(
                r.get("nombre", ""),
                r.get("handle", ""),
                r.get("tags", ""),
                r.get("idioma", ""),
                r.get("prioridad", 5),
                r.get("videos_descargados", 0),
                ultimo,
            ))
        self.lbl_canales_count.config(text=f"{len(datos)} canales registrados")

    # ──────────────────────────── Tab: Videos ────────────────────────────────

    def _build_tab_videos(self):
        f = self._tab_videos

        # Barra de filtro rápido
        ff = ttk.Frame(f, padding=(4, 4))
        ff.pack(fill=tk.X)
        ttk.Label(ff, text="Filtrar:").pack(side=tk.LEFT)
        self._var_filtro = tk.StringVar()
        self._var_filtro.trace_add("write", lambda *_: self._filtrar_videos())
        ttk.Entry(ff, textvariable=self._var_filtro, width=30).pack(side=tk.LEFT, padx=4)

        cols = ("Título", "Canal", "Tags", "Trans.", "Fecha")
        self.tree_videos = ttk.Treeview(f, columns=cols, show="headings", height=16)
        widths = {"Título": 320, "Canal": 150, "Tags": 160, "Trans.": 50, "Fecha": 145}
        for col in cols:
            self.tree_videos.heading(col, text=col)
            self.tree_videos.column(col, width=widths.get(col, 100), anchor=tk.W)

        sb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self.tree_videos.yview)
        self.tree_videos.configure(yscrollcommand=sb.set)
        self.tree_videos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.lbl_videos_count = ttk.Label(f, text="")
        self.lbl_videos_count.pack(side=tk.BOTTOM, anchor=tk.W, padx=4, pady=2)

        self._videos_cache = []

    def _cargar_videos(self):
        self._videos_cache = self.monitor.obtener_videos_favoritos(limite=500)
        self._filtrar_videos()

    def _filtrar_videos(self):
        for item in self.tree_videos.get_children():
            self.tree_videos.delete(item)
        q = self._var_filtro.get().lower()
        mostrados = 0
        for r in self._videos_cache:
            titulo = r.get("titulo", "")
            canal  = r.get("canal", "")
            tags   = r.get("tags", "")
            if q and q not in titulo.lower() and q not in canal.lower() and q not in tags.lower():
                continue
            trans = "✓" if r.get("transcripcion_procesada") else "—"
            fecha = (r.get("guardado_at") or "")[:16]
            self.tree_videos.insert("", "end", values=(titulo[:70], canal, tags, trans, fecha))
            mostrados += 1
        total = len(self._videos_cache)
        self.lbl_videos_count.config(
            text=f"Mostrando {mostrados} de {total} videos" if q else f"{total} videos favoritos"
        )

    # ──────────────────────────── Tab: Playlists ─────────────────────────────

    def _build_tab_playlists(self):
        f = self._tab_playlist

        cols = ("Título", "Canal", "Tags", "Videos", "Privada", "Activa", "Agregada")
        self.tree_playlists = ttk.Treeview(f, columns=cols, show="headings", height=10)
        widths = {"Título": 240, "Canal": 120, "Tags": 160, "Videos": 60,
                  "Privada": 60, "Activa": 55, "Agregada": 145}
        for col in cols:
            self.tree_playlists.heading(col, text=col)
            self.tree_playlists.column(col, width=widths.get(col, 100), anchor=tk.W)

        sb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self.tree_playlists.yview)
        self.tree_playlists.configure(yscrollcommand=sb.set)
        self.tree_playlists.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.lbl_playlists_count = ttk.Label(f, text="")
        self.lbl_playlists_count.pack(side=tk.BOTTOM, anchor=tk.W, padx=4, pady=2)

    def _cargar_playlists(self):
        for item in self.tree_playlists.get_children():
            self.tree_playlists.delete(item)
        datos = self.monitor.obtener_playlists()
        for r in datos:
            self.tree_playlists.insert("", "end", values=(
                r.get("titulo", ""),
                r.get("canal", ""),
                r.get("tags", ""),
                r.get("video_count", 0),
                "Sí" if r.get("es_privada") else "No",
                "✓"  if r.get("activa")    else "—",
                (r.get("agregada_at") or "")[:16],
            ))
        self.lbl_playlists_count.config(text=f"{len(datos)} playlists registradas")

    # ──────────────────────────── Stats bar ──────────────────────────────────

    def _actualizar_stats(self):
        estado = self.monitor.obtener_estado_monitor()
        ul = estado.get("ultima_sincronizacion")
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        if ul:
            txt = (
                f"Fecha: {ul['fecha_sincronizacion'][:19]}  |  "
                f"Canales: {ul['canales_procesados']}  |  "
                f"Videos: {ul['videos_descargados']}  |  "
                f"Transcripciones: {ul['transcripciones_procesadas']}  |  "
                f"Duplicados: {ul['duplicados']}  |  "
                f"Errores: {ul['errores']}  |  "
                f"Tokens ahorrados: {ul['tokens_ahorrados']}"
            )
        else:
            txt = "Sin sincronizaciones aún. Presiona '⟳ Sincronizar Ahora' para comenzar."
        self.stats_text.insert(1.0, txt)
        self.stats_text.config(state=tk.DISABLED)

    # ──────────────────────────── Acciones ───────────────────────────────────

    def _recargar_todo(self):
        self._cargar_canales()
        self._cargar_videos()
        self._cargar_playlists()
        self._actualizar_stats()

    def _sincronizar(self):
        if self.syncing:
            messagebox.showwarning("Sincronización en curso", "Ya hay una sincronización activa")
            return
        self.syncing = True
        self.lbl_estado.config(text="●  Sincronizando…", foreground="#FF9800")

        def worker():
            try:
                resultado = self.monitor.sincronizar_canales()
                self.syncing = False
                self.after(0, lambda r=resultado: self._sync_done(r))
            except Exception as e:
                self.syncing = False
                self.after(0, lambda: messagebox.showerror("Error de Sincronización", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _sync_done(self, resultado):
        self.lbl_estado.config(text="●  Listo", foreground="#4CAF50")
        self._recargar_todo()
        msg = (
            f"Sincronización completada:\n"
            f"· Canales: {resultado['canales_procesados']}\n"
            f"· Videos: {resultado['videos_descargados']}\n"
            f"· Transcripciones: {resultado['transcripciones_procesadas']}\n"
            f"· Tokens ahorrados: {resultado['tokens_ahorrados']}"
        )
        messagebox.showinfo("Sincronización Exitosa", msg)

    def _agregar_canal(self):
        """Diálogo extendido para agregar canal con metadata."""
        dlg = tk.Toplevel(self)
        dlg.title("Agregar Canal")
        dlg.geometry("420x280")
        dlg.resizable(False, False)

        pad = {"padx": 10, "pady": 3}

        ttk.Label(dlg, text="Nombre del canal:").pack(anchor=tk.W, **pad)
        e_nombre = ttk.Entry(dlg, width=48)
        e_nombre.pack(**pad)

        ttk.Label(dlg, text="URL (ej: https://www.youtube.com/@canal):").pack(anchor=tk.W, **pad)
        e_url = ttk.Entry(dlg, width=48)
        e_url.pack(**pad)

        ttk.Label(dlg, text="Tags (separados por coma, ej: shopify,ads):").pack(anchor=tk.W, **pad)
        e_tags = ttk.Entry(dlg, width=48)
        e_tags.insert(0, "dropshipping")
        e_tags.pack(**pad)

        row = ttk.Frame(dlg)
        row.pack(fill=tk.X, **pad)

        ttk.Label(row, text="Idioma:").pack(side=tk.LEFT)
        var_idioma = tk.StringVar(value="es")
        ttk.Combobox(row, textvariable=var_idioma, values=["es", "en"], width=5, state="readonly").pack(side=tk.LEFT, padx=6)

        ttk.Label(row, text="Prioridad (1=alta … 10=baja):").pack(side=tk.LEFT, padx=(12, 0))
        e_prio = ttk.Spinbox(row, from_=1, to=10, width=4)
        e_prio.set(5)
        e_prio.pack(side=tk.LEFT, padx=6)

        ttk.Label(dlg, text="Máx. videos a escanear:").pack(anchor=tk.W, **pad)
        e_max = ttk.Spinbox(dlg, from_=5, to=200, width=8)
        e_max.set(30)
        e_max.pack(anchor=tk.W, **pad)

        def guardar():
            nombre = e_nombre.get().strip()
            url    = e_url.get().strip()
            if not nombre or not url:
                messagebox.showwarning("Campos requeridos", "Completa nombre y URL")
                return
            ok = self.monitor.agregar_canal(
                url=url, nombre=nombre,
                tags=e_tags.get().strip(),
                idioma=var_idioma.get(),
                prioridad=int(e_prio.get()),
                max_videos_scan=int(e_max.get()),
            )
            if ok:
                messagebox.showinfo("Éxito", f"Canal '{nombre}' agregado")
                self._recargar_todo()
                dlg.destroy()
            else:
                messagebox.showerror("Error", "No se pudo guardar el canal")

        ttk.Button(dlg, text="Guardar", command=guardar).pack(pady=10)
