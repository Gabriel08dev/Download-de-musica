# mp3download

Aplicação web local para extrair MP3 de um vídeo ou de uma playlist do YouTube. Processa uma tarefa por vez, mantém até 20 tarefas na fila e limita playlists a 100 itens. Os downloads parciais e o estado das tarefas ficam em `downloads/`, permitindo retomada após reiniciar o servidor.

## Requisitos

- Python 3.11 ou superior
- FFmpeg e FFprobe disponíveis no `PATH` ou em `.tools/ffmpeg/`
- Acesso à internet e espaço em disco para os arquivos

Use apenas conteúdo que você tem direito de baixar. A disponibilidade depende das regras e mudanças da origem.

No Windows, execute `powershell -ExecutionPolicy Bypass -File scripts/install_ffmpeg.ps1` para instalar uma cópia portátil dos dois executáveis em `.tools/ffmpeg/`.

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Execução

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Também é possível iniciar com `python app/main.py` a partir da raiz do projeto.

Abra `http://127.0.0.1:8000`. Para escolher outra pasta de saída, defina a variável de ambiente `MP3DOWNLOAD_DIR` antes de iniciar. Não há `.env` obrigatório.

## API

| Método | Rota | Função |
| --- | --- | --- |
| POST | `/api/jobs` | Cria tarefa com `{"url":"https://...","playlist":false}` |
| GET | `/api/recent-job` | Recupera a tarefa mais recente ao reabrir a página |
| GET | `/api/jobs/{id}` | Consulta estado, progresso e arquivos |
| GET | `/api/jobs/{id}/files/{nome}` | Baixa um MP3 concluído |
| GET | `/api/jobs/{id}/archive` | Transmite todos os MP3 em um ZIP |

Estados: `na_fila`, `baixando`, `convertendo`, `concluido`, `erro`. Em playlists, o percentual representa o item atual. Ao terminar, use **Baixar todos em ZIP** para salvar a playlist com um clique; os links individuais continuam disponíveis. O ZIP é transmitido sem criar outra cópia dos MP3 no disco. O serviço foi feito para uso local, sem autenticação; mantenha o bind em `127.0.0.1`.
