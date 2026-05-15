from __future__ import annotations

import contextlib
from io import StringIO
import importlib.util
import json
import sys
from pathlib import Path
import tempfile
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

FIXTURE_FILE = Path(__file__).resolve().parent / "fixtures" / "jira_query_results.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


manage_tasks = load_module("manage_tasks_e2e", SCRIPTS_DIR / "manage_tasks.py")
run_automation_task = load_module("run_automation_task_e2e", SCRIPTS_DIR / "run_automation_task.py")


def run_cli(module, argv: list[str]) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = module.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def p0_args(data_root: str, *, dry_run: bool = False) -> list[str]:
    argv = [
        "create",
        "--data-root",
        data_root,
        "--scenario",
        "jira-scheduled-query-alert",
        "--task-name",
        "Geneva P0 Bug Alert",
        "--project",
        "GENEVA",
        "--filter-prompt",
        "每小时查询一次 GENEVA 新增的 P0 Bug",
        "--base-jql",
        'project = GENEVA AND issuetype = Bug AND "Severity" = P0',
        "--query-spec-json",
        '{"projects":["GENEVA"],"clauses":[{"field":"issuetype","op":"=","value":"Bug"},{"field":"Severity","op":"=","value":"P0"}]}',
        "--window-mode",
        "created",
        "--schedule-type",
        "recurring",
        "--schedule-expr",
        "0 * * * *",
        "--target-chat-id",
        "oc_demo",
    ]
    if dry_run:
        argv.append("--dry-run")
    return argv


def unassigned_updated_args(data_root: str, *, dry_run: bool = False) -> list[str]:
    argv = [
        "create",
        "--data-root",
        data_root,
        "--scenario",
        "jira-scheduled-query-alert",
        "--task-name",
        "Unassigned Updated Issues Alert",
        "--project",
        "GENEVA",
        "--filter-prompt",
        "每 30 分钟提醒最近有更新且 assignee 为空的 Jira",
        "--base-jql",
        "project = GENEVA AND assignee IS EMPTY",
        "--query-spec-json",
        '{"projects":["GENEVA"],"clauses":[{"field":"assignee","op":"IS","value":"EMPTY"}]}',
        "--window-mode",
        "updated",
        "--schedule-type",
        "recurring",
        "--schedule-expr",
        "*/30 * * * *",
        "--target-chat-id",
        "oc_demo",
    ]
    if dry_run:
        argv.append("--dry-run")
    return argv


def write_updated_fixture(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "query_hits": [{"key": "GENEVA-9", "updated_at": "2026-05-14T08:45:00Z"}],
                "details": {
                    "GENEVA-9": {
                        "key": "GENEVA-9",
                        "fields": {
                            "summary": "Updated unassigned issue",
                            "updated": "2026-05-14T08:45:00Z",
                            "status": {"name": "Open"},
                            "assignee": None,
                        },
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


class EndToEndAcceptanceTests(unittest.TestCase):
    def test_p0_bug_example_previews_then_runs_with_fixture_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            preview_code, preview_out, preview_err = run_cli(manage_tasks, p0_args(tmpdir, dry_run=True))
            create_code, create_out, create_err = run_cli(manage_tasks, p0_args(tmpdir))
            run_code, run_out, run_err = run_cli(
                run_automation_task,
                [
                    "Geneva P0 Bug Alert",
                    "--data-root",
                    tmpdir,
                    "--fixture-json",
                    str(FIXTURE_FILE),
                    "--dry-run",
                ],
            )

            self.assertEqual(preview_code, 0, preview_err)
            self.assertEqual(create_code, 0, create_err)
            self.assertEqual(run_code, 0, run_err)

            preview = json.loads(preview_out)
            created = json.loads(create_out)
            result = json.loads(run_out)
            self.assertFalse(preview["created"])
            self.assertTrue(preview["dry_run"])
            self.assertEqual(preview["task"]["base_jql"], 'project = GENEVA AND issuetype = Bug AND "Severity" = P0')
            self.assertTrue(created["created"])
            self.assertEqual(created["task"]["scenario_key"], "jira-scheduled-query-alert")
            self.assertEqual(result["scenario_key"], "jira-scheduled-query-alert")
            self.assertTrue(result["dry_run"])
            self.assertEqual(result["match_count"], 2)
            self.assertEqual(result["delivery_result"]["card_count"], 2)

    def test_non_p0_example_reuses_same_scenario_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = write_updated_fixture(Path(tmpdir) / "updated_fixture.json")

            preview_code, preview_out, preview_err = run_cli(manage_tasks, unassigned_updated_args(tmpdir, dry_run=True))
            create_code, create_out, create_err = run_cli(manage_tasks, unassigned_updated_args(tmpdir))
            run_code, run_out, run_err = run_cli(
                run_automation_task,
                [
                    "Unassigned Updated Issues Alert",
                    "--data-root",
                    tmpdir,
                    "--fixture-json",
                    str(fixture_path),
                    "--dry-run",
                ],
            )

            self.assertEqual(preview_code, 0, preview_err)
            self.assertEqual(create_code, 0, create_err)
            self.assertEqual(run_code, 0, run_err)

            preview = json.loads(preview_out)
            created = json.loads(create_out)
            result = json.loads(run_out)
            self.assertFalse(preview["created"])
            self.assertEqual(preview["task"]["window_mode"], "updated")
            self.assertEqual(created["task"]["base_jql"], "project = GENEVA AND assignee IS EMPTY")
            self.assertEqual(created["task"]["scenario_key"], "jira-scheduled-query-alert")
            self.assertEqual(result["scenario_key"], "jira-scheduled-query-alert")
            self.assertTrue(result["dry_run"])
            self.assertEqual(result["match_count"], 1)
            self.assertEqual(result["delivery_result"]["card_count"], 1)


if __name__ == "__main__":
    unittest.main()