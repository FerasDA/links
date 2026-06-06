import json
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "add_link.py"


class AddLinkTests(unittest.TestCase):
    def write_links_file(self, directory: Path) -> Path:
        path = directory / "links.json"
        path.write_text(
            textwrap.dedent(
                """
                [
                  {
                    "title": "Existing Link",
                    "url": "https://example.com/existing",
                    "description": "An existing link used by the test fixture.",
                    "category": "Interesting Reads",
                    "tags": ["interesting-reads"],
                    "type": "article",
                    "added": "2026-06-01",
                    "status": "unchecked"
                  }
                ]
                """
            ),
            encoding="utf-8",
        )
        return path

    def run_add_link(self, links_file: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--data", str(links_file), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def test_adds_valid_link_with_cli_metadata(self):
        with TemporaryDirectory() as tmp:
            links_file = self.write_links_file(Path(tmp))

            result = self.run_add_link(
                links_file,
                "https://example.com/new?utm_source=newsletter",
                "--title",
                "New Link",
                "--description",
                "A useful new link captured from a Hermes addlink request.",
                "--category",
                "AI",
                "--tags",
                "ai,example",
                "--type",
                "article",
                "--date",
                "2026-06-06",
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            links = json.loads(links_file.read_text(encoding="utf-8"))
            self.assertEqual([link["title"] for link in links], ["Existing Link", "New Link"])
            self.assertEqual(links[1]["status"], "unchecked")
            self.assertEqual(links[1]["tags"], ["ai", "example"])
            self.assertIn("Added New Link", result.stdout)

    def test_rejects_duplicate_normalized_url_without_writing(self):
        with TemporaryDirectory() as tmp:
            links_file = self.write_links_file(Path(tmp))
            before = links_file.read_text(encoding="utf-8")

            result = self.run_add_link(
                links_file,
                "https://example.com/existing/?utm_campaign=test",
                "--title",
                "Duplicate Link",
                "--description",
                "This should be rejected as a duplicate normalized URL.",
                "--category",
                "Interesting Reads",
                "--tags",
                "interesting-reads",
                "--date",
                "2026-06-06",
            )

            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("duplicate normalized url", result.stdout.lower())
            self.assertEqual(links_file.read_text(encoding="utf-8"), before)

    def test_can_dry_run_without_writing(self):
        with TemporaryDirectory() as tmp:
            links_file = self.write_links_file(Path(tmp))
            before = links_file.read_text(encoding="utf-8")

            result = self.run_add_link(
                links_file,
                "https://example.com/dry-run",
                "--title",
                "Dry Run Link",
                "--description",
                "A dry-run link should validate but not update the file.",
                "--category",
                "Interesting Reads",
                "--tags",
                "interesting-reads,dry-run",
                "--date",
                "2026-06-06",
                "--dry-run",
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("Dry run OK", result.stdout)
            self.assertEqual(links_file.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
