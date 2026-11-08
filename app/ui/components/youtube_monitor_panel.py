"""
YouTubeMonitorPanel - UI para Monitor de Canales YouTube y Transcripciones.
Pestañas: Canales, Videos Favoritos, Playlists y Transcripciones (leer, buscar,
copiar, exportar, pegar URL/texto y borrar).
"""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.services import transcript_store
from app.services.youtube_channel_monitor import YouTubeChannelMonitor

_LIMITE_TRANSCRIPCIONES = 300


class YouTubeMonitorPanel(ttk.Frame):
    """Panel UI para monitoreo de canales YouTube con tabs extendidos."""

    def __init__(self, parent, db_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.db_manager = db_manager
        self.monitor = YouTubeChannelMonitor(db_manager=db_manager)
        self.syncing = False
        self._t_actual = None       # transcripción abierta en el visor
        self._t_after = None        # temporizador del buscador (debounce)
        self._build_ui()

    # ─────────────────────────── Layout principal ────────────────────────────

    def _build_ui(self):
        ctrl = ttk.Frame(self, padding=(8, 6))
        ctrl.pack(fill=tk.X)

        self.btn_sync = ttk.Button(ctrl, text="⟳  Sincronizar Ahora", command=self._sincronizar)
        self.btn_sync.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_cancel = ttk.Button(ctrl, text="■  Cancelar", command=self._cancelar_sync,
                                     state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(ctrl, text="＋  Agregar Canal", command=self._agregar_canal).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(ctrl, text="↺  Recargar", command=self._recargar_todo).pack(side=tk.LEFT)

        self.lbl_estado = ttk.Label(ctrl, text="●  Listo", foreground="#4CAF50")
        self.lbl_estado.pack(side=tk.RIGHT, padx=8)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._tab_canales = ttk.Frame(self.nb)
        self._tab_videos = ttk.Frame(self.nb)
        self._tab_playlist = ttk.Frame(self.nb)
        self._tab_trans = ttk.Frame(self.nb)

        self.nb.add(self._tab_canales, text="  📡  Canales  ")
        self.nb.add(self._tab_videos, text="  🎬  Videos Favoritos  ")
        self.nb.add(self._tab_playlist, text="  📋  Playlists  ")
        self.nb.add(self._tab_trans, text="  📝  Transcripciones  ")

        self._build_tab_canales()
        self._build_tab_videos()
        self._build_tab_playlists()
        self._build_tab_transcripciones()

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

        self.lbl_canales_count = ttk.Label(f, text="")
        self.lbl_canales_count.pack(side=tk.BOTTOM, anchor=tk.W, padx=4, pady=2)

        sb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self.tree_canales.yview)
        self.tree_canales.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_canales.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _cargar_canales(self):
        for item in self.tree_canales.get_children():
            self.tree_canales.delete(item)
        datos = self.monitor.obtener_resumen_canales()
        for r in datos:
            ultimo = (r.get("ultimo_video_procesado") or "—")[:16]
            self.tree_canales.insert("", "end", values=(
                r.get("nombre") or "",
                r.get("handle") or "",
                r.get("tags") or "",
                r.get("idioma") or "",
                r.get("prioridad") or 5,
                r.get("videos_descargados") or 0,
                ultimo,
            ))
        self.lbl_canales_count.config(text=f"{len(datos)} canales registrados")

    # ──────────────────────────── Tab: Videos ────────────────────────────────

    def _build_tab_videos(self):
        f = self._tab_videos

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

        self.lbl_videos_count = ttk.Label(f, text="")
        self.lbl_videos_count.pack(side=tk.BOTTOM, anchor=tk.W, padx=4, pady=2)

        sb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self.tree_videos.yview)
        self.tree_videos.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_videos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

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
            titulo = r.get("titulo") or ""
            canal = r.get("canal") or ""
            tags = r.get("tags") or ""
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

        self.lbl_playlists_count = ttk.Label(f, text="")
        self.lbl_playlists_count.pack(side=tk.BOTTOM, anchor=tk.W, padx=4, pady=2)

        sb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self.tree_playlists.yview)
        self.tree_playlists.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_playlists.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _cargar_playlists(self):
        for item in self.tree_playlists.get_children():
            self.tree_playlists.delete(item)
        datos = self.monitor.obtener_playlists()
        for r in datos:
            self.tree_playlists.insert("", "end", values=(
                r.get("titulo") or "",
                r.get("canal") or "",
                r.get("tags") or "",
                r.get("video_count") or 0,
                "Sí" if r.get("es_privada") else "No",
                "✓" if r.get("activa") else "—",
                (r.get("agregada_at") or "")[:16],
            ))
        self.lbl_playlists_count.config(text=f"{len(datos)} playlists registradas")

    # ───────────────────────── Tab: Transcripciones ──────────────────────────

    def _build_tab_transcripciones(self):
        f = self._tab_trans

        bar = ttk.Frame(f, padding=(4, 4))
        bar.pack(fill=tk.X)
        ttk.Label(bar, text="Buscar:").pack(side=tk.LEFT)
        self._var_buscar_t = tk.StringVar()
        self._var_buscar_t.trace_add("write", lambda *_: self._buscar_transcripciones_diferido())
        ttk.Entry(bar, textvariable=self._var_buscar_t, width=28).pack(side=tk.LEFT, padx=4)

        ttk.Button(bar, text="＋ URL / texto", command=self._agregar_transcripcion).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(bar, text="Copiar", command=self._copiar_transcripcion).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(bar, text="Exportar .md", command=self._exportar_transcripcion).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(bar, text="Eliminar", command=self._eliminar_transcripcion).pack(side=tk.LEFT, padx=(4, 0))

        self._var_vista = tk.StringVar(value="limpia")
        ttk.Radiobutton(bar, text="Original", variable=self._var_vista, value="original",
                        command=self._mostrar_detalle).pack(side=tk.RIGHT)
        ttk.Radiobutton(bar, text="Limpio", variable=self._var_vista, value="limpia",
                        command=self._mostrar_detalle).pack(side=tk.RIGHT, padx=(0, 6))

        self.lbl_trans_count = ttk.Label(f, text="")
        self.lbl_trans_count.pack(side=tk.BOTTOM, anchor=tk.W, padx=4, pady=2)

        paned = ttk.PanedWindow(f, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(paned)
        cols = ("Título", "Canal", "Fecha", "Tokens", "Estado")
        self.tree_trans = ttk.Treeview(top, columns=cols, show="headings", height=7,
                                       selectmode="browse")
        widths = {"Título": 340, "Canal": 150, "Fecha": 90, "Tokens": 70, "Estado": 80}
        for col in cols:
            self.tree_trans.heading(col, text=col)
            self.tree_trans.column(col, width=widths[col], anchor=tk.W)
        sb = ttk.Scrollbar(top, orient=tk.VERTICAL, command=self.tree_trans.yview)
        self.tree_trans.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_trans.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_trans.bind("<<TreeviewSelect>>", lambda _e: self._mostrar_detalle())
        paned.add(top, weight=1)

        bottom = ttk.Frame(paned)
        self.txt_detalle = tk.Text(bottom, wrap=tk.WORD, state=tk.DISABLED, height=10)
        sb2 = ttk.Scrollbar(bottom, orient=tk.VERTICAL, command=self.txt_detalle.yview)
        self.txt_detalle.configure(yscrollcommand=sb2.set)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_detalle.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        paned.add(bottom, weight=2)

        self._set_detalle("Selecciona una transcripción para leerla.")

    def _buscar_transcripciones_diferido(self):
        """Espera 350 ms tras la última tecla antes de consultar la BD."""
        if self._t_after:
            self.after_cancel(self._t_after)
        self._t_after = self.after(350, self._cargar_transcripciones)

    def _cargar_transcripciones(self):
        self._t_after = None
        seleccionada = self.tree_trans.selection()
        try:
            res = transcript_store.list_transcripts(
                self.monitor.db_path,
                buscar=self._var_buscar_t.get(),
                limite=_LIMITE_TRANSCRIPCIONES,
            )
        except Exception as exc:
            self.lbl_trans_count.config(text=f"Error leyendo transcripciones: {exc}")
            return
        for item in self.tree_trans.get_children():
            self.tree_trans.delete(item)
        for t in res["items"]:
            tokens = t["tokens_limpios"] or t["tokens_original"] or 0
            self.tree_trans.insert("", "end", iid=str(t["id"]), values=(
                (t["titulo"] or "(sin título)")[:90],
                t["canal"] or "",
                (t["fecha"] or t["creada_at"] or "")[:10],
                f"{tokens:,}",
                "Procesada" if t["procesada"] else "Pendiente",
            ))
        mostradas, total = len(res["items"]), res["total"]
        self.lbl_trans_count.config(
            text=f"{total} transcripciones" if mostradas == total
            else f"Mostrando {mostradas} de {total} (afina la búsqueda)"
        )
        if seleccionada and self.tree_trans.exists(seleccionada[0]):
            self.tree_trans.selection_set(seleccionada[0])
        elif not res["items"]:
            self._t_actual = None
            self._set_detalle("Sin transcripciones. Sincroniza canales o pega una URL de YouTube.")

    def _set_detalle(self, texto: str):
        self.txt_detalle.config(state=tk.NORMAL)
        self.txt_detalle.delete("1.0", tk.END)
        self.txt_detalle.insert("1.0", texto)
        self.txt_detalle.config(state=tk.DISABLED)

    def _texto_actual(self) -> str:
        if not self._t_actual:
            return ""
        clave = "transcripcion_limpia" if self._var_vista.get() == "limpia" else "transcripcion_texto"
        return self._t_actual.get(clave) or ""

    def _mostrar_detalle(self):
        sel = self.tree_trans.selection()
        if not sel:
            return
        if not self._t_actual or str(self._t_actual["id"]) != sel[0]:
            try:
                self._t_actual = transcript_store.get_transcript(self.monitor.db_path, int(sel[0]))
            except Exception as exc:
                self._set_detalle(f"Error leyendo la transcripción: {exc}")
                return
        if not self._t_actual:
            self._set_detalle("La transcripción ya no existe.")
            return
        texto = self._texto_actual()
        if not texto:
            texto = "(Sin texto limpio todavía)" if self._var_vista.get() == "limpia" else "(Sin texto original)"
        self._set_detalle(texto)

    def _copiar_transcripcion(self):
        texto = self._texto_actual()
        if not texto:
            messagebox.showinfo("Copiar", "Selecciona una transcripción primero.")
            return
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.lbl_estado.config(text="●  Copiado al portapapeles", foreground="#4CAF50")
        self.after(2500, lambda: self.lbl_estado.config(
            text="●  Sincronizando…" if self.syncing else "●  Listo",
            foreground="#FF9800" if self.syncing else "#4CAF50"))

    def _exportar_transcripcion(self):
        if not self._t_actual:
            messagebox.showinfo("Exportar", "Selecciona una transcripción primero.")
            return
        limpia = self._var_vista.get() == "limpia"
        ruta = filedialog.asksaveasfilename(
            title="Exportar transcripción", defaultextension=".md",
            initialfile=transcript_store.safe_filename(self._t_actual.get("titulo")),
            filetypes=[("Markdown", "*.md"), ("Texto", "*.txt")],
        )
        if not ruta:
            return
        try:
            with open(ruta, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(transcript_store.to_markdown(self._t_actual, limpia=limpia))
        except OSError as exc:
            messagebox.showerror("Exportar", f"No se pudo guardar el archivo:\n{exc}")

    def _eliminar_transcripcion(self):
        sel = self.tree_trans.selection()
        if not sel:
            messagebox.showinfo("Eliminar", "Selecciona una transcripción primero.")
            return
        titulo = self.tree_trans.item(sel[0], "values")[0]
        if not messagebox.askyesno(
                "Eliminar transcripción",
                f"¿Eliminar «{titulo}»?\n\nEsta acción no se puede deshacer."):
            return
        transcript_store.delete_transcript(self.monitor.db_path, int(sel[0]))
        self._t_actual = None
        self._recargar_todo()

    def _agregar_transcripcion(self):
        """Diálogo: descargar por URL de YouTube o pegar texto a mano."""
        dlg = tk.Toplevel(self)
        dlg.title("Agregar transcripción")
        dlg.geometry("560x470")
        dlg.transient(self.winfo_toplevel())
        pad = {"padx": 10, "pady": 3}

        ttk.Label(dlg, text="A) URL de un vídeo de YouTube (se descargan los subtítulos):").pack(anchor=tk.W, **pad)
        fila = ttk.Frame(dlg)
        fila.pack(fill=tk.X, **pad)
        e_url = ttk.Entry(fila)
        e_url.pack(side=tk.LEFT, fill=tk.X, expand=True)
        btn_url = ttk.Button(fila, text="Descargar")
        btn_url.pack(side=tk.LEFT, padx=(6, 0))
        lbl = ttk.Label(dlg, text="", foreground="#888")
        lbl.pack(anchor=tk.W, **pad)

        ttk.Separator(dlg).pack(fill=tk.X, pady=6)
        ttk.Label(dlg, text="B) O pega el texto de la transcripción:").pack(anchor=tk.W, **pad)
        ttk.Label(dlg, text="Título:").pack(anchor=tk.W, **pad)
        e_tit = ttk.Entry(dlg)
        e_tit.pack(fill=tk.X, **pad)
        ttk.Label(dlg, text="Canal (opcional):").pack(anchor=tk.W, **pad)
        e_can = ttk.Entry(dlg)
        e_can.pack(fill=tk.X, **pad)
        txt = tk.Text(dlg, height=8, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True, **pad)
        btn_txt = ttk.Button(dlg, text="Guardar texto")
        btn_txt.pack(pady=6)

        def terminar(res=None, error=None):
            if not dlg.winfo_exists():
                return
            btn_url.config(state=tk.NORMAL)
            btn_txt.config(state=tk.NORMAL)
            if error:
                lbl.config(text=error, foreground="#E53935")
                return
            if res.get("duplicado"):
                lbl.config(text="Esa transcripción ya estaba guardada.", foreground="#FF9800")
            else:
                self._recargar_todo()
                dlg.destroy()

        def lanzar(fn):
            btn_url.config(state=tk.DISABLED)
            btn_txt.config(state=tk.DISABLED)
            lbl.config(text="Procesando…", foreground="#888")

            def worker():
                try:
                    res = fn()
                    self.after(0, lambda r=res: terminar(res=r))
                except Exception as exc:
                    self.after(0, lambda m=str(exc): terminar(error=m))
            threading.Thread(target=worker, daemon=True).start()

        def por_url():
            url = e_url.get().strip()
            if not url:
                lbl.config(text="Escribe una URL.", foreground="#E53935")
                return
            lanzar(lambda: transcript_store.ingest_url(
                self.monitor.db_path, url, self.monitor.cleaner))

        def por_texto():
            texto = txt.get("1.0", tk.END).strip()
            titulo = e_tit.get().strip()
            if not titulo:
                lbl.config(text="Falta el título.", foreground="#E53935")
                return
            lanzar(lambda: transcript_store.ingest_text(
                self.monitor.db_path, titulo, e_can.get().strip(), texto, self.monitor.cleaner))

        btn_url.config(command=por_url)
        btn_txt.config(command=por_texto)

    # ──────────────────────────── Stats bar ──────────────────────────────────

    def _actualizar_stats(self):
        estado = self.monitor.obtener_estado_monitor()
        ul = estado.get("ultima_sincronizacion")
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        if ul:
            txt = (
                f"Fecha: {str(ul.get('fecha_sincronizacion', ''))[:19]}  |  "
                f"Canales: {ul.get('canales_procesados', 0)}  |  "
                f"Descargados: {ul.get('videos_descargados', 0)}  |  "
                f"Guardadas: {ul.get('transcripciones_procesadas', 0)}  |  "
                f"Duplicados: {ul.get('duplicados', 0)}  |  "
                f"Sin subtítulos: {ul.get('sin_subtitulos', 0)}  |  "
                f"Errores: {ul.get('errores', 0)}  |  "
                f"Tokens ahorrados: {ul.get('tokens_ahorrados', 0)}"
                + ("  |  (cancelada)" if ul.get("cancelado") else "")
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
        self._cargar_transcripciones()
        self._actualizar_stats()

    def _set_sync_ui(self, activo: bool, texto: str = ""):
        self.syncing = activo
        self.btn_sync.config(state=tk.DISABLED if activo else tk.NORMAL)
        self.btn_cancel.config(state=tk.NORMAL if activo else tk.DISABLED)
        if activo:
            self.lbl_estado.config(text=f"●  {texto or 'Sincronizando…'}", foreground="#FF9800")
        else:
            self.lbl_estado.config(text="●  Listo", foreground="#4CAF50")

    def _sincronizar(self):
        if self.syncing:
            messagebox.showwarning("Sincronización en curso", "Ya hay una sincronización activa")
            return
        self._set_sync_ui(True)

        def progreso(msg: str):
            self.after(0, lambda m=msg: self.syncing and self.lbl_estado.config(
                text=f"●  {m[:70]}", foreground="#FF9800"))

        def worker():
            try:
                resultado = self.monitor.sincronizar_canales(progress=progreso)
                self.after(0, lambda r=resultado: self._sync_done(r))
            except Exception as exc:
                self.after(0, lambda m=str(exc): self._sync_error(m))

        threading.Thread(target=worker, daemon=True).start()

    def _cancelar_sync(self):
        self.monitor.cancelar_sincronizacion()
        self.lbl_estado.config(text="●  Cancelando…", foreground="#FF9800")
        self.btn_cancel.config(state=tk.DISABLED)

    def _sync_error(self, mensaje: str):
        self._set_sync_ui(False)
        messagebox.showerror("Error de Sincronización", mensaje)

    def _sync_done(self, resultado):
        self._set_sync_ui(False)
        self._recargar_todo()
        msg = (
            f"{'Sincronización cancelada' if resultado.get('cancelado') else 'Sincronización completada'}:\n"
            f"· Canales revisados: {resultado['canales_procesados']}\n"
            f"· Transcripciones nuevas: {resultado['transcripciones_procesadas']}\n"
            f"· Duplicados: {resultado['duplicados']}\n"
            f"· Sin subtítulos: {resultado['sin_subtitulos']}\n"
            f"· Errores: {resultado['errores']}\n"
            f"· Tokens ahorrados: {resultado['tokens_ahorrados']}"
        )
        messagebox.showinfo("Sincronización", msg)

    def _agregar_canal(self):
        """Diálogo extendido para agregar canal con metadata."""
        dlg = tk.Toplevel(self)
        dlg.title("Agregar Canal")
        dlg.geometry("420x300")
        dlg.resizable(False, False)
        dlg.transient(self.winfo_toplevel())

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

        def entero(widget, minimo, maximo, defecto):
            try:
                return max(minimo, min(maximo, int(widget.get())))
            except (TypeError, ValueError):
                return defecto

        def guardar():
            nombre = e_nombre.get().strip()
            url = e_url.get().strip()
            if not nombre or not url:
                messagebox.showwarning("Campos requeridos", "Completa nombre y URL", parent=dlg)
                return
            ok = self.monitor.agregar_canal(
                url=url, nombre=nombre,
                tags=e_tags.get().strip(),
                idioma=var_idioma.get(),
                prioridad=entero(e_prio, 1, 10, 5),
                max_videos_scan=entero(e_max, 5, 200, 30),
            )
            if ok:
                messagebox.showinfo("Éxito", f"Canal '{nombre}' agregado", parent=dlg)
                self._recargar_todo()
                dlg.destroy()
            else:
                messagebox.showerror(
                    "Error", self.monitor.ultimo_error or "No se pudo guardar el canal", parent=dlg)

        ttk.Button(dlg, text="Guardar", command=guardar).pack(pady=10)
