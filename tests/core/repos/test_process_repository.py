import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

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


@dataclass
class DummyRepository:
    version: str | None = None
    comment: str = ""
    package_pattern: str | None = None
    download_url: str | None = None
    filter_pattern: str | None = None
    multi_file: bool = False
    binary_name: str | None = None
    pre_update_commands: list[str] | None = None
    post_update_commands: list[str] | None = None


# -------------------------------
# Tests for process_repository
# -------------------------------
class TestProcessRepository(unittest.TestCase):
    def setUp(self) -> None:
        # Disable loguru logger output
        from loguru import logger

        logger.remove()
        # Create a temporary directory and file to use as installed file.
        self.temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
        self.temp_path: Path = Path(self.temp_dir.name)
        self.installed_file: Path = self.temp_path / "installed.yaml"
        self.download_dir = self.temp_path / "downloads"
        self.download_dir.mkdir()
        self.bin_dir = self.temp_path / "bin"
        self.bin_dir.mkdir()
        self.package_base_folder = self.temp_path / "packages"
        self.package_base_folder.mkdir()
        self.dummy_general_config = DummyGeneral(
            bin_base_folder=self.bin_dir,
            download_dir=self.download_dir,
            package_base_folder=self.package_base_folder,
            package_pattern="dummy_pattern",
        )
        self.dummy_repositories_config = DummyRepository()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_process_repository_no_release_info(self) -> None:
        with (
            patch("girsh.core.repos.check_repo_release", return_value=(repos.RepoResult.install_failed, {})),
            patch.object(logger, "info") as mock_logger,
        ):
            result, installed = repos.process_repository(
                repo="owner/repo",
                repo_config=self.dummy_repositories_config,
                general=self.dummy_general_config,
                installed_tag=None,
            )
        self.assertNotIn("owner/repo", installed)
        self.assertEqual(result, repos.RepoResult.install_failed)
        mock_logger.assert_called_once_with("Processing 'owner/repo': ")

    def test_process_repository_no_new_version(self) -> None:
        with (
            patch("girsh.core.repos.check_repo_release", return_value=(repos.RepoResult.skipped, {})),
            patch.object(logger, "info") as mock_logger,
        ):
            result, installed = repos.process_repository(
                repo="owner/repo",
                repo_config=self.dummy_repositories_config,
                general=self.dummy_general_config,
                installed_tag="v1.0",
            )
        self.assertEqual(installed, {})
        self.assertEqual(result, repos.RepoResult.skipped)
        mock_logger.assert_called_once_with("Processing 'owner/repo': ")

    def test_process_repository_download_no_package_pattern(self) -> None:
        dummy_release = {"tag_name": "v1.0"}
        self.dummy_general_config.package_pattern = "general_test_pattern"
        self.dummy_repositories_config.download_url = "dummy_download"
        with (
            patch("girsh.core.repos.check_repo_release", return_value=(repos.RepoResult.installed, dummy_release)),
            patch("girsh.core.repos.download_github_release", return_value=None) as mock_download_github_release,
        ):
            result, installed = repos.process_repository(
                repo="owner/repo",
                repo_config=self.dummy_repositories_config,
                general=self.dummy_general_config,
                installed_tag=None,
                dry_run=True,
            )
        mock_download_github_release.assert_called_once_with(
            "",
            self.dummy_general_config.package_pattern,
            self.dummy_general_config.download_dir,
            release_info=dummy_release,
            download_url=self.dummy_repositories_config.download_url,
        )
        self.assertEqual(result, repos.RepoResult.install_failed)
        self.assertEqual(installed, {})

    def test_process_repository_download_github_release_failed(self) -> None:
        dummy_release = {"tag_name": "v1.0", "url": "dummy"}
        with (
            patch("girsh.core.repos.check_repo_release", return_value=(repos.RepoResult.installed, dummy_release)),
            patch("girsh.core.repos.download_github_release", return_value=None),
        ):
            result, installed = repos.process_repository(
                repo="owner/repo",
                repo_config=DummyRepository(),
                general=self.dummy_general_config,
                installed_tag=None,
                dry_run=True,
            )
        self.assertEqual(result, repos.RepoResult.install_failed)
        self.assertEqual(installed, {})

    def test_process_repository_find_binary_none(self) -> None:
        dummy_release = {"tag_name": "v1.0", "url": "dummy"}
        with (
            patch("girsh.core.repos.check_repo_release", return_value=(repos.RepoResult.installed, dummy_release)),
            patch("girsh.core.repos.download_github_release", return_value=(Path("dummy.zip"), "v1.0")),
            patch("girsh.core.repos.extract_package"),
            patch("girsh.core.repos.find_binary", return_value=None),
        ):
            result, installed = repos.process_repository(
                repo="owner/repo",
                repo_config=self.dummy_repositories_config,
                general=self.dummy_general_config,
                installed_tag=None,
                dry_run=True,
            )
        self.assertEqual(result, repos.RepoResult.install_failed)
        self.assertEqual(installed, {})

    def test_process_repository_dry_run(self) -> None:
        dummy_release = {"tag_name": "v1.0", "url": "dummy"}
        with (
            patch("girsh.core.repos.check_repo_release", return_value=(repos.RepoResult.installed, dummy_release)),
            patch("girsh.core.repos.download_github_release", return_value=(Path("dummy.zip"), "v1.0")),
            patch("girsh.core.repos.extract_package"),
            patch("girsh.core.repos.find_binary", return_value=Path("dummy_binary")),
            patch.object(logger, "info") as mock_logger,
        ):
            result, installed = repos.process_repository(
                repo="owner/repo",
                repo_config=self.dummy_repositories_config,
                general=self.dummy_general_config,
                installed_tag=None,
                dry_run=True,
            )
        self.assertNotIn("owner/repo", installed)
        self.assertEqual(result, repos.RepoResult.dry_run_install)
        mock_logger.assert_called_with(
            "Dry-run: Found owner/repo version v1.0, extracted binary dummy_binary, skipping installation."
        )

    def test_process_repository_installation_success(self) -> None:
        dummy_release = {"tag_name": "v1.0", "url": "dummy"}
        with (
            patch("girsh.core.repos.check_repo_release", return_value=(repos.RepoResult.installed, dummy_release)),
            patch("girsh.core.repos.download_github_release", return_value=(Path("dummy.zip"), "v1.0")),
            patch("girsh.core.repos.extract_package"),
            patch("girsh.core.repos.find_binary", return_value=Path("dummy_binary")),
            patch("girsh.core.repos.copy_to_bin", return_value=Path("dummy_parent/dummy_install")),
            patch.object(logger, "info") as mock_logger,
        ):
            result, installed = repos.process_repository(
                repo="owner/repo",
                repo_config=self.dummy_repositories_config,
                general=self.dummy_general_config,
                installed_tag=None,
                dry_run=False,
            )
        self.assertIsNotNone(installed)
        self.assertEqual(installed["tag"], dummy_release["tag_name"])
        self.assertEqual(installed["binary"], "dummy_install")
        self.assertEqual(installed["path"], "dummy_parent")
        extract_dir = self.dummy_general_config.download_dir / "extracted"
        self.assertFalse(extract_dir.exists())
        mock_logger.assert_called_with("owner/repo: Installed dummy_install version v1.0 to dummy_parent")

    def test_process_repository_installation_multifile_success(self) -> None:
        dummy_release = {"tag_name": "v1.0", "url": "dummy"}
        dummy_package = self.download_dir / "dummy.zip"
        dummy_package_dir = self.bin_dir / "package"
        self.dummy_repositories_config.multi_file = True
        with (
            patch("girsh.core.repos.check_repo_release", return_value=(repos.RepoResult.installed, dummy_release)),
            patch("girsh.core.repos.download_github_release", return_value=(dummy_package, "v1.0")),
            patch("girsh.core.repos.extract_package"),
            patch("girsh.core.repos.find_binary", return_value=Path("dummy_binary")),
            patch("girsh.core.repos.copy_to_bin", return_value=Path("dummy_parent/dummy_install")),
            patch("girsh.core.repos.move_to_packages", return_value=dummy_package_dir),
            patch.object(logger, "info") as mock_logger,
        ):
            result, installed = repos.process_repository(
                repo="owner/repo",
                repo_config=self.dummy_repositories_config,
                general=self.dummy_general_config,
                installed_tag=None,
                dry_run=False,
            )
        self.assertIsNotNone(installed)
        self.assertEqual(installed["tag"], "v1.0")
        self.assertEqual(installed["binary"], dummy_package_dir.name)
        self.assertEqual(installed["path"], str(self.bin_dir))
        extracted_dir = self.dummy_general_config.download_dir / "extracted"
        self.assertFalse(extracted_dir.exists())
        mock_logger.assert_called_with(
            f"owner/repo: Installed package version {dummy_release['tag_name']} to {self.bin_dir}"
        )

    def test_pre_update_commands(self) -> None:
        dummy_release = {"tag_name": "v1.0", "url": "dummy"}
        self.dummy_repositories_config.pre_update_commands = ["echo Pre-update command executed"]
        with (
            patch("girsh.core.repos.check_repo_release", return_value=(42, dummy_release)),
            patch("girsh.core.repos.download_github_release", return_value=(Path("dummy.zip"), "v1.0")),
            patch("girsh.core.repos.extract_package"),
            patch("girsh.core.repos.find_binary", return_value=Path("dummy_binary")),
            patch("girsh.core.utils.run_commands", return_value=False),
            patch.object(logger, "info") as mock_logger,
        ):
            result, installed = repos.process_repository(
                repo="owner/repo",
                repo_config=self.dummy_repositories_config,
                general=self.dummy_general_config,
                installed_tag=None,
                dry_run=False,
            )
            self.assertEqual(result, repos.RepoResult.pre_commands_failed)
            mock_logger.assert_called_with("Processing 'owner/repo': ")

    def test_post_update_commands(self) -> None:
        dummy_release = {"tag_name": "v1.0", "url": "dummy"}
        self.dummy_repositories_config.post_update_commands = ["echo Pre-update command executed"]
        with (
            patch("girsh.core.repos.check_repo_release", return_value=(42, dummy_release)),
            patch("girsh.core.repos.download_github_release", return_value=(Path("dummy.zip"), "v1.0")),
            patch("girsh.core.repos.extract_package"),
            patch("girsh.core.repos.find_binary", return_value=Path("dummy_binary")),
            patch("girsh.core.utils.run_commands", side_effect=[True, False]),
            patch("girsh.core.repos.copy_to_bin", return_value=Path("dummy_parent/dummy_install")),
            patch.object(logger, "info") as mock_logger,
        ):
            result, installed = repos.process_repository(
                repo="owner/repo",
                repo_config=self.dummy_repositories_config,
                general=self.dummy_general_config,
                installed_tag=None,
                dry_run=False,
            )
            self.assertEqual(result, repos.RepoResult.post_commands_failed)
            mock_logger.assert_called_with("owner/repo: Installed dummy_install version v1.0 to dummy_parent")


if __name__ == "__main__":
    unittest.main()
