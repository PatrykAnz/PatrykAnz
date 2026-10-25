import tempfile
import runpy
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from xml.etree import ElementTree

import requests

import generate_readme


def response(data=None, status=200):
    result = Mock(status_code=status)
    result.json.return_value = data
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(str(status))
    return result


class ReadmeTests(unittest.TestCase):
    @patch("requests.get", side_effect=requests.HTTPError("https://api.github.com/repos/private/example"))
    def test_cli_does_not_expose_private_urls(self, get):
        with self.assertRaises(SystemExit) as error:
            runpy.run_path(str(Path(generate_readme.__file__)), run_name="__main__")
        self.assertEqual(
            str(error.exception),
            "GitHub API request failed; existing profile stats were preserved.",
        )

    @patch("generate_readme.requests.get")
    def test_authenticated_stats_and_timeouts(self, get):
        get.side_effect = [
            response({"login": "PatrykAnz"}),
            response([{"name": "example", "owner": {"login": "PatrykAnz"}}]),
            response([{"login": "patrykanz", "contributions": 12}]),
            response({"Python": 600}),
        ]
        self.assertEqual(
            generate_readme.get_github_stats("PatrykAnz", "test-token"),
            {"repos": 1, "commits": 12, "loc": 10},
        )
        for call in get.call_args_list:
            self.assertEqual(call.kwargs["timeout"], 20)

    @patch("generate_readme.requests.get")
    def test_pagination_and_empty_repository(self, get):
        repo = {"name": "example", "owner": {"login": "PatrykAnz"}}
        # Generate one no-content contributor response and one empty language map per repo.
        get.side_effect = [response([repo] * 100), response([])] + [
            item for _ in range(100) for item in (response(status=204), response({}))
        ]
        self.assertEqual(
            generate_readme.get_github_stats("PatrykAnz"),
            {"repos": 100, "commits": 0, "loc": 0},
        )
        self.assertEqual(get.call_args_list[1].kwargs["params"]["page"], 2)

    @patch("generate_readme.requests.get")
    def test_contributors_pagination(self, get):
        get.side_effect = [
            response([{"name": "example", "owner": {"login": "PatrykAnz"}}]),
            response([{"login": "someone-else", "contributions": 1}] * 100),
            response([{"login": "PatrykAnz", "contributions": 7}]),
            response({}),
        ]
        self.assertEqual(
            generate_readme.get_github_stats("PatrykAnz"),
            {"repos": 1, "commits": 7, "loc": 0},
        )
        self.assertEqual(get.call_args_list[2].kwargs["params"]["page"], 2)

    def test_api_failures_preserve_existing_svg(self):
        repo = {"name": "example", "owner": {"login": "PatrykAnz"}}
        cases = [
            [response(status=401)],
            [response({"login": "PatrykAnz"}), response(status=403)],
            [response({"login": "PatrykAnz"}), response([repo]), response(status=500)],
            [response({"login": "PatrykAnz"}), response([repo]), response([]), response(status=503)],
            [requests.Timeout("GitHub timed out")],
        ]
        with tempfile.TemporaryDirectory() as directory:
            svg = Path(directory) / "neofetch.svg"
            svg.write_text("previous stats")
            for replies in cases:
                with self.subTest(replies=replies), patch(
                    "generate_readme.requests.get", side_effect=replies
                ):
                    with self.assertRaises(requests.RequestException):
                        generate_readme.generate_neofetch_svg(svg, github_token="test-token")
                    self.assertEqual(svg.read_text(), "previous stats")

    @patch.dict("os.environ", {"MONKEYTYPE_USERNAME": ""})
    @patch("generate_readme.get_github_stats", return_value={"repos": 1, "commits": 12, "loc": 10})
    def test_svg_replacement_and_write_failure(self, stats):
        with tempfile.TemporaryDirectory() as directory:
            svg = Path(directory) / "neofetch.svg"
            generate_readme.generate_neofetch_svg(svg)
            ElementTree.parse(svg)
            previous = svg.read_bytes()
            with patch("generate_readme.os.replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    generate_readme.generate_neofetch_svg(svg)
            self.assertEqual(svg.read_bytes(), previous)
            self.assertEqual(list(Path(directory).iterdir()), [svg])


if __name__ == "__main__":
    unittest.main()
