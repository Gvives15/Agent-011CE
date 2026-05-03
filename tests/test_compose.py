import os
import tempfile
import unittest
from unittest.mock import patch

from o11ce_cli.compose import ComposeNotFound, ensure_stack_layout, resolve_compose
from o11ce_cli.config import compose_path, env_path, stack_dir, volumes_dir


class TestCompose(unittest.TestCase):
    def test_resolve_compose_not_found(self):
        with patch("shutil.which", return_value=None):
            with self.assertRaises(ComposeNotFound):
                resolve_compose()

    def test_ensure_stack_layout_creates_files(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["O11CE_HOME"] = td
            try:
                ensure_stack_layout(overwrite_compose=True)
                self.assertTrue(stack_dir().exists())
                self.assertTrue(volumes_dir().exists())
                self.assertTrue(compose_path().exists())
                self.assertTrue(env_path().exists())
            finally:
                os.environ.pop("O11CE_HOME", None)


if __name__ == "__main__":
    unittest.main()

