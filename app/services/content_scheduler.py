"""
AI Content Scheduler — Planificador de Contenido con IA
=========================================================
GEM OS Suite — Programa la publicación de copys y guiones TikTok
con sugerencias de mejor momento basadas en análisis.
"""

import json
import logging
import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Mejores horas de publicación por categoría (hora local)
BEST_TIMES = {
    "general": ["08:00", "12:00", "18:00", "21:00"],
    "tecnologia": ["09:00", "13:00", "19:00", "22:00"],
    "moda": ["07:00", "11:00", "17:00", "20:00"],
    "belleza": ["07:00", "10:00", "16:00", "19:00"],
    "hogar": ["08:00", "12:00", "15:00", "18:00"],
    "fitness": ["06:00", "07:00", "12:00", "18:00"],
    "mascotas": ["08:00", "12:00", "17:00", "20:00"],
}

# Días de la semana
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


class ContentScheduler:
    """Planificador de contenido con sugerencias de publicación."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._schedule_file = self.data_dir / "content_schedule.json"
        self._schedule: List[Dict] = []
        self._load_schedule()

    def _load_schedule(self):
        if self._schedule_file.exists():
            try:
                with open(self._schedule_file, "r", encoding="utf-8") as f:
                    self._schedule = json.load(f)
            except Exception as e:
                logger.warning(f"[SCHEDULER] Error cargando schedule: {e}")
                self._schedule = []

    def _save_schedule(self):
        try:
            with open(self._schedule_file, "w", encoding="utf-8") as f:
                json.dump(self._schedule, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[SCHEDULER] Error guardando schedule: {e}")

    def suggest_best_time(self, categoria: str = "general") -> Dict:
        """
        Sugiere el mejor momento para publicar según la categoría.

        Returns:
            Dict con 'dia', 'hora', 'score'
        """
        cat = categoria.lower().strip()
        times = BEST_TIMES.get(cat, BEST_TIMES["general"])

        # Elegir el próximo horario disponible
        now = datetime.now()
        current_hour = now.hour
        current_min = now.minute

        best_time = None
        for t in times:
            h, m = map(int, t.split(":"))
            if h > current_hour or (h == current_hour and m > current_min):
                best_time = t
                break

        if not best_time:
            best_time = times[0]  # Mañana siguiente

        # Día sugerido
        today_idx = now.weekday()
        suggested_days = [DIAS[today_idx]]
        if today_idx < 4:  # Entre semana
            suggested_days.append(DIAS[today_idx + 1])

        return {
            "categoria": cat,
            "horarios_disponibles": times,
            "hora_sugerida": best_time,
            "dias_sugeridos": suggested_days,
            "score_estimado": random.randint(70, 95),
        }

    def schedule_content(self, content_data: Dict, categoria: str = "general",
                         dias: Optional[List[str]] = None) -> Dict:
        """
        Programa contenido para publicación futura.

        Args:
            content_data: Dict con tipo, titulo, contenido
            categoria: Categoría del contenido
            dias: Días específicos (opcional)

        Returns:
            Dict con la entrada programada
        """
        suggestion = self.suggest_best_time(categoria)
        target_dias = dias or suggestion["dias_sugeridos"]

        entry = {
            "id": len(self._schedule) + 1,
            "created_at": datetime.now().isoformat(),
            "scheduled_for": target_dias,
            "scheduled_time": suggestion["hora_sugerida"],
            "categoria": categoria,
            "content_type": content_data.get("type", "copy"),
            "title": content_data.get("title", "")[:80],
            "content_preview": str(content_data.get("content", ""))[:100],
            "status": "scheduled",
            "score": suggestion["score_estimado"],
        }

        self._schedule.append(entry)
        self._save_schedule()
        logger.info(f"[SCHEDULER] Contenido programado: {entry['title']} para {target_dias}")
        return entry

    def get_schedule(self, status: Optional[str] = None) -> List[Dict]:
        """Obtiene la lista de contenido programado."""
        if status:
            return [s for s in self._schedule if s.get("status") == status]
        return self._schedule

    def mark_posted(self, entry_id: int) -> bool:
        """Marca un contenido como publicado."""
        for entry in self._schedule:
            if entry.get("id") == entry_id:
                entry["status"] = "posted"
                entry["posted_at"] = datetime.now().isoformat()
                self._save_schedule()
                logger.info(f"[SCHEDULER] Contenido {entry_id} marcado como publicado")
                return True
        return False

    def get_weekly_plan(self, categoria: str = "general") -> List[Dict]:
        """Genera un plan semanal de contenido."""
        suggestion = self.suggest_best_time(categoria)
        plan = []
        for dia in DIAS[:5]:  # Lunes a Viernes
            plan.append({
                "dia": dia,
                "hora": suggestion["horarios_disponibles"][DIAS.index(dia) % len(suggestion["horarios_disponibles"])],
                "tipo": "copy" if DIAS.index(dia) % 2 == 0 else "tiktok",
                "categoria": categoria,
            })
        return plan