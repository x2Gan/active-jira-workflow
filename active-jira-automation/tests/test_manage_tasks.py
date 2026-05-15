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

SCRIPT = SCRIPTS_DIR / "manage_tasks.py"
SPEC = importlib.util.spec_from_file_location("manage_tasks", SCRIPT)
assert SPEC is not None
manage_tasks = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = manage_tasks
SPEC.loader.exec_module(manage_tasks)


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = manage_tasks.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def create_args(tmpdir: str, name: str = "Geneva P0 Bug Alert") -> list[str]:
    return [
        "create",
        "--data-root",
        tmpdir,
        "--task-name",
        name,
        "--scenario-key",
        "jira-scheduled-query-alert",
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
        "--lookback-minutes",
        "5",
        "--notify-policy-json",
        '{"mode":"per_issue","max_issues_per_run":20,"repeat_snapshot":false}',
        "--schedule-type",
        "recurring",
        "--schedule-expr",
        "0 * * * *",
        "--target-chat-id",
        "oc_123",
    ]


class ManageTasksTests(unittest.TestCase):
    def test_create_and_list_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_code, create_out, create_err = run_cli(create_args(tmpdir))
            list_code, list_out, list_err = run_cli(["list", "--data-root", tmpdir])

            self.assertEqual(create_code, 0, create_err)
            self.assertEqual(list_code, 0, list_err)
            created = json.loads(create_out)
            listed = json.loads(list_out)
            self.assertTrue(created["created"])
            self.assertEqual(created["task"]["message_template_key"], "lark-jira-query-alert-card-v1")
            self.assertEqual(created["task"]["llm_policy"], "on-match-only")
            self.assertEqual(created["task"]["base_jql"], 'project = GENEVA AND issuetype = Bug AND "Severity" = P0')
            self.assertEqual(created["task"]["window_mode"], "created")
            self.assertEqual(created["task"]["notify_policy"]["max_issues_per_run"], 20)
            self.assertEqual(listed["tasks"][0]["task_name"], "Geneva P0 Bug Alert")
            self.assertEqual(listed["tasks"][0]["status"], "enabled")

    def test_create_missing_required_field_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            code, _out, err = run_cli(
                [
                    "create",
                    "--data-root",
                    tmpdir,
                    "--task-name",
                    "Missing Chat",
                    "--scenario-key",
                    "jira-scheduled-query-alert",
                    "--project",
                    "GENEVA",
                    "--filter-prompt",
                    "每小时查询一次 GENEVA 新增的 P0 Bug",
                    "--base-jql",
                    'project = GENEVA AND issuetype = Bug AND "Severity" = P0',
                    "--query-spec-json",
                    '{"projects":["GENEVA"],"clauses":[{"field":"issuetype","op":"=","value":"Bug"}]}',
                    "--schedule-type",
                    "recurring",
                    "--schedule-expr",
                    "0 * * * *",
                ]
            )

            self.assertEqual(code, 1)
            self.assertIn("target_chat_id", err)

    def test_duplicate_task_name_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first_code, _first_out, first_err = run_cli(create_args(tmpdir))
            second_code, _second_out, second_err = run_cli(create_args(tmpdir))

            self.assertEqual(first_code, 0, first_err)
            self.assertEqual(second_code, 1)
            self.assertIn("task_name already exists", second_err)

    def test_pause_resume_delete_by_id_and_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_code, create_out, create_err = run_cli(create_args(tmpdir))
            self.assertEqual(create_code, 0, create_err)
            task_id = json.loads(create_out)["task"]["task_id"]

            pause_code, pause_out, pause_err = run_cli(["pause", "--data-root", tmpdir, task_id])
            resume_code, resume_out, resume_err = run_cli(["resume", "--data-root", tmpdir, "Geneva P0 Bug Alert"])
            preview_code, preview_out, preview_err = run_cli(["delete", "--data-root", tmpdir, task_id])
            delete_code, delete_out, delete_err = run_cli(["delete", "--data-root", tmpdir, task_id, "--confirm"])
            list_code, list_out, list_err = run_cli(["list", "--data-root", tmpdir])

            self.assertEqual(pause_code, 0, pause_err)
            self.assertEqual(resume_code, 0, resume_err)
            self.assertEqual(preview_code, 2, preview_err)
            self.assertEqual(delete_code, 0, delete_err)
            self.assertEqual(list_code, 0, list_err)
            self.assertEqual(json.loads(pause_out)["task"]["status"], "paused")
            self.assertEqual(json.loads(resume_out)["task"]["status"], "enabled")
            self.assertTrue(json.loads(preview_out)["requires_confirmation"])
            self.assertEqual(json.loads(delete_out)["task"]["status"], "deleted")
            self.assertEqual(json.loads(list_out)["tasks"], [])

    def test_name_lookup_ignores_deleted_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first_code, first_out, first_err = run_cli(create_args(tmpdir))
            self.assertEqual(first_code, 0, first_err)
            first_task_id = json.loads(first_out)["task"]["task_id"]
            delete_code, _delete_out, delete_err = run_cli(["delete", "--data-root", tmpdir, first_task_id, "--confirm"])
            self.assertEqual(delete_code, 0, delete_err)

            second_code, _second_out, second_err = run_cli(create_args(tmpdir))
            pause_code, pause_out, pause_err = run_cli(["pause", "--data-root", tmpdir, "Geneva P0 Bug Alert"])

            self.assertEqual(second_code, 0, second_err)
            self.assertEqual(pause_code, 0, pause_err)
            self.assertEqual(json.loads(pause_out)["task"]["status"], "paused")

    def test_create_from_json_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "task.json"
            input_path.write_text(
                json.dumps(
                    {
                        "task_name": "Input JSON Task",
                        "scenario_key": "jira-scheduled-query-alert",
                        "project": "GENEVA",
                        "filter_prompt": "每天检查一次当前未分配的 GENEVA Bug",
                        "query_spec": {
                            "projects": ["GENEVA"],
                            "clauses": [
                                {"field": "issuetype", "op": "=", "value": "Bug"},
                                {"field": "assignee", "op": "IS", "value": "EMPTY"},
                            ],
                        },
                        "base_jql": "project = GENEVA AND issuetype = Bug AND assignee IS EMPTY",
                        "window_mode": "snapshot",
                        "lookback_minutes": 5,
                        "notify_policy": {"mode": "per_issue", "max_issues_per_run": 10, "repeat_snapshot": False},
                        "schedule_type": "once",
                        "schedule_expr": "2026-05-14T20:00:00+08:00",
                        "target_chat_id": "oc_456",
                    }
                ),
                encoding="utf-8",
            )

            code, out, err = run_cli(["create", "--data-root", tmpdir, "--input-json", str(input_path)])

            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["task"]["task_name"], "Input JSON Task")

    def test_create_supports_query_spec_file_and_default_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            query_spec_path = Path(tmpdir) / "query-spec.json"
            query_spec_path.write_text(
                json.dumps(
                    {
                        "projects": ["GENEVA"],
                        "clauses": [{"field": "labels", "op": "=", "value": "customer-escalation"}],
                    }
                ),
                encoding="utf-8",
            )

            code, out, err = run_cli(
                [
                    "create",
                    "--data-root",
                    tmpdir,
                    "--task-name",
                    "Escalation Alert",
                    "--scenario",
                    "jira-scheduled-query-alert",
                    "--project",
                    "GENEVA",
                    "--filter-prompt",
                    "每小时提醒带 customer-escalation 标签的新 Jira",
                    "--base-jql",
                    "project = GENEVA AND labels = customer-escalation",
                    "--query-spec-file",
                    str(query_spec_path),
                    "--schedule-type",
                    "recurring",
                    "--schedule-expr",
                    "0 * * * *",
                    "--target-chat-id",
                    "oc_789",
                ]
            )

            task = json.loads(out)["task"]
            self.assertEqual(code, 0, err)
            self.assertEqual(task["window_mode"], "created")
            self.assertEqual(task["lookback_minutes"], 5)
            self.assertEqual(task["notify_policy"]["mode"], "per_issue")

    def test_create_missing_base_jql_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            args = create_args(tmpdir)
            base_jql_index = args.index("--base-jql")
            del args[base_jql_index : base_jql_index + 2]

            code, _out, err = run_cli(args)

            self.assertEqual(code, 1)
            self.assertIn("base_jql", err)

    def test_create_rejects_legacy_scenario_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            args = create_args(tmpdir)
            args[args.index("jira-scheduled-query-alert")] = "new-p0-bug-alert"

            code, _out, err = run_cli(args)

            self.assertEqual(code, 1)
            self.assertIn("deprecated", err)

    def test_old_task_can_be_listed_paused_and_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "tasks" / "legacy-task.json"
            task_path.parent.mkdir(parents=True)
            task_path.write_text(
                json.dumps(
                    {
                        "task_id": "legacy-task",
                        "task_name": "Legacy P0 Bug Alert",
                        "scenario_key": "new-p0-bug-alert",
                        "project": "GENEVA",
                        "query_rule": {"issue_type": "Bug", "severity": "P0"},
                        "schedule_type": "recurring",
                        "schedule_expr": "0 * * * *",
                        "target_chat_id": "oc_123",
                        "message_template_key": "lark-p0-bug-card-v1",
                        "llm_policy": "on-match-only",
                        "status": "enabled",
                        "created_at": "2026-05-14T08:00:00Z",
                        "updated_at": "2026-05-14T08:00:00Z",
                    }
                ),
                encoding="utf-8",
            )

            list_code, list_out, list_err = run_cli(["list", "--data-root", tmpdir])
            pause_code, pause_out, pause_err = run_cli(["pause", "--data-root", tmpdir, "legacy-task"])
            delete_code, _delete_out, delete_err = run_cli(["delete", "--data-root", tmpdir, "legacy-task", "--confirm"])

            self.assertEqual(list_code, 0, list_err)
            self.assertEqual(pause_code, 0, pause_err)
            self.assertEqual(delete_code, 0, delete_err)
            self.assertEqual(json.loads(list_out)["tasks"][0]["scenario_key"], "new-p0-bug-alert")
            self.assertEqual(json.loads(pause_out)["task"]["status"], "paused")


if __name__ == "__main__":
    unittest.main()
