# Estado do projeto

## Arquivos

- `app/jobs.py`: fila, persistência JSON, worker e yt-dlp.
- `app/main.py`: FastAPI, validação, rotas e headers.
- `app/archive.py`: transmissão de ZIP com fila limitada e sem arquivo temporário.
- `app/main.py` pode iniciar via `python app/main.py` ou como módulo Uvicorn.
- `app/static/`: HTML, CSS e JavaScript da interface.
- `downloads/{id}/`: `job.json`, `archive.txt`, arquivos parciais e MP3.
- `requirements.txt`, `.gitignore`, `README.md`, `roadmap.md`.
- `scripts/install_ffmpeg.ps1`: instalador Windows com verificação SHA256.
- `.tools/ffmpeg/`: binários portáteis locais (ignorados pelo Git).

## Contratos

- `POST /api/jobs`: entrada `{url: str HTTPS YouTube, playlist: bool}`; saída `job`.
- `GET /api/jobs/{id}`: saída `job`.
- `GET /api/recent-job`: saída da tarefa mais recente, usada para restaurar a tela.
- `GET /api/jobs/{id}/files/{filename}`: arquivo MP3 listado no job.
- `GET /api/jobs/{id}/archive`: ZIP de todos os MP3 concluídos (também inclui arquivos parciais de tarefa com erro).
- `job`: `id`, `url`, `playlist`, `status`, `percent`, `title`, `files`, `error`.
- Estados: `na_fila`, `baixando`, `convertendo`, `concluido`, `erro`.

## Funções e DOM

- `jobs.create`, `jobs.snapshot`, `jobs.update`, `jobs.start`: interface da fila.
- `apiRequest`, `showJob`, `watch`: funções JavaScript.
- IDs: `download-form`, `url`, `playlist`, `result`, `status`, `progress`, `message`, `files`, `download-all`.
- Classes CSS: `option`, `download-all`.

## Limites

- Um worker, fila de 20 tarefas e no máximo 100 vídeos por playlist.
- Entrada restrita a URLs HTTPS do YouTube; aplicação escuta apenas em localhost conforme README.
- O worker usa automaticamente `.tools/ffmpeg/` quando contém ambos os executáveis.
