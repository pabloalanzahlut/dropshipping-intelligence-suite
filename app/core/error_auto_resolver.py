"""
error_auto_resolver.py - Decorators & Context Managers v2.0 (Avanzado)
============================================================================
Basado en:
  - PEP 318: Decorators for Functions and Methods
  - PEP 343: The "with" Statement
  - contextlib stdlib module
  - functools.wraps (PEP 378)
  - inspect module (reflection)
  - ErrorKnowledgeMeta (metaclase)

Proposito:
  Decoradores que interceptan errores, consultan el ErrorKnowledgeRegistry
  y aplican soluciones automaticamente en la SEGUNDA ocurrencia.
  Incluye 7 estrategias de resolucion para errores comunes.

Uso:
    @remember_and_resolve()
    def mi_funcion():
        ...

    with auto_recovery():
        ...

    class MiClase(metaclass=ErrorKnowledgeMeta):
        @auto_handle
        def metodo(self):
            ...
"""

import functools
import inspect
import logging
import time
from typing import Callable, Optional, Type, Tuple, Dict, Any, List

from app.core.error_knowledge_registry import (
    error_kb, ErrorPattern, ErrorKnowledgeMeta, auto_handle,
)

logger = logging.getLogger(__name__)

# ============================================================
# ESTRATEGIAS DE RESOLUCION - 7 para errores comunes
# ============================================================

_RESOLUTION_STRATEGIES: Dict[str, Callable] = {}


def register_strategy(name: str):
    def decorator(func: Callable):
        _RESOLUTION_STRATEGIES[name] = func
        return func
    return decorator


@register_strategy('retry_once')
def _strategy_retry_once(func, args, kwargs, exc, record):
    """Reintenta la funcion una vez mas."""
    logger.info("[AUTO-RESOLVE] Estrategia 'retry_once': reintentando %s", func.__name__)
    return func(*args, **kwargs)


@register_strategy('retry_with_backoff')
def _strategy_retry_backoff(func, args, kwargs, exc, record):
    """Reintenta con espera de 2 segundos."""
    logger.info("[AUTO-RESOLVE] Estrategia 'retry_with_backoff': esperando 2 seg...")
    time.sleep(2)
    return func(*args, **kwargs)


@register_strategy('return_default')
def _strategy_return_default(func, args, kwargs, exc, record):
    """Retorna None y loggea el error (no critico)."""
    logger.warning("[AUTO-RESOLVE] Estrategia 'return_default': error no critico, retornando None")
    return None


@register_strategy('log_and_raise')
def _strategy_log_and_raise(func, args, kwargs, exc, record):
    """Loggea y relanza la excepcion (no hay recuperacion posible)."""
    logger.error("[AUTO-RESOLVE] Estrategia 'log_and_raise': error irrecuperable, relanzando")
    raise exc


@register_strategy('retry_exponential')
def _strategy_retry_exponential(func, args, kwargs, exc, record):
    """Reintenta hasta 3 veces con backoff exponencial (1, 2, 4 seg)."""
    max_attempts = 3
    last_exc = exc
    for attempt in range(max_attempts):
        delay = 2 ** attempt
        logger.info("[AUTO-RESOLVE] Estrategia 'retry_exponential': intento %d/%d, esperando %ds...",
                    attempt + 1, max_attempts, delay)
        time.sleep(delay)
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            logger.warning("[AUTO-RESOLVE] Reintento %d fallo: %s", attempt + 1, e)
    raise last_exc


@register_strategy('cache_and_continue')
def _strategy_cache_and_continue(func, args, kwargs, exc, record):
    """Cachea el error y continua la ejecucion retornando un placeholder."""
    logger.warning("[AUTO-RESOLVE] Estrategia 'cache_and_continue': error cacheado, continuando con placeholder")
    return {'_error_cached': True, '_error_type': type(exc).__name__}


@register_strategy('auto_reconnect')
def _strategy_auto_reconnect(func, args, kwargs, exc, record):
    """Para errores de conexion: espera 3 seg y reintenta 1 vez."""
    logger.info("[AUTO-RESOLVE] Estrategia 'auto_reconnect': esperando 3 seg...")
    time.sleep(3)
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error("[AUTO-RESOLVE] Reconexion fallo: %s", e)
        raise e


# ============================================================
# MAPA: Patron de Error -> Estrategia por Defecto
# ============================================================

PATTERN_STRATEGY_MAP: Dict[ErrorPattern, str] = {
    ErrorPattern.NETWORK_CONNECTION: 'auto_reconnect',
    ErrorPattern.NETWORK_TIMEOUT: 'retry_with_backoff',
    ErrorPattern.NETWORK_DNS: 'retry_exponential',
    ErrorPattern.RATE_LIMIT: 'retry_exponential',
    ErrorPattern.API_ERROR: 'retry_with_backoff',
    ErrorPattern.DATABASE_CONNECTION: 'auto_reconnect',
    ErrorPattern.DATABASE_LOCKED: 'retry_exponential',
    ErrorPattern.DATABASE_INTEGRITY: 'log_and_raise',
    ErrorPattern.FILE_NOT_FOUND: 'return_default',
    ErrorPattern.FILE_PERMISSION: 'log_and_raise',
    ErrorPattern.FILE_CORRUPT: 'log_and_raise',
    ErrorPattern.PARSE_ERROR: 'cache_and_continue',
    ErrorPattern.JSON_DECODE: 'cache_and_continue',
    ErrorPattern.ENCODING_ERROR: 'cache_and_continue',
    ErrorPattern.VALIDATION_ERROR: 'return_default',
    ErrorPattern.STATE_ERROR: 'retry_once',
    ErrorPattern.CONFIG_ERROR: 'log_and_raise',
    ErrorPattern.THREAD_ERROR: 'retry_once',
    ErrorPattern.DEADLOCK_DETECTED: 'retry_exponential',
    ErrorPattern.DEPENDENCY_MISSING: 'log_and_raise',
    ErrorPattern.IMPORT_ERROR: 'log_and_raise',
    ErrorPattern.MEMORY_ERROR: 'log_and_raise',
    ErrorPattern.RESOURCE_EXHAUSTED: 'retry_exponential',
    ErrorPattern.UNKNOWN: 'log_and_raise',
}


# ============================================================
# Decorador: @remember_and_resolve (v2 con soporte de patrones)
# ============================================================


def remember_and_resolve(
    max_retries: int = 2,
    module: str = '',
    strategies: Optional[Dict[str, str]] = None,
    auto_mark_resolved: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    use_pattern_detection: bool = True,
):
    """
    Decorador que intercepta errores y los resuelve automaticamente.

    Primera vez: registra el error en el knowledge base, relanza.
    Segunda vez: reconoce el error, aplica estrategia, NO relanza.

    v2.0: Soporte para deteccion de patrones (ErrorPattern) + 7 estrategias.
    """
    if retryable_exceptions is None:
        retryable_exceptions = (Exception,)

    def decorator(func: Callable):
        func_module = module or getattr(func, '__module__', 'unknown')
        func_name = func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except retryable_exceptions as exc:
                    last_exc = exc

                    pattern = None
                    if use_pattern_detection:
                        pattern = ErrorPattern.detect_from_exception(exc)

                    record = error_kb.register_error(
                        exc, module=func_module, function=func_name, pattern=pattern
                    )

                    strategy = None

                    if strategies and type(exc).__name__ in strategies:
                        strategy = strategies[type(exc).__name__]

                    if not strategy:
                        strategy = error_kb.get_solution(exc, func_module, func_name)

                    if not strategy and pattern and pattern in PATTERN_STRATEGY_MAP:
                        strategy = PATTERN_STRATEGY_MAP[pattern]

                    if not strategy and pattern:
                        strategy = error_kb._pattern_strategies.get(pattern)

                    if strategy and strategy in _RESOLUTION_STRATEGIES:
                        logger.info(
                            "[AUTO-RESOLVE] Aplicando estrategia '%s' para %s.%s (patron: %s)",
                            strategy, func_module, func_name,
                            pattern.code if pattern else 'N/A'
                        )
                        strategy_fn = _RESOLUTION_STRATEGIES[strategy]
                        try:
                            result = strategy_fn(func, args, kwargs, exc, record)
                            if auto_mark_resolved:
                                error_kb.mark_resolved(
                                    exc, func_module, func_name, strategy=strategy,
                                    context={'auto_resolved': True,
                                             'pattern': pattern.code if pattern else 'unknown',
                                             'attempt': attempt}
                                )
                            return result
                        except Exception:
                            raise exc

                    if error_kb.is_recurring(exc, func_module, func_name, threshold=2):
                        logger.info(
                            "[AUTO-RESOLVE] Error RECURRENTE en %s.%s - aplicando retry_once",
                            func_module, func_name
                        )
                        try:
                            result = _strategy_retry_once(func, args, kwargs, exc, record)
                            if auto_mark_resolved:
                                error_kb.mark_resolved(
                                    exc, func_module, func_name, strategy='retry_once',
                                    context={'auto_resolved': True, 'recurring': True, 'attempt': attempt}
                                )
                            return result
                        except Exception:
                            raise exc

                    if attempt < max_retries:
                        logger.warning(
                            "[AUTO-RESOLVE] Intento %d/%d fallo en %s.%s: %s",
                            attempt + 1, max_retries, func_module, func_name, exc
                        )
                        continue

                except Exception as exc:
                    raise exc

            logger.error("[AUTO-RESOLVE] Agotados %d intentos para %s.%s. Ultimo error: %s",
                         max_retries, func_module, func_name, last_exc)
            raise last_exc

        return wrapper
    return decorator


# ============================================================
# Decorador: @resolve_with_strategy
# ============================================================


def resolve_with_strategy(strategy: str = 'retry_once', **strategy_kwargs):
    """Decorador que fuerza una estrategia de resolucion especifica."""
    if strategy not in _RESOLUTION_STRATEGIES:
        raise ValueError(
            f"[AUTO-RESOLVE] Estrategia desconocida: '{strategy}'. "
            f"Disponibles: {list(_RESOLUTION_STRATEGIES.keys())}"
        )

    def decorator(func: Callable):
        func_module = getattr(func, '__module__', 'unknown')
        func_name = func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                pattern = ErrorPattern.detect_from_exception(exc)
                error_kb.register_error(exc, module=func_module, function=func_name, pattern=pattern)
                record = error_kb.find_error(exc, func_module, func_name)
                strategy_fn = _RESOLUTION_STRATEGIES[strategy]
                logger.info("[AUTO-RESOLVE] Aplicando estrategia forzada '%s' para %s.%s (patron: %s)",
                            strategy, func_module, func_name, pattern.code if pattern else 'N/A')
                return strategy_fn(func, args, kwargs, exc, record)

        return wrapper
    return decorator


# ============================================================
# Context Manager: auto_recovery
# ============================================================


class auto_recovery:
    """
    Context Manager para auto-recuperacion de errores.
    Basado en: PEP 343 (The 'with' Statement)
    """

    def __init__(self, module: str = '', strategy: str = 'retry_once',
                 max_attempts: int = 2, use_patterns: bool = True):
        self.module = module
        self.strategy = strategy
        self.max_attempts = max_attempts
        self.use_patterns = use_patterns
        self.recovered = False
        self.error_record = None
        self.error_pattern = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False
        if not issubclass(exc_type, Exception):
            return False

        pattern = None
        if self.use_patterns:
            pattern = ErrorPattern.detect_from_exception(exc_val)

        func_name = self._get_caller_name()
        record = error_kb.register_error(exc_val, module=self.module, function=func_name, pattern=pattern)
        self.error_record = record
        self.error_pattern = pattern

        solution = error_kb.get_solution(exc_val, self.module, func_name)
        if solution and solution in _RESOLUTION_STRATEGIES:
            logger.info("[AUTO-RECOVERY] Error conocido con solucion '%s': %s", solution, exc_val)
            self.recovered = True
            return True

        if pattern and pattern in PATTERN_STRATEGY_MAP:
            pattern_strategy = PATTERN_STRATEGY_MAP[pattern]
            if pattern_strategy in _RESOLUTION_STRATEGIES:
                logger.info("[AUTO-RECOVERY] Error con patron '%s' -> estrategia '%s': %s",
                            pattern.code, pattern_strategy, exc_val)
                self.recovered = True
                return True

        if error_kb.is_recurring(exc_val, self.module, func_name, threshold=2):
            logger.info("[AUTO-RECOVERY] Error recurrente suprimido: %s", exc_val)
            self.recovered = True
            return True

        logger.warning("[AUTO-RECOVERY] Error sin solucion conocida (1ra ocurrencia): %s", exc_val)
        return False

    @staticmethod
    def _get_caller_name() -> str:
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            return frame.f_back.f_back.f_code.co_name
        return 'unknown'


# ============================================================
# Decorador: @auto_resolve_class
# ============================================================


def auto_resolve_class(strategy: str = 'retry_once', use_patterns: bool = True):
    """Decorador de clase que envuelve TODOS los metodos publicos con auto-resolucion."""
    def decorator(cls: type) -> type:
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith('_'):
                continue
            wrapped = remember_and_resolve(
                max_retries=2, module=getattr(cls, '__module__', 'unknown'),
                use_pattern_detection=use_patterns,
            )(method)
            setattr(cls, name, wrapped)
        logger.info("[AUTO-RESOLVE] Clase '%s' envuelta con auto-resolucion (estrategia base: %s, patrones: %s)",
                    cls.__name__, strategy, use_patterns)
        return cls
    return decorator


# ============================================================
# Decorador: @auto_resolve_method
# ============================================================


def auto_resolve_method(strategy: str = 'retry_once'):
    """Decorador para metodos de clase que necesitan auto-resolucion."""
    def decorator(method: Callable):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            func_module = type(self).__module__
            func_name = f"{type(self).__qualname__}.{method.__name__}"
            try:
                return method(self, *args, **kwargs)
            except Exception as exc:
                pattern = ErrorPattern.detect_from_exception(exc)
                error_kb.register_error(exc, module=func_module, function=func_name, pattern=pattern)
                if error_kb.is_recurring(exc, func_module, func_name, threshold=2):
                    effective_strategy = strategy
                    if pattern and pattern in PATTERN_STRATEGY_MAP:
                        effective_strategy = PATTERN_STRATEGY_MAP[pattern]
                    logger.info("[AUTO-RESOLVE] Error recurrente en metodo %s - aplicando '%s' (patron: %s)",
                                func_name, effective_strategy, pattern.code if pattern else 'N/A')
                    if effective_strategy in _RESOLUTION_STRATEGIES:
                        record = error_kb.find_error(exc, func_module, func_name)
                        return _RESOLUTION_STRATEGIES[effective_strategy](
                            method, (self,) + args, kwargs, exc, record
                        )
                raise exc
        return wrapper
    return decorator


# ============================================================
# Helper: apply_strategy
# ============================================================


def apply_strategy(strategy_name: str, func: Callable,
                   args: tuple = (), kwargs: Optional[Dict] = None,
                   exc: Optional[Exception] = None,
                   record=None) -> Any:
    """Aplica una estrategia de resolucion programaticamente."""
    if strategy_name not in _RESOLUTION_STRATEGIES:
        raise ValueError(
            f"[AUTO-RESOLVE] Estrategia desconocida: '{strategy_name}'. "
            f"Disponibles: {list(_RESOLUTION_STRATEGIES.keys())}"
        )
    if kwargs is None:
        kwargs = {}
    return _RESOLUTION_STRATEGIES[strategy_name](func, args, kwargs, exc, record)


# ============================================================
# Helpers de introspeccion
# ============================================================


def get_available_strategies() -> List[str]:
    """Retorna la lista de estrategias de resolucion disponibles."""
    return list(_RESOLUTION_STRATEGIES.keys())


def get_strategy_description(strategy_name: str) -> Optional[str]:
    """Retorna la descripcion/docstring de una estrategia."""
    if strategy_name not in _RESOLUTION_STRATEGIES:
        return None
    return inspect.getdoc(_RESOLUTION_STRATEGIES[strategy_name])


# ============================================================
# Excepcion base del modulo
# ============================================================


class AutoResolveError(Exception):
    """Excepcion base para errores del sistema de auto-resolucion."""
    pass