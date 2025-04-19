import argparse
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml
from loguru import logger

from girsh.core import config


# Dummy resource context manager for simulating a template file.
class DummyResource:
    def __init__(self, content: str) -> None:
        self._content: str = content

    def __enter__(self) -> "DummyResource":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def read_text(self) -> str:
        return self._content


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


class TestConfigModule(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()  # Remove all loguru handlers to silence logging output
        # Create a temporary directory and file to use as installed file.
        self.temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
        self.temp_path: Path = Path(self.temp_dir.name)
        self.download_dir = self.temp_path / "downloads"
        self.bin_dir = self.temp_path / "bin"
        self.package_base_folder = self.temp_path / "packages"
        self.installed_file: Path = self.temp_path / "installed.yaml"
        self.installed_name = self.installed_file.name
        self.test_general: config.General = config.General(
            bin_base_folder=self.bin_dir,
            download_dir=self.download_dir,
            package_base_folder=self.package_base_folder,
            installed_file=self.installed_file,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    # -------------------------------
    # Tests for convert_to_bool
    # -------------------------------

    def test_convert_to_bool_is_bool(self) -> None:
        self.assertTrue(config.convert_to_bool(True))
        self.assertFalse(config.convert_to_bool(False))

    # -------------------------------
    # Test dataclasses and data conversion
    # -------------------------------
    def test_conversion_error(self) -> None:
        with self.assertRaises(config.ConversionError) as cm:
            raise config.ConversionError("invalid", int)
        self.assertEqual(str(cm.exception), "Cannot convert 'invalid' to int")
        self.assertEqual(cm.exception.value, "invalid")
        self.assertEqual(cm.exception.expected_type, int)

    def test_general_set_path(self) -> None:
        g: config.General = config.General()
        g.bin_base_folder = "/dummy/path"  # type: ignore[assignment]
        self.assertIsInstance(g.bin_base_folder, Path)
        self.assertEqual(g.bin_base_folder, Path("/dummy/path"))

    def test_general_set_string(self) -> None:
        g: config.General = config.General()
        g.package_pattern = ".*arm64.*(gz|zip)$"
        self.assertIsInstance(g.package_pattern, str)
        self.assertEqual(g.package_pattern, ".*arm64.*(gz|zip)$")

    def test_general_invalid_type(self) -> None:
        g: config.General = config.General()
        # Should fail because Path-like is expected
        with self.assertRaises(config.ConversionError):
            g.installed_file = 1.1  # type: ignore[assignment]

    def test_repository_set_str(self) -> None:
        r: config.Repository = config.Repository()
        r.comment = 123  # type: ignore[assignment] # Should be auto-converted to a string
        self.assertIsInstance(r.comment, str)
        self.assertEqual(r.comment, "123")

    def test_repository_set_bool(self) -> None:
        r: config.Repository = config.Repository()
        r.multi_file = "True"  # type: ignore[assignment] # Should be auto-converted to bool
        self.assertIsInstance(r.multi_file, bool)
        self.assertEqual(r.multi_file, True)

    def test_repository_invalid_conversion(self) -> None:
        r: config.Repository = config.Repository()
        with self.assertRaises(config.ConversionError):
            r.multi_file = "not_a_boolean"  # type: ignore[assignment] # Should raise ConversionError

    # -------------------------------
    # Tests for update_general_config
    # -------------------------------

    def test_update_general_config_is_not_dict(self) -> None:
        updated = config.update_general_config(self.test_general, {"general": ["list"]})
        self.assertEqual(updated, self.test_general)

    def test_update_general_config_is_none(self) -> None:
        updated = config.update_general_config(self.test_general, {"general": None})
        self.assertEqual(updated, self.test_general)

    def test_update_general_config_skip_extra_data(self) -> None:
        general_config = config.General()
        data: dict = {"general": {"dummy": "dummy_string"}}
        self.assertEqual(config.update_general_config(general_config, data), general_config)

    def test_update_general_config_with_general_and_repositories(self) -> None:
        data: dict[str, Any] = {
            "general": {"installed_file": "/new/path", "package_pattern": "test_pattern"},
            "repositories": {"repo1": {"comment": "Test repo", "binary_name": "test_binary"}},
        }
        general = config.update_general_config(self.test_general, data)
        self.assertEqual(general.installed_file, Path("/new/path"))
        self.assertEqual(general.package_pattern, "test_pattern")
        self.assertFalse(hasattr(general, "repositories"))
        self.assertFalse(hasattr(general, "repo1"))

    # -------------------------------
    # Tests for update_repositories_config
    # -------------------------------

    def test_update_repositories_config_with_data(self) -> None:
        data: dict[str, Any] = {
            "general": {"installed_file": self.installed_name, "package_pattern": "test_pattern"},
            "repositories": {"repo1": {"comment": "Test repo", "binary_name": "test_binary"}},
        }
        repositories = config.update_repositories_config(repo_config={}, data=data, default_pattern="test_pattern")
        self.assertIn("repo1", repositories)
        repo: config.Repository = repositories["repo1"]
        self.assertEqual(repo.comment, "Test repo")
        self.assertEqual(repo.binary_name, "test_binary")
        # If no package_pattern is provided for the config.Repository, it defaults to config.General.package_pattern.
        self.assertEqual(repo.package_pattern, "test_pattern")

    def test_update_repositories_config_not_dict(self) -> None:
        data: dict[str, Any] = {"repositories": []}
        with patch.object(logger, "error") as mock_logger_error:
            repositories = config.update_repositories_config(repo_config={}, data=data, default_pattern="test_pattern")
            mock_logger_error.assert_called_once_with("The 'repositories' YAML config is not a dictionary.")
            self.assertEqual(repositories, {})

    def test_update_repositories_config_repo_config_none(self) -> None:
        data: dict = {"repositories": {"repo1": None}}
        repositories = config.update_repositories_config(repo_config={}, data=data, default_pattern="test_pattern")
        self.assertIn("repo1", repositories)
        self.assertIsInstance(repositories["repo1"], config.Repository)

    def test_update_repositories_config_repo_not_in_data(self) -> None:
        repositories = {"Dummy": config.Repository()}
        data: dict = {"other": "TEST"}
        repositories = config.update_repositories_config(
            repo_config=repositories, data=data, default_pattern="test_pattern"
        )
        self.assertEqual(list(repositories.keys()), ["Dummy"])

    def test_update_repositories_config_repo_has_pattern(self) -> None:
        repositories = {"Dummy": config.Repository()}
        data: dict = {"repositories": {"Dummy": {"package_pattern": "1x2y"}}}
        repositories = config.update_repositories_config(
            repo_config=repositories, data=data, default_pattern="test_pattern"
        )
        self.assertEqual(repositories["Dummy"].package_pattern, "1x2y")

    def test_update_repositories_config_type_error(self) -> None:
        repositories = {"Dummy": config.Repository()}
        data: dict = {"repositories": {"Dummy": {"multi_file": "NotBool"}}}
        with patch.object(logger, "error") as mock_logger_error:
            updated = config.update_repositories_config(
                repo_config=repositories, data=data, default_pattern="test_pattern"
            )
            mock_logger_error.assert_called_once_with("Repository 'Dummy': Cannot convert 'NotBool' to bool")
            self.assertEqual(repositories, updated)

    # -------------------------------
    # Tests for load_yaml_config
    # -------------------------------

    def test_load_yaml_config_success(self) -> None:
        # Create a temporary file with valid YAML data.
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp_file:
            try:
                config_data: dict[str, Any] = {
                    "general": {"installed_file": self.installed_name},
                    "repositories": {"repo2": {"comment": "Another repo", "binary_name": "binary2"}},
                }
                tmp_file.write(yaml.safe_dump(config_data))
                tmp_file.close()
                with patch.object(logger, "trace") as mock_logger_debug:
                    general, repositories = config.load_yaml_config(tmp_file.name)
                    self.assertEqual(general.installed_file, Path(self.installed_name))
                    self.assertIn("repo2", repositories)
                    calls = [call.args[0] for call in mock_logger_debug.call_args_list]
                    self.assertTrue(any("Loaded config:" in s for s in calls))
            finally:
                Path(tmp_file.name).unlink()

    def test_load_yaml_config_no_data(self) -> None:
        # Create a temporary file with YAML that is not a dict.
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp_file:
            try:
                tmp_file.write(yaml.safe_dump(["not", "a", "dict"]))
                tmp_file.close()
                with patch.object(logger, "warning") as mock_logger_warning:
                    config.load_yaml_config(tmp_file.name)
                    mock_logger_warning.assert_called_once()
            finally:
                Path(tmp_file.name).unlink()

    def test_load_yaml_config_file_not_found(self) -> None:
        non_existent: str = "nonexistent_config.yaml"
        with patch.object(logger, "error") as mock_logger_error, patch("sys.exit", side_effect=SystemExit) as mock_exit:
            with self.assertRaises(SystemExit):
                config.load_yaml_config(non_existent)
            mock_logger_error.assert_called_once_with(f"Config file '{non_existent}' not found.")
            mock_exit.assert_called_once_with(1)

    def test_load_yaml_config_permission_error(self) -> None:
        fake_path: str = "fake_config.yaml"
        with (
            patch("girsh.core.config.Path.open", side_effect=PermissionError("No permission")),
            patch.object(logger, "error") as mock_logger_error,
            patch("sys.exit", side_effect=SystemExit) as mock_exit,
        ):
            with self.assertRaises(SystemExit):
                config.load_yaml_config(fake_path)
            mock_logger_error.assert_called_once_with(f"Permission denied when reading config file '{fake_path}'.")
            mock_exit.assert_called_once_with(1)

    def test_load_yaml_config_scanner_error(self) -> None:
        # Create a temporary file with invalid YAML data.
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp_file:
            try:
                yaml_invalid = """
invalid:
  Test: 123
  - list
"""
                tmp_file.write(yaml_invalid)
                tmp_file.close()
                with (
                    patch.object(logger, "error") as mock_logger_error,
                    patch("sys.exit", side_effect=SystemExit) as mock_exit,
                ):
                    with self.assertRaises(SystemExit):
                        general, repositories = config.load_yaml_config(tmp_file.name)
                    mock_exit.assert_called_once_with(1)
                    mock_logger_error.assert_called_once_with(
                        SubstringMatcher(containing="YAML syntax error in config file")
                    )
                    # self.assertEqual(general.installed_file, Path(self.installed_name))
                    # self.assertIn("repo2", repositories)
                    # calls = [call.args[0] for call in mock_logger_debug.call_args_list]
                    # self.assertTrue(any("Loaded config:" in s for s in calls))

            finally:
                Path(tmp_file.name).unlink()

    def test_load_yaml_config_extra_keys(self) -> None:
        # Create a temporary file with invalid YAML data.
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp_file:
            try:
                yaml_extra = """
repositories:
  dummy:
extra_config:
  Test: 123
"""
                tmp_file.write(yaml_extra)
                tmp_file.close()
                with (
                    patch.object(logger, "warning") as mock_logger,
                ):
                    general, repositories = config.load_yaml_config(tmp_file.name)
                    mock_logger.assert_called_once_with("Config YAML contains unexpected keys: {'extra_config'}")
            finally:
                Path(tmp_file.name).unlink()

    def test_load_yaml_config_no_general(self) -> None:
        # Create a temporary file without general section
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp_file:
            try:
                yaml_extra = """
repositories:
  dummy:
"""
                tmp_file.write(yaml_extra)
                tmp_file.close()
                with (
                    patch.object(logger, "warning") as mock_logger,
                ):
                    general, repositories = config.load_yaml_config(tmp_file.name)
                    mock_logger.assert_not_called()
            finally:
                Path(tmp_file.name).unlink()
            self.assertTrue("dummy" in repositories)
            self.assertEqual(general, config.General())

    def test_load_yaml_config_no_repositories(self) -> None:
        # Create a temporary file without repositories section
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp_file:
            try:
                yaml_extra = """
general:
  installed_file: dummy_file
"""
                tmp_file.write(yaml_extra)
                tmp_file.close()
                with (
                    patch.object(logger, "warning") as mock_logger,
                ):
                    general, repositories = config.load_yaml_config(tmp_file.name)
                    mock_logger.assert_called_once_with(
                        "No repositories configured.{'general': {'installed_file': 'dummy_file'}}"
                    )
            finally:
                Path(tmp_file.name).unlink()
            self.assertEqual(repositories, {})
            self.assertEqual(general.installed_file, Path("dummy_file"))

    # -------------------------------
    # Tests for edit_config
    # -------------------------------

    def test_edit_config_file_does_not_exist_abort(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path: Path = Path(tmpdir) / "nonexistent.yaml"
            # Simulate user input "n" to abort.
            with patch("builtins.input", return_value="n"), patch.object(logger, "error") as mock_logger_error:
                result: int = config.edit_config(config_path)
                self.assertEqual(result, 0)
                mock_logger_error.assert_called_once_with("Operation aborted. No file was created.")

    def test_edit_config_file_does_not_exist_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path: Path = Path(tmpdir) / "new_config.yaml"
            dummy_template: str = "dummy: template"
            # Create a dummy CompletedProcess to simulate a successful editor run.
            dummy_completed_process: subprocess.CompletedProcess = subprocess.CompletedProcess(
                args=["editor"], returncode=0
            )
            # Simulate user input "y" and a template from resources.
            with (
                patch("builtins.input", return_value="y"),
                patch("girsh.core.config.resources.path", return_value=DummyResource(dummy_template)),
                patch("subprocess.run", return_value=dummy_completed_process),
                patch.object(logger, "info") as mock_logger_info,
            ):
                result: int = config.edit_config(config_path)
                self.assertEqual(result, 0)
                self.assertEqual(config_path.read_text(), dummy_template)
                calls = [call.args[0] for call in mock_logger_info.call_args_list]
                self.assertTrue(any("Create config file from template" in s for s in calls))

    def test_edit_config_file_exists_no_change(self) -> None:
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            tmp.write("original content")
            tmp_path: Path = Path(tmp.name)
            try:
                with (
                    patch("subprocess.run", return_value=None),
                    patch.object(logger, "info") as mock_logger_info,
                ):
                    result: int = config.edit_config(tmp_path)
                    self.assertEqual(result, 0)
                    calls = [call.args[0] for call in mock_logger_info.call_args_list]
                    self.assertTrue(any("No changes were made to the config file." in s for s in calls))
            finally:
                tmp_path.unlink()

    def test_edit_config_file_exists_modified(self) -> None:
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            tmp.write("original content")
            tmp_path: Path = Path(tmp.name)
        try:
            original_mod_time: float = 1000.0
            new_mod_time: float = 2000.0
            # Patch Path.stat so that first call returns original_mod_time and second returns new_mod_time.
            with (
                patch("subprocess.run", return_value=None),
                patch.object(
                    Path,
                    "stat",
                    side_effect=[
                        type("stat", (), {"st_mtime": original_mod_time})(),
                        type("stat", (), {"st_mtime": original_mod_time})(),
                        type("stat", (), {"st_mtime": new_mod_time})(),
                    ],
                ),
                patch.object(logger, "info") as mock_logger_info,
            ):
                result: int = config.edit_config(tmp_path)
                self.assertEqual(result, 0)
                calls = [call.args[0] for call in mock_logger_info.call_args_list]
                self.assertTrue(any("The config file was modified." in s for s in calls))
        finally:
            tmp_path.unlink()

    def test_edit_config_editor_not_found(self) -> None:
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            tmp.write("content")
            tmp_path: Path = Path(tmp.name)
        try:
            with (
                patch.dict(os.environ, {"EDITOR": "nonexistent_editor"}),
                patch("subprocess.run", side_effect=FileNotFoundError("Not found")),
                patch.object(logger, "error") as mock_logger_error,
            ):
                result: int = config.edit_config(tmp_path)
                self.assertEqual(result, 1)
                mock_logger_error.assert_called_once_with(
                    "Error: Editor 'nonexistent_editor' not found. Please set the EDITOR environment variable."
                )
        finally:
            tmp_path.unlink()

    def test_edit_config_subprocess_called_process_error(self) -> None:
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            tmp.write("content")
            tmp_path: Path = Path(tmp.name)
        try:
            with (
                patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd", "error")),
                patch.object(Path, "stat", return_value=type("stat", (), {"st_mtime": 1234})()),
                patch.object(logger, "error") as mock_logger_error,
            ):
                result: int = config.edit_config(tmp_path)
                self.assertEqual(result, 1)
                self.assertTrue(
                    any("Error: Failed to open" in call.args[0] for call in mock_logger_error.call_args_list)
                )
        finally:
            tmp_path.unlink()

    # -------------------------------
    # Tests for get_arguments
    # -------------------------------

    def test_get_arguments_default(self) -> None:
        test_args: list[str] = ["prog"]
        with patch("sys.argv", test_args):
            args: argparse.Namespace = config.get_arguments()
            expected_default: Path = Path.home() / ".config" / "girsh" / "settings.yaml"
            self.assertEqual(args.config, expected_default)
            self.assertFalse(args.reinstall)
            self.assertFalse(args.dry_run)
            self.assertFalse(args.uninstall)
            self.assertFalse(args.uninstall_all)
            self.assertFalse(args.clean)
            self.assertFalse(args.show)
            self.assertFalse(args.edit)
            self.assertFalse(args.verbose)

    def test_get_arguments_all_options(self) -> None:
        test_args: list[str] = [
            "prog",
            "--config",
            self.installed_name,
            "--reinstall",
            "--dry-run",
            "--uninstall",
            "--uninstall-all",
            "--clean",
            "--show",
            "--edit",
            "--verbose",
            "--version",
        ]
        # The --version flag will trigger sys.exit, so we expect a SystemExit.
        with patch("sys.argv", test_args), patch("argparse._sys.argv", test_args), self.assertRaises(SystemExit):
            config.get_arguments()


if __name__ == "__main__":
    unittest.main()
