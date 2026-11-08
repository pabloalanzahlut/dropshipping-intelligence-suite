"""Regresiones de la herramienta de transcripciones (escritorio + web).

Sin red: la descarga de YouTube se prueba aparte a mano. Cada test usa su propia
base de datos temporal; nunca toca data/dropshipping_suite.db.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import DatabaseConnection
from app.services import transcript_store
from app.services.kb_cache_validator import KBCacheValidator
from app.services.transcript_cleaner import TranscriptCleaner
from app.services.youtube_rss_fetcher import _parse_vtt, _pick_vtt, parse_video_id_for_tests \
    if False else (None, None, None)  # noqa: E501  (ver import real más abajo)
