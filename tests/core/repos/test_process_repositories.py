import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

from loguru import logger

from girsh.core import repos


# -------------------------------
# Dummy classes used for testing
# -------------------------------
@dataclass
class DummyGeneral:
    bin_base_folder: Path
    download_dir: Path
    package_base_folder: Path
    package_pattern: str


# -------------------------------
# Tests for process_repositories
# -------------------------------
class TestProcessRepositories(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path: Path = Path(self.temp_dir.name)
        self.download_dir = self.temp_path / "downloads"
        self.bin_dir = self.temp_path / "bin"
        self.package_base_folder = self.temp_path / "packages"
        self.general = DummyGeneral(
            bin_base_folder=self.bin_dir,
            download_dir=self.download_dir,
            package_base_folder=self.package_base_folder,
            package_pattern="dummy_pattern",
        )
        self.repositories = {
            "owner/repo1": MagicMock(),
            "owner/repo2": MagicMock(),
        }
        self.installed = {
            "owner/repo1": {"tag": "v1.0"},
        }

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_process_repositories_undefined(self) -> None:
        updated_installed, summary = repos.process_repositories(
            {},
            self.general,
            self.installed,
            reinstall=[],
            dry_run=False,
        )

        self.assertEqual(summary, {})
        self.assertEqual(updated_installed, self.installed)

    @patch("pathlib.Path.mkdir", side_effect=PermissionError("No permission"))
    @patch.object(logger, "error")
    def test_process_repositories_permission_denied(self, mock_logger_error: MagicMock, mock_mkdir: MagicMock) -> None:
        updated_installed, summary = repos.process_repositories(
            self.repositories,
            self.general,
            self.installed,
            reinstall=[],
            dry_run=False,
        )
        mock_logger_error.assert_called_once_with(
            f"Permission denied when creating download folder '{self.general.download_dir}'"
        )
        self.assertEqual(updated_installed, self.installed)
        self.assertEqual(summary, {repos.RepoResult.exception: 1})

    @patch("girsh.core.repos.logger")
    @patch("girsh.core.repos.process_repository")
    def test_process_repositories_install(self, mock_process_repository: MagicMock, mock_logger: MagicMock) -> None:
        mock_process_repository.side_effect = [
            (repos.RepoResult.installed, {"tag": "v2.0", "binary": "binary1", "path": "/usr/local/bin"}),
            (repos.RepoResult.installed, {"tag": "v1.0", "binary": "binary2", "path": "/usr/local/bin"}),
        ]

        updated_installed, summary = repos.process_repositories(
            self.repositories,
            self.general,
            self.installed,
            reinstall=[],
            dry_run=False,
        )

        self.assertEqual(summary[repos.RepoResult.installed], 2)
        self.assertEqual(updated_installed["owner/repo1"]["tag"], "v2.0")
        self.assertEqual(updated_installed["owner/repo2"]["tag"], "v1.0")
        mock_logger.success.assert_called_with("owner/repo2 installed version v1.0")

    @patch("girsh.core.repos.logger")
    @patch("girsh.core.repos.process_repository")
    def test_process_repositories_update(self, mock_process_repository: MagicMock, mock_logger: MagicMock) -> None:
        mock_process_repository.side_effect = [
            (repos.RepoResult.installed, {"tag": "v2.0", "binary": "binary1", "path": "/usr/local/bin"}),
            (repos.RepoResult.updated, {"tag": "v1.0", "binary": "binary2", "path": "/usr/local/bin"}),
        ]
        self.installed["owner/repo2"] = {"tag": "v.1"}

        updated_installed, summary = repos.process_repositories(
            self.repositories,
            self.general,
            self.installed,
            reinstall=[],
            dry_run=False,
        )

        self.assertEqual(summary[repos.RepoResult.installed], 1)
        self.assertEqual(summary[repos.RepoResult.updated], 1)
        self.assertEqual(updated_installed["owner/repo1"]["tag"], "v2.0")
        self.assertEqual(updated_installed["owner/repo2"]["tag"], "v1.0")
        mock_logger.success.assert_called_with("owner/repo2 updated from v.1 to v1.0")

    @patch("girsh.core.repos.process_repository")
    def test_process_repositories_no_new_version(self, mock_process_repository: MagicMock) -> None:
        mock_process_repository.side_effect = [
            (repos.RepoResult.skipped, {}),
            (repos.RepoResult.skipped, {}),
        ]

        updated_installed, summary = repos.process_repositories(
            self.repositories,
            self.general,
            self.installed,
            reinstall=[],
            dry_run=False,
        )

        self.assertEqual(summary[repos.RepoResult.skipped], 2)
        self.assertEqual(updated_installed["owner/repo1"]["tag"], "v1.0")
        self.assertNotIn("owner/repo2", updated_installed)

    @patch("girsh.core.repos.process_repository")
    def test_process_repositories_dry_run(self, mock_process_repository: MagicMock) -> None:
        mock_process_repository.side_effect = [
            (repos.RepoResult.dry_run_install, {}),
            (repos.RepoResult.dry_run_install, {}),
        ]

        updated_installed, summary = repos.process_repositories(
            self.repositories,
            self.general,
            self.installed,
            reinstall=[],
            dry_run=True,
        )

        self.assertEqual(summary[repos.RepoResult.dry_run_install], 2)
        self.assertEqual(updated_installed["owner/repo1"]["tag"], "v1.0")
        self.assertNotIn("owner/repo2", updated_installed)

    @patch("girsh.core.repos.process_repository")
    def test_process_repositories_install_failed(self, mock_process_repository: MagicMock) -> None:
        mock_process_repository.side_effect = [
            (repos.RepoResult.install_failed, {}),
            (repos.RepoResult.install_failed, {}),
        ]

        updated_installed, summary = repos.process_repositories(
            self.repositories,
            self.general,
            self.installed,
            reinstall=[],
            dry_run=False,
        )

        self.assertEqual(summary[repos.RepoResult.install_failed], 2)
        self.assertEqual(updated_installed["owner/repo1"]["tag"], "v1.0")
        self.assertNotIn("owner/repo2", updated_installed)

    @patch("girsh.core.repos.logger")
    @patch("girsh.core.repos.process_repository")
    def test_process_repositories_reinstall(self, mock_process_repository: MagicMock, mock_logger: MagicMock) -> None:
        mock_process_repository.side_effect = [
            (repos.RepoResult.installed, {"tag": "v2.0", "binary": "binary1", "path": "/usr/local/bin"}),
            (repos.RepoResult.installed, {"tag": "v1.0", "binary": "binary2", "path": "/usr/local/bin"}),
        ]
        self.installed["owner/repo1"] = {"tag": "v2.0"}

        updated_installed, summary = repos.process_repositories(
            self.repositories,
            self.general,
            self.installed,
            reinstall=["owner/repo1"],
            dry_run=False,
        )
        mock_process_repository.assert_called_once_with(
            "owner/repo1",
            ANY,
            ANY,
            ANY,
            reinstall=True,
            dry_run=ANY,
        )
        self.assertEqual(summary[repos.RepoResult.installed], 1)
        self.assertEqual(updated_installed["owner/repo1"]["tag"], "v2.0")
        mock_logger.success.assert_any_call("owner/repo1 installed version v2.0")


if __name__ == "__main__":
    unittest.main()
