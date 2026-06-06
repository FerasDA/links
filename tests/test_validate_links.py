import subprocess
import sys
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_links.py"


class ValidateLinksTests(unittest.TestCase):
    def run_validator(self, json_text):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            links_file = tmp_path / "links.json"
            links_file.write_text(textwrap.dedent(json_text), encoding="utf-8")

            return subprocess.run(
                [sys.executable, str(SCRIPT), str(links_file)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

    def test_accepts_valid_links_file(self):
        result = self.run_validator(
            """
            [
              {
                "title": "Example Article",
                "url": "https://example.com/article",
                "description": "A short useful description of this example link.",
                "category": "Interesting Reads",
                "tags": ["example", "article"],
                "type": "article",
                "added": "2026-06-06",
                "status": "unchecked"
              }
            ]
            """
        )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Validated 1 links", result.stdout)

    def test_rejects_duplicate_normalized_urls(self):
        result = self.run_validator(
            """
            [
              {
                "title": "Example One",
                "url": "https://example.com/path/",
                "description": "A short useful description of this example link.",
                "category": "Interesting Reads",
                "tags": ["example"],
                "type": "article",
                "added": "2026-06-06",
                "status": "unchecked"
              },
              {
                "title": "Example Two",
                "url": "https://example.com/path",
                "description": "A short useful description of this duplicate link.",
                "category": "Interesting Reads",
                "tags": ["duplicate"],
                "type": "article",
                "added": "2026-06-06",
                "status": "unchecked"
              }
            ]
            """
        )

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("duplicate normalized url", result.stdout.lower())

    def test_rejects_invalid_tags_status_type_and_url(self):
        result = self.run_validator(
            """
            [
              {
                "title": "Bad Link",
                "url": "not-a-url",
                "description": "Missing useful data.",
                "category": "AI",
                "tags": ["Bad Tag"],
                "type": "made-up",
                "added": "not-a-date",
                "status": "alive"
              }
            ]
            """
        )

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("url", result.stdout.lower())
        self.assertIn("tag", result.stdout.lower())
        self.assertIn("status", result.stdout.lower())
        self.assertIn("type", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
