"""Exercise local helper contracts without provider credentials or paid calls."""
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/launch-remake/scripts"
FAKE_KEY = "test-only-provider-key-not-a-secret"


class Response(io.BytesIO):
    headers = {"song-id": "fixture-song", "character-cost": "10"}


class ProviderHelpers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "video.mp4").write_bytes(b"synthetic test video")
        (self.root / "prompt.md").write_text("Review the fixture.")
        (self.root / "jobs.json").write_text(json.dumps([
            {"name": "fixture", "description": "Synthetic music test", "secs": 10}
        ]))

    def run_helper(self, name, response=None, failure=None):
        music = name == "music/gen_music.py"
        script = SCRIPTS / name
        args = ([self.root / "jobs.json", self.root / "out"] if music
                else [self.root / "video.mp4", self.root / "prompt.md"])
        output, errors, status = io.StringIO(), io.StringIO(), 0
        with patch.dict(os.environ, {"ELEVEN_LABS_API_KEY": FAKE_KEY, "GEMINI_API_KEY": FAKE_KEY}), \
             patch.object(sys, "argv", [str(script), *map(str, args)]), \
             patch("urllib.request.urlopen", return_value=response, side_effect=failure) as request, \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            try:
                runpy.run_path(str(script), run_name="__main__")
            except SystemExit as error:
                status = error.code
        return status, output.getvalue() + errors.getvalue(), request

    def test_gemini_http_failure_is_not_success_and_does_not_print_key(self):
        failure = urllib.error.HTTPError("https://example.invalid", 401, "Unauthorized", {},
                                         io.BytesIO(("Rejected " + FAKE_KEY).encode()))
        status, output, request = self.run_helper("gemini_review.py", failure=failure)
        self.assertEqual(status, 1)
        self.assertIn("401", output)
        self.assertNotIn(FAKE_KEY, output)
        self.assertEqual(request.call_count, 1)

    def test_gemini_success_keeps_review_text(self):
        response = Response(json.dumps({"candidates": [{"content": {"parts": [{"text": "Fixture reviewed"}]}}]}).encode())
        status, output, _ = self.run_helper("gemini_review.py", response=response)
        self.assertEqual(status, 0)
        self.assertIn("Fixture reviewed", output)

    def test_music_http_failure_redacts_output_and_receipt_and_exits_nonzero(self):
        failure = urllib.error.HTTPError("https://example.invalid", 401, "Unauthorized", {},
                                         io.BytesIO(("Rejected " + FAKE_KEY).encode()))
        status, output, request = self.run_helper("music/gen_music.py", failure=failure)
        self.assertEqual(status, 1)
        receipt = (self.root / "out/receipts.jsonl").read_text()
        self.assertNotIn(FAKE_KEY, output + receipt)
        self.assertFalse(json.loads(receipt)["ok"])
        self.assertFalse((self.root / "out/fixture.mp3").exists())
        self.assertEqual(request.call_count, 1)

    def test_music_transport_failure_also_redacts_key(self):
        status, output, _ = self.run_helper("music/gen_music.py", failure=RuntimeError("Rejected " + FAKE_KEY))
        self.assertEqual(status, 1)
        self.assertNotIn(FAKE_KEY, output + (self.root / "out/receipts.jsonl").read_text())

    def test_music_success_saves_track_and_receipt(self):
        status, _, request = self.run_helper("music/gen_music.py", response=Response(b"ID3-fixture-audio"))
        self.assertEqual(status, 0)
        self.assertEqual((self.root / "out/fixture.mp3").read_bytes(), b"ID3-fixture-audio")
        receipt = json.loads((self.root / "out/receipts.jsonl").read_text())
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["song_id"], "fixture-song")
        self.assertEqual(request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
