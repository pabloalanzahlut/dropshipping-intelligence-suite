"""
error_knowledge_registry.py — Error Knowledge Registry v2.0 (Avanzado)
============================================================================
Basado en:
  - Gang of Four Singleton Pattern
  - Metaclases (Python Data Model: __call__, __new__, __init__)
  - PEP 8: Programming Recommendations (exception handling)
  - Reflection: inspect module para introspeccion de funciones
  - traceback: parsing de stack traces para fingerprinting

Proposito:
  Biblioteca de errores con memoria que a la SEGUNDA ocurrencia
  resuelve automaticamente. 15+ patrones de error detectables por
  reflection + metaclases.

Integracion GEM OS:
  - EliteLogger (elite_logger.py) -> logging estructurado
  - MemoryLogger (memory_logger.py) -> persistencia dual
  - RetryDecorator (retry_decorator.py) -> reinteligencia
"""

import enum
import hashlib
import inspect
import json
import logging
import sqlite3
import threading
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path as PathLib
from typing import Dict, List, Optional, Tuple, Type, Any, Callable

logger = logging.getLogger(__name__)

# ============================================================
# ENUM: ErrorPattern - 15+ Patrones de Error Detectables
# ============================================================


class ErrorPattern(enum.Enum):
    """
    15+ patrones de error reconocibles por el sistema.
    Cada patron define: codigo, categoria, estrategia por defecto.
    """

    # Red y Comunicacion
    NETWORK_CONNECTION = ("connection_error", "red", "Reintentar con backoff exponencial")
    NETWORK_TIMEOUT = ("timeout", "red", "Reintentar con espera creciente")
    NETWORK_DNS = ("dns_error", "red", "Verificar DNS y reintentar")
    RATE_LIMIT = ("rate_limit", "red", "Esperar y reintentar con jitter")
    API_ERROR = ("api_error", "red", "Reintentar con backoff + log")

    # Base de Datos
    DATABASE_CONNECTION = ("db_connection", "base_datos", "Reconectar y reintentar")
    DATABASE_LOCKED = ("db_locked", "base_datos", "Esperar liberacion y reintentar")
    DATABASE_INTEGRITY = ("db_integrity", "base_datos", "Validar datos y reintentar")

    # Archivos y E/S
    FILE_NOT_FOUND = ("file_not_found", "archivos", "Buscar en rutas alternativas")
    FILE_PERMISSION = ("file_permission", "archivos", "Intentar con permisos elevados")
    FILE_CORRUPT = ("file_corrupt", "archivos", "Restaurar desde backup")

    # Parseo y Serializacion
    PARSE_ERROR = ("parse_error", "parseo", "Intentar parseo leniente")
    JSON_DECODE = ("json_decode", "parseo", "Sanitizar y re-intentar parseo")
    ENCODING_ERROR = ("encoding_error", "parseo", "Detectar encoding y re-intentar")

    # Validacion y Estado
    VALIDATION_ERROR = ("validation", "validacion", "Sanitizar entrada y reintentar")
    STATE_ERROR = ("state_error", "estado", "Resetear estado y reintentar")
    CONFIG_ERROR = ("config_error", "configuracion", "Cargar configuracion por defecto")

    # Concurrencia
    THREAD_ERROR = ("thread_error", "concurrencia", "Reintentar en nuevo hilo")
    DEADLOCK_DETECTED = ("deadlock", "concurrencia", "Liberar locks y reintentar")

    # Dependencias
    DEPENDENCY_MISSING = ("dep_missing", "dependencias", "Instalar dependencia faltante")
    IMPORT_ERROR = ("import_error", "dependencias", "Verificar entorno e importar")

    # Memoria y Recursos
    MEMORY_ERROR = ("memory", "recursos", "Liberar memoria y reintentar")
    RESOURCE_EXHAUSTED = ("resource_exhausted", "recursos", "Esperar liberacion de recursos")

    # Genericos
    UNKNOWN = ("unknown", "general", "Registrar y relanzar")

    def __init__(self, code: str, category: str, default_strategy: str):
        self._code = code
        self._category = category
        self._default_strategy = default_strategy

    @property
    def code(self) -> str:
        return self._code

    @property
    def category(self) -> str:
        return self._category

    @property
    def default_strategy(self) -> str:
        return self._default_strategy

    @classmethod
    def detect_from_exception(cls, exc: Exception) -> "ErrorPattern":
        """Detecta el patron de error a partir de una excepcion usando heuristica."""
        exc_type = type(exc).__qualname__
        exc_msg = str(exc).lower()
        exc_mod = getattr(exc, '__module__', '') or ''

        type_map: Dict[str, ErrorPattern] = {
            'ConnectionError': ErrorPattern.NETWORK_CONNECTION,
            'ConnectionRefusedError': ErrorPattern.NETWORK_CONNECTION,
            'ConnectionAbortedError': ErrorPattern.NETWORK_CONNECTION,
            'ConnectionResetError': ErrorPattern.NETWORK_CONNECTION,
            'TimeoutError': ErrorPattern.NETWORK_TIMEOUT,
            'FileNotFoundError': ErrorPattern.FILE_NOT_FOUND,
            'PermissionError': ErrorPattern.FILE_PERMISSION,
            'MemoryError': ErrorPattern.MEMORY_ERROR,
            'ImportError': ErrorPattern.IMPORT_ERROR,
            'ModuleNotFoundError': ErrorPattern.IMPORT_ERROR,
            'KeyError': ErrorPattern.STATE_ERROR,
            'ValueError': ErrorPattern.VALIDATION_ERROR,
            'TypeError': ErrorPattern.VALIDATION_ERROR,
            'AttributeError': ErrorPattern.STATE_ERROR,
            'IndexError': ErrorPattern.STATE_ERROR,
            'OSError': ErrorPattern.FILE_NOT_FOUND,
        }

        full_type = f"{exc_mod}.{exc_type}" if exc_mod else exc_type
        if full_type in type_map:
            return type_map[full_type]
        if exc_type in type_map:
            return type_map[exc_type]

        keyword_map: List[Tuple[List[str], ErrorPattern]] = [
            (['429', 'too many requests', 'rate limit', 'rate_limit'], ErrorPattern.RATE_LIMIT),
            (['timeout', 'timed out', 'connection timed'], ErrorPattern.NETWORK_TIMEOUT),
            (['dns', 'name resolution', 'name or service not known'], ErrorPattern.NETWORK_DNS),
            (['database is locked', 'database locked', 'locking protocol'], ErrorPattern.DATABASE_LOCKED),
            (['unique constraint', 'foreign key', 'integrity error'], ErrorPattern.DATABASE_INTEGRITY),
            (['no such table', 'no such column', 'database error'], ErrorPattern.DATABASE_CONNECTION),
            (['parse', 'unexpected token', 'syntax error'], ErrorPattern.PARSE_ERROR),
            (['json', 'decode', 'expect value'], ErrorPattern.JSON_DECODE),
            (['encoding', 'codec', "can't encode", "can't decode"], ErrorPattern.ENCODING_ERROR),
            (['permission denied', 'access denied', 'eacces'], ErrorPattern.FILE_PERMISSION),
            (['no such file', 'not found', 'does not exist', 'enoent'], ErrorPattern.FILE_NOT_FOUND),
            (['corrupt', 'bad file', 'invalid file'], ErrorPattern.FILE_CORRUPT),
            (['memory', 'out of memory', 'cannot allocate'], ErrorPattern.MEMORY_ERROR),
            (['too many open files', 'too many connections', 'resource temporarily'], ErrorPattern.RESOURCE_EXHAUSTED),
            (['deadlock', 'deadlock detected'], ErrorPattern.DEADLOCK_DETECTED),
            (['thread', "can't start new thread"], ErrorPattern.THREAD_ERROR),
            (['no module', 'module not found', 'import error', 'cannot import'], ErrorPattern.IMPORT_ERROR),
            (['dependency', 'missing', 'not installed'], ErrorPattern.DEPENDENCY_MISSING),
            (['config', 'configuration', 'setting'], ErrorPattern.CONFIG_ERROR),
            (['invalid', 'validation', 'not valid'], ErrorPattern.VALIDATION_ERROR),
            (['state', 'unexpected', 'illegal state'], ErrorPattern.STATE_ERROR),
            (['api', 'endpoint', 'http', 'response'], ErrorPattern.API_ERROR),
        ]

        for keywords, pattern in keyword_map:
            if any(kw in exc_msg for kw in keywords):
                return pattern

        return ErrorPattern.UNKNOWN


# ============================================================
# Data Classes
# ============================================================


@dataclass
class ErrorSignature:
    """Fingerprint unico de un error (hash criptografico del contexto)."""
    exception_type: str
    exception_message: str
    module: str
    function: str
    pattern: str
    hash: str = field(init=False)

    def __post_init__(self):
        raw = f"{self.exception_type}:{self.exception_message}:{self.module}:{self.function}:{self.pattern}"
        self.hash = hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class ErrorRecord:
    """Registro completo de un error en el knowledge base."""
    signature_hash: str
    exception_type: str
    exception_message: str
    module: str
    function: str
    pattern: str
    pattern_category: str
    occurrence_count: int
    first_seen: str
    last_seen: str
    resolved: bool
    resolution_strategy: Optional[str]
    context_hint: Optional[str]
    stacktrace_sample: Optional[str]
    source_file: Optional[str]
    source_line: Optional[int]


# ============================================================
# METACLASE: ErrorKnowledgeMeta
# ============================================================


class ErrorKnowledgeMeta(type):
    """
    Metaclase que auto-registra manejadores de error y wrappers.
    Basado en: Python Data Model - __new__, __init__, __call__
    """

    def __new__(mcs, name: str, bases: Tuple[type, ...], namespace: dict):
        namespace['__error_handlers__'] = {}
        namespace['__error_stats__'] = {}
        namespace['__error_patterns__'] = set()
        cls = super().__new__(mcs, name, bases, namespace)
        if not name.startswith('_'):
            _METACLASS_REGISTRY[name] = cls
        return cls

    def __init__(cls, name: str, bases: Tuple[type, ...], namespace: dict):
        super().__init__(name, bases, namespace)

    def __call__(cls, *args, **kwargs):
        """Intercepta la creacion de instancias para wrappear metodos."""
        instance = super().__call__(*args, **kwargs)
        for attr_name in dir(cls):
            if attr_name.startswith('_'):
                continue
            attr = cls.__dict__.get(attr_name)
            if attr is not None and callable(attr) and hasattr(attr, '_auto_handle'):
                wrapped = cls._wrap_with_resolution(attr, attr_name)
                setattr(instance, attr_name, wrapped.__get__(instance, cls))
        return instance

    @staticmethod
    def _wrap_with_resolution(method: Callable, name: str) -> Callable:
        """Envuelve un metodo con logica de auto-resolucion."""
        import functools

        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except Exception as exc:
                instance = getattr(method, '__self__', None) or (args[0] if args else None)
                module = type(instance).__module__ if instance else 'unknown'
                func_name = f"{type(instance).__qualname__}.{name}" if instance else name
                pattern = ErrorPattern.detect_from_exception(exc)
                from app.core.error_knowledge_registry import error_kb
                record = error_kb.register_error(exc, module=module, function=func_name, pattern=pattern)
                if error_kb.is_recurring(exc, module, func_name, threshold=2):
                    strategy = pattern.default_strategy
                    from app.core.error_auto_resolver import apply_strategy
                    logger.info("[META-RESOLVE] Error recurrente en %s - aplicando '%s'", func_name, strategy)
                    try:
                        return apply_strategy(strategy, method, args, kwargs, exc, record)
                    except Exception:
                        raise exc
                raise exc
        return wrapper


_METACLASS_REGISTRY: Dict[str, type] = {}


# ============================================================
# Decorador: auto_handle
# ============================================================


def auto_handle(func: Callable):
    """Decorador para marcar metodos que deben ser wrappeado con auto-resolucion."""
    func._auto_handle = True
    return func


# ============================================================
# SINGLETON: ErrorKnowledgeRegistry
# ============================================================


class ErrorKnowledgeRegistry(metaclass=ErrorKnowledgeMeta):
    """
    Singleton - Biblioteca de errores con memoria + metaclases + reflection.
    Primera vez: registra. Segunda vez: reconoce y aplica solucion.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: Optional[str] = None, memory_dir: Optional[str] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True

        if db_path is None:
            try:
                from app.config.path_manager import PathManager
                paths = PathManager.get_paths()
                db_path = str(paths['db'])
            except Exception:
                db_path = 'data/dropshipping_suite.db'
        if memory_dir is None:
            memory_dir = str(PathLib('governance/memory'))

        self.db_path = db_path
        self.memory_dir = PathLib(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self._cache: Dict[str, ErrorRecord] = {}
        self._session_counts: Dict[str, int] = {}
        self._pattern_strategies: Dict[ErrorPattern, str] = {}
        self._custom_resolvers: Dict[str, Callable] = {}

        self._init_db()
        self._load_cache()

        logger.info(
            "[ERR_KB] ErrorKnowledgeRegistry v2.0 inicializado | %d errores conocidos | %d patrones disponibles",
            len(self._cache), len(ErrorPattern)
        )

    def _init_db(self):
        """Crea tabla error_knowledge si no existe."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS error_knowledge (
                    signature_hash TEXT PRIMARY KEY,
                    exception_type TEXT NOT NULL,
                    exception_message TEXT,
                    module TEXT,
                    function TEXT,
                    pattern TEXT DEFAULT 'unknown',
                    pattern_category TEXT DEFAULT 'general',
                    occurrence_count INTEGER DEFAULT 1,
                    first_seen TEXT,
                    last_seen TEXT,
                    resolved INTEGER DEFAULT 0,
                    resolution_strategy TEXT,
                    context_hint TEXT,
                    stacktrace_sample TEXT,
                    source_file TEXT,
                    source_line INTEGER
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_error_knowledge_type ON error_knowledge(exception_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_error_knowledge_module ON error_knowledge(module)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_error_knowledge_pattern ON error_knowledge(pattern)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_error_knowledge_resolved ON error_knowledge(resolved)")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("[ERR_KB] Error inicializando BD: %s", e)

    def _load_cache(self):
        """Carga todos los errores conocidos a cache en memoria."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM error_knowledge")
            for row in cursor.fetchall():
                record = ErrorRecord(
                    signature_hash=row['signature_hash'],
                    exception_type=row['exception_type'],
                    exception_message=row['exception_message'] or '',
                    module=row['module'] or '',
                    function=row['function'] or '',
                    pattern=row['pattern'] or 'unknown',
                    pattern_category=row['pattern_category'] or 'general',
                    occurrence_count=row['occurrence_count'],
                    first_seen=row['first_seen'] or '',
                    last_seen=row['last_seen'] or '',
                    resolved=bool(row['resolved']),
                    resolution_strategy=row['resolution_strategy'],
                    context_hint=row['context_hint'],
                    stacktrace_sample=row['stacktrace_sample'],
                    source_file=row['source_file'],
                    source_line=row['source_line'],
                )
                self._cache[record.signature_hash] = record
            conn.close()
        except Exception as e:
            logger.error("[ERR_KB] Error cargando cache: %s", e)

    def _compute_signature(self, exc: Exception, module: str = '',
                           function: str = '',
                           pattern: Optional[ErrorPattern] = None) -> ErrorSignature:
        exc_type = type(exc).__qualname__
        exc_msg = str(exc)[:200]
        if pattern is None:
            pattern = ErrorPattern.detect_from_exception(exc)
        return ErrorSignature(
            exception_type=exc_type, exception_message=exc_msg,
            module=module, function=function, pattern=pattern.code,
        )

    def _get_stacktrace_sample(self) -> str:
        tb = traceback.format_exc()
        lines = tb.split('\n')
        return '\n'.join(lines[-10:]) if len(lines) > 10 else tb

    def _get_caller_info(self) -> Tuple[Optional[str], Optional[int]]:
        try:
            stack = inspect.stack()
            this_file = __file__
            for frame_info in stack[2:]:
                if frame_info.filename != this_file and 'error_knowledge' not in frame_info.filename:
                    return frame_info.filename, frame_info.lineno
        except Exception:
            pass
        return None, None

    def register_error(self, exc: Exception, module: str = '', function: str = '',
                       context: Optional[Dict] = None,
                       pattern: Optional[ErrorPattern] = None) -> ErrorRecord:
        """Registra un error en el knowledge base con deteccion automatica de patron."""
        if not module or not function:
            caller_frame = self._get_caller_frame()
            if caller_frame:
                if not module:
                    module = caller_frame.f_globals.get('__name__', module)
                if not function:
                    function = caller_frame.f_code.co_name

        if pattern is None:
            pattern = ErrorPattern.detect_from_exception(exc)

        sig = self._compute_signature(exc, module, function, pattern)
        now = datetime.now(timezone.utc).isoformat()
        source_file, source_line = self._get_caller_info()

        self._session_counts[sig.hash] = self._session_counts.get(sig.hash, 0) + 1

        if sig.hash in self._cache:
            record = self._cache[sig.hash]
            record.occurrence_count += 1
            record.last_seen = now
            if source_file:
                record.source_file = source_file
                record.source_line = source_line
            self._update_db(record)
            logger.info("[ERR_KB] Error CONOCIDO: %s | %s | %d ocurrencias | Resuelto: %s",
                        sig.hash[:8], pattern.code, record.occurrence_count, record.resolved)
        else:
            record = ErrorRecord(
                signature_hash=sig.hash, exception_type=sig.exception_type,
                exception_message=sig.exception_message, module=sig.module,
                function=sig.function, pattern=pattern.code,
                pattern_category=pattern.category, occurrence_count=1,
                first_seen=now, last_seen=now, resolved=False,
                resolution_strategy=None,
                context_hint=json.dumps(context) if context else None,
                stacktrace_sample=self._get_stacktrace_sample(),
                source_file=source_file, source_line=source_line,
            )
            self._cache[sig.hash] = record
            self._insert_db(record)
            logger.info("[ERR_KB] Error NUEVO: %s | %s | %s:%s",
                        sig.hash[:8], pattern.code, sig.exception_type, sig.exception_message[:60])

        return record

    def find_error(self, exc: Exception, module: str = '', function: str = '') -> Optional[ErrorRecord]:
        pattern = ErrorPattern.detect_from_exception(exc)
        sig = self._compute_signature(exc, module, function, pattern)
        return self._cache.get(sig.hash)

    def find_by_pattern(self, pattern: ErrorPattern) -> List[ErrorRecord]:
        return [r for r in self._cache.values() if r.pattern == pattern.code]

    def find_by_module(self, module: str) -> List[ErrorRecord]:
        return [r for r in self._cache.values() if r.module == module]

    def has_solution(self, exc: Exception, module: str = '', function: str = '') -> bool:
        record = self.find_error(exc, module, function)
        return record is not None and record.resolved and record.resolution_strategy is not None

    def get_solution(self, exc: Exception, module: str = '', function: str = '') -> Optional[str]:
        record = self.find_error(exc, module, function)
        if record and record.resolved and record.resolution_strategy:
            return record.resolution_strategy
        return None

    def get_pattern_solution(self, pattern: ErrorPattern) -> Optional[str]:
        return pattern.default_strategy

    def mark_resolved(self, exc: Exception, module: str = '', function: str = '',
                      strategy: str = '', context: Optional[Dict] = None) -> bool:
        pattern = ErrorPattern.detect_from_exception(exc)
        sig = self._compute_signature(exc, module, function, pattern)
        if sig.hash not in self._cache:
            return False
        record = self._cache[sig.hash]
        record.resolved = True
        record.resolution_strategy = strategy
        if context:
            record.context_hint = json.dumps(context)
        self._update_db(record)
        logger.info("[ERR_KB] Error RESUELTO: %s | Estrategia: %s", sig.hash[:8], strategy[:60])
        return True

    def is_recurring(self, exc: Exception, module: str = '', function: str = '', threshold: int = 2) -> bool:
        pattern = ErrorPattern.detect_from_exception(exc)
        sig = self._compute_signature(exc, module, function, pattern)
        return self._session_counts.get(sig.hash, 0) >= threshold

    def set_pattern_strategy(self, pattern: ErrorPattern, strategy: str):
        self._pattern_strategies[pattern] = strategy
        logger.info("[ERR_KB] Estrategia personalizada para patron '%s': %s", pattern.code, strategy)

    def register_custom_resolver(self, name: str, resolver: Callable):
        self._custom_resolvers[name] = resolver
        logger.info("[ERR_KB] Resolver personalizado registrado: %s", name)

    def get_stats(self) -> Dict:
        total = len(self._cache)
        resolved = sum(1 for r in self._cache.values() if r.resolved)
        by_type: Dict[str, int] = {}
        by_pattern: Dict[str, int] = {}
        by_module: Dict[str, int] = {}
        for r in self._cache.values():
            by_type[r.exception_type] = by_type.get(r.exception_type, 0) + 1
            by_pattern[r.pattern] = by_pattern.get(r.pattern, 0) + 1
            by_module[r.module or 'unknown'] = by_module.get(r.module or 'unknown', 0) + 1
        return {
            'total_known_errors': total, 'resolved_errors': resolved,
            'unresolved_errors': total - resolved,
            'session_errors_logged': sum(self._session_counts.values()),
            'by_exception_type': by_type, 'by_pattern': by_pattern, 'by_module': by_module,
            'patterns_available': len(ErrorPattern),
            'metaclass_registry_size': len(_METACLASS_REGISTRY),
        }

    def get_all_known(self) -> List[ErrorRecord]:
        return list(self._cache.values())

    def clear_session_counts(self):
        self._session_counts.clear()

    def get_pattern_breakdown(self) -> Dict[str, List[Dict]]:
        result: Dict[str, List[Dict]] = {}
        for record in self._cache.values():
            if record.pattern not in result:
                result[record.pattern] = []
            result[record.pattern].append(asdict(record))
        return result

    @staticmethod
    def _get_caller_frame():
        try:
            frame = inspect.currentframe()
            this_file = __file__
            while frame:
                if (frame.f_code.co_filename != this_file and
                    'error_knowledge' not in frame.f_code.co_filename and
                    'error_auto_resolver' not in frame.f_code.co_filename):
                    return frame
                frame = frame.f_back
        except Exception:
            pass
        return None

    @staticmethod
    def inspect_function(func: Callable) -> Dict:
        try:
            sig = inspect.signature(func)
            src = inspect.getsource(func)
            doc = inspect.getdoc(func)
            module = inspect.getmodule(func)
            return {
                'name': func.__name__,
                'module': module.__name__ if module else 'unknown',
                'signature': str(sig), 'params': list(sig.parameters.keys()),
                'docstring': doc, 'source_lines': len(src.split('\n')) if src else 0,
            }
        except Exception as e:
            return {'name': func.__name__, 'error': str(e)}

    def _insert_db(self, record: ErrorRecord):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO error_knowledge
                (signature_hash, exception_type, exception_message, module, function,
                 pattern, pattern_category, occurrence_count, first_seen, last_seen,
                 resolved, resolution_strategy, context_hint, stacktrace_sample,
                 source_file, source_line)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (record.signature_hash, record.exception_type, record.exception_message,
                  record.module, record.function, record.pattern, record.pattern_category,
                  record.occurrence_count, record.first_seen, record.last_seen,
                  int(record.resolved), record.resolution_strategy,
                  record.context_hint, record.stacktrace_sample,
                  record.source_file, record.source_line))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("[ERR_KB] Error insertando en BD: %s", e)

    def _update_db(self, record: ErrorRecord):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                UPDATE error_knowledge SET
                    occurrence_count = ?, last_seen = ?, resolved = ?,
                    resolution_strategy = ?, context_hint = ?,
                    stacktrace_sample = ?, source_file = ?, source_line = ?
                WHERE signature_hash = ?
            """, (record.occurrence_count, record.last_seen, int(record.resolved),
                  record.resolution_strategy, record.context_hint,
                  record.stacktrace_sample, record.source_file, record.source_line,
                  record.signature_hash))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("[ERR_KB] Error actualizando BD: %s", e)

    def export_to_json(self, filepath: Optional[str] = None) -> str:
        if filepath is None:
            filepath = str(self.memory_dir / 'error_memory.json')
        data = {
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'version': '2.0', 'stats': self.get_stats(),
            'patterns_available': [p.code for p in ErrorPattern],
            'errors': [asdict(r) for r in self._cache.values()],
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("[ERR_KB] Knowledge base exportado a: %s", filepath)
        return filepath

    def export_pattern_report(self, filepath: Optional[str] = None) -> str:
        if filepath is None:
            filepath = str(self.memory_dir / 'error_pattern_report.json')
        breakdown = self.get_pattern_breakdown()
        report = {'exported_at': datetime.now(timezone.utc).isoformat(),
                  'total_patterns_detected': len(breakdown), 'patterns': {}}
        for pattern_code, records in breakdown.items():
            report['patterns'][pattern_code] = {
                'count': len(records),
                'errors': [{'hash': r['signature_hash'][:8], 'type': r['exception_type'],
                            'module': r['module'], 'function': r['function'],
                            'occurrences': r['occurrence_count'], 'resolved': r['resolved']}
                           for r in records],
            }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("[ERR_KB] Pattern report exportado a: %s", filepath)
        return filepath


# ============================================================
# Instancia singleton para import directo
# ============================================================
error_kb = ErrorKnowledgeRegistry()
