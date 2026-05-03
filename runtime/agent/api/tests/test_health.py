from django.test import TestCase
from ninja.testing import TestClient

from api.router import api


class TestHealth(TestCase):
    def test_health(self):
        client = TestClient(api)
        resp = client.get("/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["version"] == "v1"
