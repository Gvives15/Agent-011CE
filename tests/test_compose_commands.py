import os
import tempfile
import unittest
from unittest.mock import patch

import requests

from o11ce_cli.compose import ComposeBinary, down, ensure_stack_layout, status, up


class TestComposeCommands(unittest.TestCase):
    def test_up_success_health(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["O11CE_HOME"] = td
            try:
                ensure_stack_layout(overwrite_compose=True)
                with patch("o11ce_cli.compose.resolve_compose", return_value=ComposeBinary(mode="docker-compose-plugin", argv_prefix=["docker", "compose"])):
                    with patch("subprocess.run") as m_run:
                        m_run.return_value.returncode = 0
                        m_run.return_value.stdout = ""
                        m_run.return_value.stderr = ""
                        with patch("requests.get") as m_get:
                            m_get.return_value.status_code = 200
                            up(wait_health=True, timeout_seconds=1)
            finally:
                os.environ.pop("O11CE_HOME", None)

    def test_down_success(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["O11CE_HOME"] = td
            try:
                ensure_stack_layout(overwrite_compose=True)
                with patch("o11ce_cli.compose.resolve_compose", return_value=ComposeBinary(mode="docker-compose", argv_prefix=["docker-compose"])):
                    with patch("subprocess.run") as m_run:
                        m_run.return_value.returncode = 0
                        m_run.return_value.stdout = ""
                        m_run.return_value.stderr = ""
                        down()
            finally:
                os.environ.pop("O11CE_HOME", None)

    def test_status_success(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["O11CE_HOME"] = td
            try:
                ensure_stack_layout(overwrite_compose=True)
                with patch("o11ce_cli.compose.resolve_compose", return_value=ComposeBinary(mode="docker-compose", argv_prefix=["docker-compose"])):
                    with patch("subprocess.run") as m_run:
                        m_run.return_value.returncode = 0
                        m_run.return_value.stdout = "ok"
                        m_run.return_value.stderr = ""
                        out = status()
                        self.assertEqual(out, "ok")
            finally:
                os.environ.pop("O11CE_HOME", None)


if __name__ == "__main__":
    unittest.main()

