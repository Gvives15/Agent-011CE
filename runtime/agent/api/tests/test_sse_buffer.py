import time

from django.test import TestCase

from api.services.run_manager import RunManager


class TestSseBuffer(TestCase):
    def test_replay_since_event_id(self):
        mgr = RunManager(max_events=10, max_age_seconds=60)
        run = mgr.create_run()
        mgr.emit(run.id, "status", {"phase": "routing"})
        mgr.emit(run.id, "token", {"text": "a"})
        mgr.emit(run.id, "token", {"text": "b"})

        all_events = mgr.get_events(run.id, last_event_id=None)
        assert [e.event_type for e in all_events] == ["status", "token", "token"]

        last_id = all_events[0].event_id
        replay = mgr.get_events(run.id, last_event_id=last_id)
        assert [e.event_type for e in replay] == ["token", "token"]

    def test_eviction_by_age(self):
        mgr = RunManager(max_events=100, max_age_seconds=0)
        run = mgr.create_run()
        mgr.emit(run.id, "status", {"phase": "routing"})
        time.sleep(0.01)
        ev = mgr.get_events(run.id, last_event_id=None)
        assert ev == []
