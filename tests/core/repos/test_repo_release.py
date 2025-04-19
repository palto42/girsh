import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from loguru import logger
from requests.exceptions import HTTPError, RequestException

from girsh.core import repos


class SubstringMatcher:
    def __init__(self, containing: str) -> None:
        self.containing: str = containing.lower()

    def __eq__(self, other: Any) -> Any:
        return other.lower().find(self.containing) > -1

    def __unicode__(self) -> str:
        return f'a string containing "{self.containing}"'

    def __str__(self) -> str:
        return self.__unicode__().encode("utf-8").decode("utf-8")

    __repr__ = __unicode__


# -------------------------------
# Dummy classes used for testing
# -------------------------------
class DummyResponse:
    def __init__(self, json_data: Any, raise_for_status: bool = False) -> None:
        self._json = json_data
        self._raise_exc = raise_for_status
        self.headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
        if self._raise_exc:
            raise HTTPError("status")

    def json(self) -> Any:
        return self._json


# -------------------------------
# Tests for fetch_release_info
# -------------------------------
class TestFetchReleaseInfo(unittest.TestCase):
    def setUp(self) -> None:
        # Disable loguru logger output

        logger.remove()
        self.repo_version = "v1.0"

    def test_fetch_release_info_valid(self) -> None:
        dummy_json = {"tag_name": self.repo_version, "url": "dummy"}
        with patch("requests.get", return_value=DummyResponse(dummy_json)):
            info: dict[Any, Any] | None = repos.fetch_release_info(
                "owner/repo",
                self.repo_version,
                False,
            )
        self.assertEqual(info, dummy_json)

    def test_fetch_release_info_invalid_data(self) -> None:
        dummy_json = ["not", "a", "dict"]
        with patch("requests.get", return_value=DummyResponse(dummy_json)):
            info: dict[Any, Any] | None = repos.fetch_release_info(
                "owner/repo",
                self.repo_version,
                False,
            )
        self.assertIsNone(info)

    def test_fetch_release_info_status_exception(self) -> None:
        dummy_json = {"tag_name": self.repo_version, "url": "dummy"}
        with (
            patch("requests.get", return_value=DummyResponse(dummy_json, raise_for_status=True)),
            patch.object(logger, "error") as mock_logger_error,
        ):
            info: dict[Any, Any] | None = repos.fetch_release_info(
                "owner/repo",
                self.repo_version,
                False,
            )
            mock_logger_error.assert_called_once_with(SubstringMatcher(containing="status"))
        self.assertIsNone(info)

    def test_fetch_release_info_general_exception(self) -> None:
        with (
            patch("requests.get", side_effect=RequestException("error")),
            patch.object(logger, "error") as mock_logger_error,
        ):
            info: dict[Any, Any] | None = repos.fetch_release_info(
                "owner/repo",
                self.repo_version,
                False,
            )
            mock_logger_error.assert_called_once_with(SubstringMatcher(containing="error"))
        self.assertIsNone(info)


# -------------------------------
# Tests for is_new_version
# -------------------------------
class TestIsNewVersion(unittest.TestCase):
    def test_no_installed_info(self) -> None:
        self.assertTrue(repos.is_new_version(None, "v1", False))

    def test_different_version(self) -> None:
        self.assertTrue(repos.is_new_version("v0.9", "v1", False))

    def test_same_version_no_reinstall(self) -> None:
        self.assertEqual(repos.is_new_version("v1", "v1", False), repos.RepoResult.skipped)

    def test_same_version_with_reinstall(self) -> None:
        self.assertEqual(repos.is_new_version("v1", "v1", True), repos.RepoResult.installed)


# -------------------------------
# Tests for check_repo_release
# -------------------------------
class TestCheckRepoRelease(unittest.TestCase):
    # def setUp(self) -> None:
    #     # logger.remove()
    #     self.repo = "dummy/repo"
    #     self.version = "v1.0"

    @patch("girsh.core.repos.logger")
    @patch("girsh.core.repos.fetch_release_info", return_value=None)
    def test_check_repo_release_no_release_info(
        self, mock_fetch_release_info: MagicMock, mock_logger: MagicMock
    ) -> None:
        self.assertEqual(
            repos.check_repo_release(repo="dummy", target_version=None, current_version=None, reinstall=False),
            (repos.RepoResult.install_failed, {}),
        )
        mock_logger.error.assert_called_once_with("No valid release info received")

    @patch("girsh.core.repos.logger")
    @patch("girsh.core.repos.fetch_release_info", return_value={"tag_name": "v1.0"})
    @patch("girsh.core.repos.is_new_version", return_value=repos.RepoResult.installed)
    def test_check_repo_release_new_version(
        self, mock_is_new_version: MagicMock, mock_fetch_release_info: MagicMock, mock_logger: MagicMock
    ) -> None:
        self.assertEqual(
            repos.check_repo_release(repo="dummy", target_version=None, current_version=None, reinstall=False),
            (repos.RepoResult.installed, {"tag_name": "v1.0"}),
        )
        mock_logger.error.assert_not_called()

    @patch("girsh.core.repos.logger")
    @patch("girsh.core.repos.fetch_release_info", return_value={"tag_name": "v1.0"})
    @patch("girsh.core.repos.is_new_version", return_value=repos.RepoResult.skipped)
    def test_check_repo_release_skipped(
        self, mock_is_new_version: MagicMock, mock_fetch_release_info: MagicMock, mock_logger: MagicMock
    ) -> None:
        self.assertEqual(
            repos.check_repo_release(repo="dummy", target_version=None, current_version=None, reinstall=False),
            (repos.RepoResult.skipped, {}),
        )
        mock_logger.info.assert_called_once_with("dummy: No newer version than v1.0 found, skipping.")
        mock_logger.error.assert_not_called()


if __name__ == "__main__":
    unittest.main()
