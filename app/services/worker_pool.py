"""
worker_pool.py — Pool de Workers Paralelos para GEM OS
=======================================================
Orquestación concurrente de descargas y procesamiento de videos
con ThreadPoolExecutor, cola de tareas, reporte de progreso y
apagado graceful.

Complejidad:
  Temporal (enqueue): O(1) amortizado usando deque
  Temporal (ejecución): O(n * t) donde n = tareas, t = tiempo por tarea
  Espacial: O(n) para cola de tareas y futuros

Referencias:
  [concurrent.futures] ThreadPoolExecutor con submit()/shutdown()
  [PEP 343]   Context manager via __enter__/__exit__ para cleanup
  [PEP 391]   logging.getLogger(__name__) para trazabilidad
  [PEP 484]   Type hints en todas las funciones públicas
  [PEP 557]   @dataclass + field() para modelo Task
  [Threading Docs] threading.Lock para acceso thread-safe
  [Queue Docs] queue.Queue como base para TaskQueue
  [Big-O]     Ver PROGRAMMING_STANDARDS.md sección 3
  [SOLID-SRP] WorkerPool: gestión de workers; TaskQueue: cola

Uso (desarrollo):
    pool = WorkerPool(max_workers=3)
    pool.submit(descargar_video, video_id="abc")
    results = pool.wait_completion()
"""

import queue
import threading
import time
import logging
import random
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Modelos
# ═══════════════════════════════════════════════════════════════════════════


class TaskStatus(Enum):
    """Estados posibles de una tarea en el pool."""
    PENDING = "Pendiente"
    RUNNING = "Ejecutando"
    COMPLETED = "Completado"
    FAILED = "Fallido"
    CANCELLED = "Cancelado"


@dataclass
class Task:
    """Representa una unidad de trabajo dentro del pool."""
    id: str
    fn: Callable
    args: Tuple[Any, ...] = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Más alto = más prioritario
    max_retries: int = 2
    retry_delay_base: float = 2.0
    depends_on: List[str] = field(default_factory=list)  # IDs de tareas hijas

    # Estado interno (no tocar manualmente)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    attempts: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    _future: Optional[Future] = None

    @property
    def elapsed(self) -> Optional[float]:
        """Segundos transcurridos desde que empezó (si está en ejecución o terminó)."""
        if self.started_at is None:
            return None
        end = self.finished_at if self.finished_at else time.time()
        return end - self.started_at


class TaskQueue:
    """Cola thread-safe con soporte de prioridades y dependencias."""

    def __init__(self):
        self._lock = threading.Lock()
        self._tasks: Dict[str, Task] = {}
        self._pending: List[str] = []  # IDs ordenados por prioridad

    def put(self, task: Task) -> None:
        """Agrega una tarea a la cola."""
        with self._lock:
            self._tasks[task.id] = task
            self._pending.append(task.id)
            self._pending.sort(key=lambda tid: self._tasks[tid].priority, reverse=True)

    def get_ready(self) -> Optional[Task]:
        """Retorna la siguiente tarea lista (dependencias resueltas) o None."""
        with self._lock:
            for tid in self._pending:
                task = self._tasks[tid]
                if task.depends_on:
                    all_done = all(
                        dep_id in self._tasks
                        and (self._tasks[dep_id].status == TaskStatus.COMPLETED
                             or self._tasks[dep_id].status == TaskStatus.FAILED)
                        for dep_id in task.depends_on
                    )
                    if not all_done:
                        continue
                self._pending.remove(tid)
                return task
            return None

    def peek(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status != TaskStatus.PENDING:
                return False
            task.status = TaskStatus.CANCELLED
            if task_id in self._pending:
                self._pending.remove(task_id)
            return True

    def cancel_all_pending(self) -> int:
        count = 0
        with self._lock:
            for tid in list(self._pending):
                self._tasks[tid].status = TaskStatus.CANCELLED
                count += 1
            self._pending.clear()
        return count

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    @property
    def all_tasks(self) -> Dict[str, Task]:
        with self._lock:
            return dict(self._tasks)

    @property
    def stats(self) -> Dict[str, int]:
        counts = {s.value: 0 for s in TaskStatus}
        with self._lock:
            for t in self._tasks.values():
                counts[t.status.value] = counts.get(t.status.value, 0) + 1
        return counts


# ═══════════════════════════════════════════════════════════════════════════
# Pool de Workers
# ═══════════════════════════════════════════════════════════════════════════


class WorkerPool:
    """
    Pool de workers paralelos para descarga/procesamiento simultáneo.
    Características: ThreadPoolExecutor, cola con prioridades,
    callbacks de progreso, reintento automático, graceful shutdown.
    """

    def __init__(
        self,
        max_workers: int = 3,
        task_timeout: Optional[float] = None,
        on_task_complete: Optional[Callable[[Task], None]] = None,
        on_batch_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        graceful_timeout: float = 30.0,
        thread_name_prefix: str = "WorkerPool",
    ):
        self.max_workers = max_workers
        self.task_timeout = task_timeout
        self.on_task_complete = on_task_complete
        self.on_batch_complete = on_batch_complete
        self.graceful_timeout = graceful_timeout
        self.thread_name_prefix = thread_name_prefix
        self._task_queue = TaskQueue()
        self._executor: Optional[ThreadPoolExecutor] = None
        self._dispatch_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._completed_count = 0
        self._failed_count = 0

    # ── Gestión del ciclo de vida ─────────────────────────────────────────

    def start(self) -> None:
        """Inicia el pool: crea el executor y lanza el hilo despachador."""
        if self._running:
            return
        self._running = True
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix=self.thread_name_prefix,
        )
        self._dispatch_thread = threading.Thread(
            target=self._dispatch_loop,
            daemon=True,
        )
        self._dispatch_thread.start()
        logger.info("[WORKER_POOL] Pool iniciado (%d workers)", self.max_workers)

    def stop(self, cancel_pending: bool = True) -> Dict[str, Any]:
        """Detiene el pool de forma graceful."""
        if not self._running:
            return self._summary()
        logger.info("[WORKER_POOL] Deteniendo pool (graceful)...")
        if cancel_pending:
            cancelled = self._task_queue.cancel_all_pending()
            logger.info("[WORKER_POOL] %d pendientes canceladas.", cancelled)
        self._running = False
        if self._dispatch_thread and self._dispatch_thread.is_alive():
            self._dispatch_thread.join(timeout=self.graceful_timeout)
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=False)
            self._executor = None
        summary = self._summary()
        logger.info("[WORKER_POOL] Pool detenido.")
        return summary

    def submit(
        self,
        fn: Callable,
        *args,
        task_id: Optional[str] = None,
        priority: int = 0,
        max_retries: int = 2,
        depends_on: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        """Encola una tarea para ejecución asíncrona."""
        if not self._running:
            self.start()
        tid = task_id or f"task_{int(time.time() * 1000)}_{random.randrange(1000)}"
        task = Task(
            id=tid, fn=fn, args=args, kwargs=kwargs,
            priority=priority, max_retries=max_retries,
            depends_on=depends_on or [],
        )
        self._task_queue.put(task)
        logger.debug("[WORKER_POOL] Tarea encolada: %s (prioridad=%d)", tid, priority)
        return tid

    def wait_completion(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Bloquea hasta que todas las tareas finalicen."""
        start = time.time()
        while True:
            stats = self._task_queue.stats
            active = stats.get(TaskStatus.RUNNING.value, 0)
            pending = stats.get(TaskStatus.PENDING.value, 0)
            if active == 0 and pending == 0:
                break
# ── Bucle Interno ─────────────────────────────────────────────────────

    def _dispatch_loop(self) -> None:
        """Hilo despachador: toma tareas de la cola y las envía al executor."""
        while self._running:
            try:
                task = self._task_queue.get_ready()
                if task is None:
                    time.sleep(0.1)
                    continue
                if not self._running:
                    return
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                future = self._executor.submit(self._run_task_with_retry, task)
                task._future = future
                future.add_done_callback(self._on_future_done)
            except Exception as exc:
                logger.error("[WORKER_POOL] Error en dispatch: %s", exc)
                time.sleep(0.5)

    def _run_task_with_retry(self, task: Task) -> Any:
        """Ejecuta la tarea con reintento interno."""
        while task.attempts <= task.max_retries:
            try:
                result = task.fn(*task.args, **task.kwargs)
                task.result = result
                task.status = TaskStatus.COMPLETED
                return result
            except Exception as exc:
                task.attempts += 1
                if task.attempts > task.max_retries:
                    task.status = TaskStatus.FAILED
                    task.error = f"{type(exc).__name__}: {exc}"
                    raise
                delay = task.retry_delay_base * (2 ** (task.attempts - 1))
                jitter = delay * random.uniform(-0.25, 0.25)
                time.sleep(max(0.5, delay + jitter))
        return None

    def _on_future_done(self, future: Future) -> None:
        """Callback cuando un Future completa."""
        task = None
        for t in self._task_queue.all_tasks.values():
            if t._future is future:
                task = t
                break
        if task is None:
            return
        task.finished_at = time.time()
        if task.status == TaskStatus.COMPLETED:
            with self._lock:
                self._completed_count += 1
        elif task.status == TaskStatus.FAILED:
            with self._lock:
                self._failed_count += 1
        if self.on_task_complete:
            try:
                self.on_task_complete(task)
            except Exception as exc:
                logger.error("[WORKER_POOL] Error en on_task_complete: %s", exc)
        stats = self._task_queue.stats
        if (self.on_batch_complete
            and stats.get(TaskStatus.RUNNING.value, 0) == 0
            and stats.get(TaskStatus.PENDING.value, 0) == 0):
            try:
                self.on_batch_complete(self._summary())
            except Exception as exc:
                logger.error(
                    "[WORKER_POOL] Error en on_batch_complete: %s",
                    exc,
                )

    def _summary(self) -> Dict[str, Any]:
        """Resumen actual de ejecución del pool."""
        stats = self._task_queue.stats
        return {
            "max_workers": self.max_workers,
            "total_completed": self._completed_count,
            "total_failed": self._failed_count,
            "by_status": stats,
            "is_running": self._running,
            "pending_count": self._task_queue.pending_count,
        }

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def completed_count(self) -> int:
        return self._completed_count

    @property
    def failed_count(self) -> int:
        return self._failed_count

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop(cancel_pending=True)
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════════════════════


def create_worker_pool(
    max_workers: int = 3,
    on_task_complete: Optional[Callable] = None,
    on_batch_complete: Optional[Callable] = None,
) -> WorkerPool:
    """Crea un WorkerPool pre-configurado para descarga/procesamiento."""
    return WorkerPool(
        max_workers=max_workers,
        on_task_complete=on_task_complete,
        on_batch_complete=on_batch_complete,
        thread_name_prefix="GEM-Worker",
    )