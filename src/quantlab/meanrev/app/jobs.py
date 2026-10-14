"""Background jobs for the terminal: walk-forward runs and trading re-runs.

Jobs run in a worker thread of the app process (the walk-forward itself fans
out to worker processes). The UI polls :func:`status`; a job can be asked to
stop, which takes effect at the next walk-forward step -- completed steps are
checkpointed, so the run can be resumed later.
"""
from __future__ import annotations

import logging
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from ..config import MRConfig

log = logging.getLogger(__name__)


@dataclass
class Job:
    kind: str
    state: str = "running"           # running | done | failed | stopped
    frac: float = 0.0
    message: str = "starting"
    started: float = field(default_factory=time.time)
    finished: float | None = None
    run_dir: str | None = None
    error: str | None = None
    history: list[str] = field(default_factory=list)
    stop: threading.Event = field(default_factory=threading.Event)


class JobManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.job: Job | None = None

    def busy(self) -> bool:
        return self.job is not None and self.job.state == "running"

    def _progress(self, job: Job):
        def cb(frac: float, msg: str) -> None:
            job.frac, job.message = float(frac), msg
            if not job.history or job.history[-1] != msg:
                job.history.append(f"{time.strftime('%H:%M:%S')}  {msg}")
                del job.history[:-200]
        return cb

    def start_run(self, cfg: MRConfig) -> Job:
        from .. import pipeline

        return self._start("walk-forward", lambda job: pipeline.run(cfg, progress=self._progress(job),
                                                                   stop_flag=job.stop.is_set))

    def start_trading(self, run_dir: Path, cfg: MRConfig) -> Job:
        from .. import pipeline

        return self._start("backtest", lambda job: pipeline.rerun_trading(run_dir, cfg, progress=self._progress(job)))

    def _start(self, kind: str, fn) -> Job:
        with self._lock:
            if self.busy():
                raise RuntimeError("a job is already running")
            job = Job(kind)
            self.job = job

        def target():
            try:
                out = fn(job)
                job.run_dir = str(out)
                job.state = "stopped" if job.stop.is_set() else "done"
                job.frac = 1.0
            except Exception as exc:  # noqa: BLE001 - surfaced in the UI
                job.state, job.error = "failed", f"{type(exc).__name__}: {exc}"
                job.history.append(traceback.format_exc(limit=3))
                log.exception("job failed")
            finally:
                job.finished = time.time()

        threading.Thread(target=target, daemon=True, name=f"job-{kind}").start()
        return job

    def request_stop(self) -> None:
        if self.job and self.busy():
            self.job.stop.set()


JOBS = JobManager()
