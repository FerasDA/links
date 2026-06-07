import contextlib
import importlib.util
import io
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "add_link_pr.py"


def load_module():
    spec = importlib.util.spec_from_file_location("add_link_pr", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AddLinkPrTests(unittest.TestCase):
    def test_slugifies_title_for_stable_branch_name(self):
        module = load_module()

        self.assertEqual(
            module.branch_name("AI & Product: A practical guide!", "https://example.com/guide"),
            "addlink/ai-product-a-practical-guide",
        )
        self.assertEqual(
            module.branch_name("", "https://example.com/some/path/?utm_source=test"),
            "addlink/example-com-some-path",
        )

    def test_builds_reviewable_pr_command_plan(self):
        module = load_module()
        args = module.parse_args(
            [
                "https://example.com/article?utm_source=newsletter",
                "--title",
                "Example Article",
                "--description",
                "A useful article captured through Hermes.",
                "--category",
                "Interesting Reads",
                "--tags",
                "interesting-reads,example",
                "--type",
                "article",
                "--date",
                "2026-06-06",
                "--no-fetch",
            ]
        )

        commands = module.build_command_plan(args)
        joined = "\n".join(" ".join(command) for command in commands)

        self.assertEqual(commands[0], ["git", "checkout", "master"])
        self.assertIn("git pull --ff-only origin master", joined)
        self.assertIn("git checkout -b addlink/example-article", joined)
        self.assertIn("npm run addlink -- https://example.com/article?utm_source=newsletter", joined)
        self.assertIn("--title Example Article", joined)
        self.assertIn("--tags interesting-reads,example", joined)
        self.assertIn("--no-fetch", joined)
        self.assertIn("npm run validate", joined)
        self.assertIn("npm test", joined)
        self.assertIn("npm run build", joined)
        self.assertIn("git add data/links.json", joined)
        self.assertIn("git push -u origin HEAD", joined)
        self.assertIn("gh pr create", joined)

    def test_dry_run_returns_plan_without_executing_runner(self):
        module = load_module()
        args = module.parse_args(
            [
                "https://example.com/article",
                "--title",
                "Example Article",
                "--description",
                "A useful article captured through Hermes.",
                "--category",
                "Interesting Reads",
                "--tags",
                "interesting-reads,example",
                "--dry-run",
            ]
        )
        calls = []

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = module.run(args, runner=lambda command: calls.append(command))

        self.assertEqual(exit_code, 0)
        self.assertIn("Dry run: addlink PR command plan", stdout.getvalue())
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
