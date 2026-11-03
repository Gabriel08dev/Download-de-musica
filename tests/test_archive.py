import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app import jobs
from app.main import get_archive


class ArchiveTests(unittest.TestCase):
    def test_download_all_contains_each_mp3(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "job123"
            folder.mkdir()
            (folder / "um.mp3").write_bytes(b"first")
            (folder / "dois.mp3").write_bytes(b"second")
            job = {"id": "job123", "status": "concluido", "files": ["um.mp3", "dois.mp3"]}
            with patch.object(jobs, "ROOT", Path(directory)), patch.object(jobs, "snapshot", return_value=job):
                response = get_archive("job123")
                self.assertEqual(response.media_type, "application/zip")
                import asyncio

                async def collect():
                    return b"".join([chunk async for chunk in response.body_iterator])

                data = asyncio.run(collect())
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                self.assertEqual(archive.namelist(), ["um.mp3", "dois.mp3"])
                self.assertEqual(archive.read("um.mp3"), b"first")
                self.assertEqual(archive.read("dois.mp3"), b"second")

    def test_rejects_unfinished_job(self):
        job = {"id": "job123", "status": "baixando", "files": ["um.mp3"]}
        with patch.object(jobs, "snapshot", return_value=job), self.assertRaises(HTTPException):
            get_archive("job123")
