from django.test import TestCase

from api.schemas import Attachment, RunOptions
from api.services.routing import decide_route


class TestRouting(TestCase):
    def test_vision_never_forces_logic(self):
        route, model = decide_route(
            message="mirá la imagen",
            attachments=[Attachment(type="image", path="workspace/a.png", mime="image/png")],
            options=RunOptions(vision="never", preferred_model="auto", profile="dev", enable_browser=False),
            models={"logic": "L", "vision": "V", "ui": "U"},
            enable_ui=False,
        )
        assert route == "logic"
        assert model == "L"

    def test_image_forces_vision(self):
        route, model = decide_route(
            message="hola",
            attachments=[Attachment(type="image", path="workspace/a.png", mime="image/png")],
            options=RunOptions(vision="auto", preferred_model="auto", profile="dev", enable_browser=False),
            models={"logic": "L", "vision": "V", "ui": "U"},
            enable_ui=False,
        )
        assert route == "vision"
        assert model == "V"

    def test_ui_tars_requires_enable(self):
        route, model = decide_route(
            message="hola",
            attachments=[],
            options=RunOptions(vision="auto", preferred_model="ui-tars", profile="dev", enable_browser=False),
            models={"logic": "L", "vision": "V", "ui": "U"},
            enable_ui=False,
        )
        assert route == "error"
        assert model == ""
