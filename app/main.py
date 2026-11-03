from contextlib import asynccontextmanager
from pathlib import Path
import sys
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, field_validator

if __package__:
    from . import archive, jobs
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app import archive, jobs

PUBLIC = Path(__file__).parent / "static"
ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com",
                 "music.youtube.com", "youtu.be"}


class DownloadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    playlist: bool = False

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if len(value) > 2048 or any(char.isspace() for char in value):
            raise ValueError("Link inválido")
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
                or parsed.username or parsed.password or parsed.port):
            raise ValueError("Use um link HTTPS do YouTube")
        return value


@asynccontextmanager
async def lifespan(_: FastAPI):
    jobs.start()
    yield


app = FastAPI(title="mp3download", lifespan=lifespan)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(PUBLIC / "index.html")


@app.get("/static/app.css")
def css() -> FileResponse:
    return FileResponse(PUBLIC / "app.css", media_type="text/css")


@app.get("/static/app.js")
def js() -> FileResponse:
    return FileResponse(PUBLIC / "app.js", media_type="text/javascript")


@app.post("/api/jobs", status_code=202)
def create_job(request: DownloadRequest) -> dict:
    try:
        return jobs.create(request.url, request.playlist)
    except (RuntimeError, OverflowError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Falha ao salvar a tarefa") from exc


@app.get("/api/recent-job")
def recent_job() -> dict:
    job = jobs.latest()
    if job is None:
        raise HTTPException(status_code=404, detail="Nenhuma tarefa encontrada")
    return job


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = jobs.snapshot(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return job


@app.get("/api/jobs/{job_id}/files/{filename}")
def get_file(job_id: str, filename: str) -> FileResponse:
    job = jobs.snapshot(job_id)
    if job is None or filename not in job["files"]:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    path = jobs.ROOT / job_id / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(path, media_type="audio/mpeg", filename=filename)


@app.get("/api/jobs/{job_id}/archive")
def get_archive(job_id: str) -> StreamingResponse:
    job = jobs.snapshot(job_id)
    if job is None or job["status"] not in {"concluido", "erro"} or not job["files"]:
        raise HTTPException(status_code=404, detail="Arquivos não disponíveis")
    folder = jobs.ROOT / job_id
    paths = [folder / name for name in job["files"]]
    if any(path.parent != folder or not path.is_file() for path in paths):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return StreamingResponse(
        archive.stream_zip(paths),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="mp3download-{job_id[:8]}.zip"'},
    )


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
    )
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
