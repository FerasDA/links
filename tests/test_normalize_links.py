import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "normalize_links.py"


def run_normalize(data_file: Path, *extra_args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--data", str(data_file), *extra_args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class NormalizeLinksTests(unittest.TestCase):
    def write_links(self, directory: Path):
        data_file = directory / "links.json"
        links = [
            {
                "title": " API Thing ",
                "url": "https://example.com/api",
                "description": "  Useful API reference.  ",
                "category": "APIs",
                "tags": ["apis", "api", "api", "Business & Startup", ""],
                "type": "article",
                "added": "2026-06-06",
                "status": "unchecked",
            },
            {
                "title": "Music Lesson",
                "url": "https://example.com/music",
                "description": "Learn music.",
                "category": "Music & Learning",
                "tags": ["music-and-learning", "music-learning"],
                "type": "video",
                "added": "2026-06-06",
                "status": "ok",
            },
        ]
        data_file.write_text(json.dumps(links, indent=2), encoding="utf-8")
        return data_file

    def test_normalizes_alias_tags_and_whitespace(self):
        with TemporaryDirectory() as tmp:
            data_file = self.write_links(Path(tmp))

            result = run_normalize(data_file)

            self.assertEqual(result.returncode, 0, result.stderr)
            links = json.loads(data_file.read_text(encoding="utf-8"))
            self.assertEqual(links[0]["title"], "API Thing")
            self.assertEqual(links[0]["description"], "Useful API reference.")
            self.assertEqual(links[0]["tags"], ["api", "business-startups"])
            self.assertEqual(links[1]["tags"], ["music-learning"])
            self.assertIn("Updated 2 links", result.stdout)

    def test_dry_run_reports_changes_without_writing(self):
        with TemporaryDirectory() as tmp:
            data_file = self.write_links(Path(tmp))
            before = data_file.read_text(encoding="utf-8")

            result = run_normalize(data_file, "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(data_file.read_text(encoding="utf-8"), before)
            self.assertIn("Dry run", result.stdout)


if __name__ == "__main__":
    unittest.main()
