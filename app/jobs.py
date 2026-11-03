from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
from pathlib import Path
from queue import Full, Queue
from uuid import uuid4

import yt_dlp

ROOT = Path(os.environ.get("MP3DOWNLOAD_DIR", "downloads")).resolve()
LOCAL_FFMPEG = Path(__file__).resolve().parents[1] / ".tools" / "ffmpeg"
ROOT.mkdir(parents=True, exist_ok=True)
QUEUE: Queue[str] = Queue(maxsize=20)
LOCK = threading.RLock()
JOBS: dict[str, dict] = {}
STARTED = False
LOG = logging.getLogger(__name__)


def _save(job: dict) -> None:
    folder = ROOT / job["id"]
    folder.mkdir(exist_ok=True)
    target = folder / "job.json"
    temp = folder / "job.json.tmp"
    temp.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, target)


def snapshot(job_id: str) -> dict | None:
    with LOCK:
        job = JOBS.get(job_id)
        return dict(job) if job else None


def latest() -> dict | None:
    with LOCK:
        paths = sorted(ROOT.glob("*/job.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for path in paths:
            job = JOBS.get(path.parent.name)
            if job:
                return dict(job)
    return None


def update(job_id: str, **changes: object) -> None:
    with LOCK:
        job = JOBS[job_id]
        job.update(changes)
        _save(job)


def create(url: str, playlist: bool) -> dict:
    local_tools = all((LOCAL_FFMPEG / name).is_file() for name in ("ffmpeg.exe", "ffprobe.exe"))
    if not local_tools and (not shutil.which("ffmpeg") or not shutil.which("ffprobe")):
        raise RuntimeError("Instale FFmpeg e FFprobe no PATH ou em .tools/ffmpeg/.")
    job = {"id": uuid4().hex, "url": url, "playlist": playlist,
           "status": "na_fila", "percent": 0, "title": "", "files": [], "error": ""}
    with LOCK:
        try:
            QUEUE.put_nowait(job["id"])
        except Full as exc:
            raise OverflowError("A fila está cheia. Tente novamente em alguns minutos.") from exc
        JOBS[job["id"]] = job
        try:
            _save(job)
        except OSError:
            JOBS.pop(job["id"], None)
            raise
    return dict(job)


def _process(job_id: str) -> None:
    folder = ROOT / job_id
    last_progress = 0.0

    def progress(data: dict) -> None:
        nonlocal last_progress
        if data.get("status") != "downloading":
            return
        now = time.monotonic()
        if now - last_progress < 1:
            return
        last_progress = now
        total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
        percent = round(100 * data.get("downloaded_bytes", 0) / total) if total else 0
        update(job_id, percent=min(percent, 100), status="baixando")

    def postprocess(data: dict) -> None:
        if data.get("status") == "started":
            update(job_id, status="convertendo", percent=100)

    job = snapshot(job_id)
    if job is None:
        return
    options = {
        "format": "bestaudio/best",
        "outtmpl": str(folder / "%(title).120B [%(id)s].%(ext)s"),
        "paths": {"temp": str(folder)},
        "noplaylist": not job["playlist"],
        "playlistend": 100,
        "continuedl": True,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
        "socket_timeout": 20,
        "concurrent_fragment_downloads": 2,
        "download_archive": str(folder / "archive.txt"),
        "progress_hooks": [progress],
        "postprocessor_hooks": [postprocess],
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        "quiet": True,
        "no_warnings": True,
    }
    if all((LOCAL_FFMPEG / name).is_file() for name in ("ffmpeg.exe", "ffprobe.exe")):
        options["ffmpeg_location"] = str(LOCAL_FFMPEG)
    update(job_id, status="baixando", error="")
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            result = downloader.extract_info(job["url"], download=True)
        if result is None:
            raise RuntimeError("Nenhuma mídia disponível")
        files = sorted(path.name for path in folder.glob("*.mp3") if path.is_file())
        if not files:
            raise RuntimeError("Nenhum MP3 foi gerado")
        update(job_id, status="concluido", percent=100, files=files,
               title=result.get("title") or "Download concluído")
    except Exception:
        LOG.exception("Falha no download %s", job_id)
        files = sorted(path.name for path in folder.glob("*.mp3") if path.is_file())
        update(job_id, status="erro", files=files,
               error="O download falhou. Verifique o link e tente novamente.")


def _worker() -> None:
    while True:
        job_id = QUEUE.get()
        try:
            _process(job_id)
        except Exception:
            LOG.exception("Worker não conseguiu processar a tarefa %s", job_id)
        finally:
            QUEUE.task_done()


def start() -> None:
    global STARTED
    with LOCK:
        if STARTED:
            return
        for path in ROOT.glob("*/job.json"):
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
                if job["id"] != path.parent.name:
                    continue
                if job["status"] in {"na_fila", "baixando", "convertendo"}:
                    job["status"] = "na_fila"
                    QUEUE.put_nowait(job["id"])
                JOBS[job["id"]] = job
            except (ValueError, KeyError, Full, OSError):
                LOG.warning("Estado de tarefa ignorado: %s", path)
        threading.Thread(target=_worker, daemon=True, name="mp3-worker").start()
        STARTED = True
