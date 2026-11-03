import logging
import threading
import zipfile
from pathlib import Path
from queue import Empty, Full, Queue

LOG = logging.getLogger(__name__)
CHUNK_SIZE = 256 * 1024


def stream_zip(paths: list[Path]):
    chunks: Queue[bytes | None] = Queue(maxsize=4)
    stopped = threading.Event()

    class Sink:
        def write(self, data: bytes) -> int:
            while not stopped.is_set():
                try:
                    chunks.put(data, timeout=0.2)
                    return len(data)
                except Full:
                    continue
            raise BrokenPipeError("Download do ZIP interrompido")

        def flush(self) -> None:
            pass

    def produce() -> None:
        try:
            with zipfile.ZipFile(Sink(), "w", compression=zipfile.ZIP_STORED,
                                 allowZip64=True) as archive:
                for path in paths:
                    with path.open("rb") as source, archive.open(path.name, "w", force_zip64=True) as target:
                        while data := source.read(CHUNK_SIZE):
                            target.write(data)
        except BrokenPipeError:
            pass
        except Exception:
            LOG.exception("Falha ao transmitir ZIP")
        finally:
            while not stopped.is_set():
                try:
                    chunks.put(None, timeout=0.2)
                    break
                except Full:
                    continue

    thread = threading.Thread(target=produce, daemon=True, name="zip-stream")
    thread.start()
    try:
        while True:
            try:
                chunk = chunks.get(timeout=0.2)
            except Empty:
                if not thread.is_alive():
                    break
                continue
            if chunk is None:
                break
            yield chunk
    finally:
        stopped.set()
        thread.join(timeout=1)
