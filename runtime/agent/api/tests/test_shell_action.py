import time

from django.test import TestCase
from ninja.testing import TestClient

from api.router import api
from api.urls import _run_manager


class TestShellAction(TestCase):
    def test_shell_action_flow(self):
        client = TestClient(api)
        resp = client.post(
            "/v1/runs",
            json={
                "input": {"message": "!shell echo hi", "attachments": []},
                "options": {"profile": "dev", "vision": "auto", "preferred_model": "auto", "enable_browser": False},
            },
        )
        assert resp.status_code == 200
        run_id = resp.json()["id"]

        for _ in range(50):
            events = _run_manager.get_events(run_id, last_event_id=None)
            pa = [e for e in events if e.event_type == "proposed_action"]
            if pa:
                action_id = pa[0].data["action_id"]
                break
            time.sleep(0.02)
        else:
            raise AssertionError("proposed_action not emitted")

        state = _run_manager.get_run(run_id)
        assert action_id in state.pending_actions

        resp2 = client.post(f"/v1/runs/{run_id}/actions/{action_id}/approve", json={"approved": True})
        assert resp2.status_code == 200

        for _ in range(50):
            events = _run_manager.get_events(run_id, last_event_id=None)
            if any(e.event_type == "action_result" for e in events) and any(e.event_type == "final" for e in events):
                break
            time.sleep(0.02)
        else:
            raise AssertionError("action_result/final not emitted")
