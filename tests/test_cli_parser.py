import unittest

from o11ce_cli.main import build_parser


class TestCliParser(unittest.TestCase):
    def test_help_builds(self):
        p = build_parser()
        args = p.parse_args(["--version"])
        self.assertTrue(args.version)


if __name__ == "__main__":
    unittest.main()

