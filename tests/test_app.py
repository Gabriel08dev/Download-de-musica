import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from app import jobs
from app.main import DownloadRequest


class FakeDownloader:
    last_options = None

    def __init__(self, options):
        self.options = options
        FakeDownloader.last_options = options

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def extract_info(self, url, download):
        self.options["progress_hooks"][0]({"status": "downloading", "downloaded_bytes": 10, "total_bytes": 20})
        self.options["postprocessor_hooks"][0]({"status": "started"})
        Path(self.options["outtmpl"]).parent.joinpath("musica.mp3").write_bytes(b"MP3")
        return {"title": "Teste"}


class AppTests(unittest.TestCase):
    def test_url_rejects_non_youtube_hosts(self):
        for url in ("http://www.youtube.com/watch?v=1", "https://youtube.com.evil.test/watch?v=1",
                    "https://127.0.0.1/video", "https://user@youtube.com/watch?v=1"):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                DownloadRequest(url=url)

    def test_job_produces_downloadable_mp3(self):
        with tempfile.TemporaryDirectory() as directory:
            binaries = Path(directory) / "bin"
            binaries.mkdir()
            for name in ("ffmpeg.exe", "ffprobe.exe"):
                (binaries / name).touch()
            with patch.object(jobs, "ROOT", Path(directory)), patch.object(jobs, "LOCAL_FFMPEG", binaries), \
                    patch.object(jobs.yt_dlp, "YoutubeDL", FakeDownloader):
                job = jobs.create("https://www.youtube.com/watch?v=example", False)
                jobs._process(job["id"])
                saved = jobs.snapshot(job["id"])
                self.assertEqual(saved["status"], "concluido")
                self.assertEqual(saved["files"], ["musica.mp3"])
                self.assertEqual(saved["percent"], 100)
                self.assertEqual(FakeDownloader.last_options["ffmpeg_location"], str(binaries))

    def test_latest_restores_completed_job(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "saved-job"
            folder.mkdir()
            (folder / "job.json").write_text("{}", encoding="utf-8")
            job = {"id": "saved-job", "status": "concluido", "files": ["music.mp3"]}
            with patch.object(jobs, "ROOT", Path(directory)), patch.dict(jobs.JOBS, {"saved-job": job}):
                self.assertEqual(jobs.latest(), job)


if __name__ == "__main__":
    unittest.main()
