from django.test import TestCase
from ninja.testing import TestClient

from api.router import api
from api.urls import _run_manager


class TestSseFormat(TestCase):
    def test_sse_lines(self):
        run = _run_manager.create_run()
        _run_manager.emit(run.id, "status", {"run_id": run.id, "phase": "routing"})
        _run_manager.emit(run.id, "final", {"run_id": run.id, "status": "done"})

        client = TestClient(api)
        resp = client.get(f"/v1/runs/{run.id}/events")
        assert resp.status_code == 200
        body = resp.content.decode("utf-8")
        assert "event: status" in body
        assert "event: final" in body
        assert "id:" in body
