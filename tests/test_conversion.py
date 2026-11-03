import functools
import http.server
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from app import jobs


@unittest.skipUnless((jobs.LOCAL_FFMPEG / "ffmpeg.exe").is_file(), "FFmpeg local ausente")
class ConversionTests(unittest.TestCase):
    def test_yt_dlp_and_ffmpeg_convert_local_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sample.wav"
            subprocess.run([
                str(jobs.LOCAL_FFMPEG / "ffmpeg.exe"), "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-y", str(source),
            ], check=True)
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with patch.object(jobs, "ROOT", root):
                    job = jobs.create("https://www.youtube.com/watch?v=placeholder", False)
                    jobs.update(job["id"], url=f"http://127.0.0.1:{server.server_port}/sample.wav")
                    jobs._process(job["id"])
                    result = jobs.snapshot(job["id"])
                    self.assertEqual(result["status"], "concluido")
                    self.assertEqual(len(result["files"]), 1)
                    self.assertTrue((root / job["id"] / result["files"][0]).is_file())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
