from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_markdown_doc.py"
SPEC = importlib.util.spec_from_file_location("publish_markdown_doc", SCRIPT)
assert SPEC is not None
publisher = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = publisher
SPEC.loader.exec_module(publisher)


class PublishMarkdownDocTests(unittest.TestCase):
    def test_title_replaces_existing_h1(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.md"
            path.write_text("# Old title\n\nbody\n", encoding="utf-8")

            payload = publisher.content_payload(path, "New title")

        self.assertEqual(payload, "# New title\n\nbody\n")

    def test_title_is_prepended_when_h1_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.md"
            path.write_text("body\n", encoding="utf-8")

            payload = publisher.content_payload(path, "New title")

        self.assertEqual(payload, "# New title\n\nbody\n")


if __name__ == "__main__":
    unittest.main()
