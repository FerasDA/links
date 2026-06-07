import json
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_links.py"


class LinkFixtureHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.respond()

    def do_GET(self):
        self.respond()

    def respond(self):
        if self.path == "/ok":
            self.send_response(200)
            self.end_headers()
        elif self.path == "/redirect":
            self.send_response(301)
            self.send_header("Location", "/ok")
            self.end_headers()
        elif self.path == "/missing":
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        return


class CheckLinksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), LinkFixtureHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)

    def write_links_file(self, directory: Path) -> Path:
        links = [
            {
                "title": "OK Link",
                "url": f"{self.base_url}/ok",
                "description": "A local test link that returns HTTP 200.",
                "category": "Testing",
                "tags": ["testing"],
                "type": "article",
                "added": "2026-06-06",
                "status": "unchecked",
            },
            {
                "title": "Redirect Link",
                "url": f"{self.base_url}/redirect",
                "description": "A local test link that redirects to another URL.",
                "category": "Testing",
                "tags": ["testing"],
                "type": "article",
                "added": "2026-06-06",
                "status": "unchecked",
            },
            {
                "title": "Broken Link",
                "url": f"{self.base_url}/missing",
                "description": "A local test link that returns HTTP 404.",
                "category": "Testing",
                "tags": ["testing"],
                "type": "article",
                "added": "2026-06-06",
                "status": "unchecked",
            },
        ]
        path = directory / "links.json"
        path.write_text(json.dumps(links, indent=2) + "\n", encoding="utf-8")
        return path

    def run_checker(self, links_file: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--data", str(links_file), "--date", "2026-06-07", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def test_updates_statuses_and_check_metadata(self):
        with TemporaryDirectory() as tmp:
            links_file = self.write_links_file(Path(tmp))

            result = self.run_checker(links_file)

            self.assertEqual(result.returncode, 0, result.stdout)
            links = json.loads(links_file.read_text(encoding="utf-8"))
            by_title = {link["title"]: link for link in links}

            self.assertEqual(by_title["OK Link"]["status"], "ok")
            self.assertEqual(by_title["OK Link"]["last_checked"], "2026-06-07")
            self.assertNotIn("redirect_url", by_title["OK Link"])
            self.assertNotIn("check_error", by_title["OK Link"])

            self.assertEqual(by_title["Redirect Link"]["status"], "redirected")
            self.assertEqual(by_title["Redirect Link"]["last_checked"], "2026-06-07")
            self.assertTrue(by_title["Redirect Link"]["redirect_url"].endswith("/ok"))

            self.assertEqual(by_title["Broken Link"]["status"], "broken")
            self.assertEqual(by_title["Broken Link"]["last_checked"], "2026-06-07")
            self.assertIn("404", by_title["Broken Link"]["check_error"])
            self.assertIn("OK Link: ok", result.stdout)
            self.assertIn("Redirect Link: redirected", result.stdout)
            self.assertIn("Broken Link: broken", result.stdout)

    def test_dry_run_reports_without_writing(self):
        with TemporaryDirectory() as tmp:
            links_file = self.write_links_file(Path(tmp))
            before = links_file.read_text(encoding="utf-8")

            result = self.run_checker(links_file, "--dry-run")

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("Dry run", result.stdout)
            self.assertEqual(links_file.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
