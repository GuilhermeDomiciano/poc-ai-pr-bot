import json
import unittest

from domain.payload_parser import CONTRACT_ERROR_PREFIX, parse_payload


def _valid_payload_with_path(file_path: str) -> str:
    payload = {
        "files": {
            file_path: "content",
        },
        "branch": "feature/test",
        "commit": "feat(test): payload parser",
        "pr_title": "Test payload parser",
        "pr_body": "Body",
    }
    return json.dumps(payload)


class PayloadParserTests(unittest.TestCase):
    def test_parse_payload_rejects_non_json_with_clear_error(self) -> None:
        with self.assertRaises(RuntimeError) as raised_error:
            parse_payload("this is not json")

        self.assertIn(CONTRACT_ERROR_PREFIX, str(raised_error.exception))
        self.assertIn("no valid JSON object found", str(raised_error.exception))

    def test_parse_payload_rejects_paths_outside_backend_frontend(self) -> None:
        with self.assertRaises(RuntimeError) as raised_error:
            parse_payload(_valid_payload_with_path("src/app.py"))

        self.assertIn("must start with 'backend/' or 'frontend/'", str(raised_error.exception))

    def test_parse_payload_rejects_path_traversal(self) -> None:
        with self.assertRaises(RuntimeError) as raised_error:
            parse_payload(_valid_payload_with_path("backend/../secrets.txt"))

        self.assertIn("path traversal", str(raised_error.exception))

    def test_parse_payload_rejects_absolute_path(self) -> None:
        with self.assertRaises(RuntimeError) as raised_error:
            parse_payload(_valid_payload_with_path("/etc/passwd"))

        self.assertIn("repository-relative", str(raised_error.exception))


if __name__ == "__main__":
    unittest.main()
