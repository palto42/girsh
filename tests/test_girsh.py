# ty: ignore[unresolved-attribute]
import contextlib
import sys
import tempfile
import unittest
import unittest.mock
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from unittest.mock import patch

# Import the module under test as specified.
from girsh import girsh


# --- Dummy CLI arguments ---
@dataclass
class DummyArgs:
    edit: bool = False
    clean: bool = False
    verbose: bool = False
    show: bool = False
    uninstall: bool = False
    uninstall_all: bool = False
    dry_run: bool = False
    reinstall: bool = False
    config: str = "dummy_config.yaml"
    system: bool = False
    proxy: str | None = None
    test_proxy: bool = False


# --- Dummy general config class ---
class DummyGeneral:
    pass


class DummyRepoResult(Enum):
    # Installation status changed
    result1 = 1
    result2 = 2
    fail1 = 3
    fail2 = 4


DUMMY_EDIT_RETURN = 42
DUMMY_SHOW_RETURN = 43
DUMMY_ELEVATED_EXIT = 44
DUMMY_REPO_CONFIG = {"repo1": "config1", "repo2": "config2"}


def dummy_elevate_privileges() -> None:
    sys.exit(DUMMY_ELEVATED_EXIT)


def dummy_edit_config(config: str) -> int:
    return DUMMY_EDIT_RETURN


def dummy_clean_downloads_folder(download_dir: Path) -> int:
    return 0


def dummy_load_yaml_config(config: str) -> tuple[DummyGeneral, dict]:
    # Do nothing for testing.
    general: Any = DummyGeneral()
    general.installed_file = "dummy_installed_file"
    general.download_dir = "dummy_download_dir"
    general.proxy = None
    return general, DUMMY_REPO_CONFIG


def dummy_load_yaml_config_empty(config: str) -> tuple[DummyGeneral, dict]:
    # Do nothing for testing.
    general: Any = DummyGeneral()
    general.installed_file = "dummy_installed_file"
    general.proxy = None
    return general, {}


def dummy_load_installed_empty(installed_file: str) -> dict[Any, Any]:
    return {}


def dummy_show_installed(installed: dict[Any, Any], repositories: dict) -> int:
    return DUMMY_SHOW_RETURN


def dummy_uninstall(repositories: dict, installed: dict[Any, Any], dry_run: bool) -> dict:
    return defaultdict(int)


def dummy_uninstall_all(
    installed_file: Path, installed: dict[Any, Any], repositories: dict, dry_run: bool = False
) -> int:
    installed.clear()
    return 0


def dummy_process_repositories(
    repositories: dict, general: Any, installed: dict[Any, Any], reinstall: bool, dry_run: bool
) -> tuple[dict[str, dict], dict]:
    for repo in repositories:
        installed[repo] = {"processed": True}
    return installed, defaultdict(int)


def dummy_process_repositories_no_installed(
    repositories: dict, general: Any, installed: dict[Any, Any], reinstall: bool, dry_run: bool
) -> tuple[dict[str, dict], dict]:
    return {}, {}


def dummy_save_installed(installed_file: str, installed: dict[Any, Any]) -> int:
    return 0


# --- Test class for girsh.main() ---


class TestMain(unittest.TestCase):
    def setUp(self) -> None:
        # Disable loguru logger output.
        from loguru import logger

        logger.remove()

        self.dummy_general_config: Any = DummyGeneral()
        self.dummy_general_config.installed_file = "dummy_installed_file"
        # Use a temporary directory for downloads.
        self.dummy_general_config.download_dir = Path(tempfile.gettempdir()) / "dummy_download_dir"
        self.dummy_general_config.download_dir.mkdir(exist_ok=True)
        # Create a dummy repository configuration.
        self.dummy_repositories_config = {"dummy_repo": "dummy_repo_config"}
        # Create a temporary directory to simulate file operations if needed.

        self.temp_dir: Path = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        # Clean up temporary directory.
        if self.temp_dir.exists():
            with contextlib.suppress(Exception):
                self.temp_dir.rmdir()

    def test_elevate_privileges(self) -> None:
        dummy_args = DummyArgs(system=True)
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.elevate_privileges", side_effect=dummy_elevate_privileges),
            patch("sys.exit", side_effect=SystemExit) as mock_exit,
        ):
            with self.assertRaises(SystemExit):
                girsh.main()
            mock_exit.assert_called_once_with(DUMMY_ELEVATED_EXIT)

    def test_edit_branch(self) -> None:
        dummy_args = DummyArgs(edit=True, config="config.yaml")
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.edit_config", side_effect=dummy_edit_config) as mock_edit,
        ):
            ret: int = girsh.main()
            self.assertEqual(ret, DUMMY_EDIT_RETURN)
            mock_edit.assert_called_once_with("config.yaml")

    def test_clean_branch(self) -> None:
        dummy_args = DummyArgs(clean=True, config="config.yaml")
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.load_yaml_config", side_effect=dummy_load_yaml_config),
            patch("girsh.girsh.clean_downloads_folder", side_effect=dummy_clean_downloads_folder) as mock_clean,
        ):
            ret: int = girsh.main()
            self.assertEqual(ret, 0)
            mock_clean.assert_called_once()

    def test_verbose_default_branch(self) -> None:
        dummy_args = DummyArgs(verbose=True, config="config.yaml", reinstall=False, dry_run=False)
        dummy_installed_file: str = "dummy_installed_file"

        repositories = {"repo1": "config1", "repo2": "config2"}
        dummy_installed: dict[Any, Any] = repositories
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.load_yaml_config", side_effect=dummy_load_yaml_config) as _mock_load_yaml,
            patch("girsh.girsh.load_installed", side_effect=dummy_load_installed_empty) as _mock_load_installed,
            patch("girsh.girsh.process_repositories", side_effect=dummy_process_repositories) as _mock_process,
            patch("girsh.girsh.save_installed", side_effect=dummy_save_installed) as mock_save_installed,
            patch("girsh.girsh.logger.add", lambda *args, **kwargs: None),
            patch("girsh.girsh.logger.debug", lambda *args, **kwargs: None),
        ):
            ret: int = girsh.main()
        self.assertEqual(ret, 0)
        for repo in repositories:
            self.assertIn(repo, dummy_installed)
        mock_save_installed.assert_called_once_with(
            dummy_installed_file, {"repo1": {"processed": True}, "repo2": {"processed": True}}
        )

    def test_process_repositories_none_installed(self) -> None:
        dummy_args = DummyArgs(show=False, config="config.yaml")
        dummy_installed_data: dict[Any, Any] = {"a": {"path": "/path", "binary": "bin"}}
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.load_yaml_config", side_effect=dummy_load_yaml_config),
            patch("girsh.girsh.load_installed", return_value=(dummy_installed_data)),
            patch("girsh.girsh.uninstall", side_effect=dummy_uninstall),
            patch("girsh.girsh.show_installed", side_effect=dummy_show_installed),
            patch(
                "girsh.girsh.process_repositories", side_effect=dummy_process_repositories_no_installed
            ) as mock_process_repositories,
        ):
            ret: int = girsh.main()
            self.assertEqual(ret, 3)
            mock_process_repositories.assert_called()

    def test_show_installed(self) -> None:
        dummy_args = DummyArgs(show=True, config="config.yaml")
        dummy_installed_data: dict[Any, Any] = {"a": 1}
        # dummy_repositories: dict = {}
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.load_yaml_config", side_effect=dummy_load_yaml_config),
            patch("girsh.girsh.load_installed", return_value=(dummy_installed_data)),
            patch("girsh.girsh.show_installed", side_effect=dummy_show_installed) as mock_show,
            patch("girsh.girsh.os.putenv") as mock_putenv,
        ):
            ret: int = girsh.main()
            self.assertEqual(ret, DUMMY_SHOW_RETURN)
            mock_show.assert_called_once_with(dummy_installed_data, DUMMY_REPO_CONFIG)
            mock_putenv.assert_not_called()

    def test_uninstall_branch(self) -> None:
        dummy_args = DummyArgs(uninstall=True, dry_run=True, config="config.yaml")
        dummy_installed: dict[Any, Any] = {"a": 1}
        dummy_repositories: dict = {}
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.load_yaml_config", side_effect=dummy_load_yaml_config_empty),
            patch("girsh.girsh.load_installed", return_value=(dummy_installed)),
            patch("girsh.girsh.uninstall", side_effect=dummy_uninstall) as mock_uninstall,
            patch("girsh.girsh.save_installed", side_effect=dummy_save_installed) as mock_save,
        ):
            ret: int = girsh.main()
            self.assertEqual(ret, 0)
            mock_uninstall.assert_called_once_with(
                repositories=list(dummy_repositories), installed=dummy_installed, dry_run=True
            )
            mock_save.assert_called_once_with("dummy_installed_file", dummy_installed)

    def test_uninstall_all_installed(self) -> None:
        dummy_args = DummyArgs(uninstall_all=True, dry_run=True, config="config.yaml")
        dummy_installed: dict[Any, Any] = {}
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.load_yaml_config", side_effect=dummy_load_yaml_config),
            patch("girsh.girsh.load_installed", return_value=(dummy_installed)),
            patch("girsh.girsh.uninstall") as mock_uninstall,
            patch("girsh.girsh.save_installed", side_effect=dummy_save_installed) as mock_save,
            patch("girsh.girsh.show_installed") as mock_show,
        ):
            ret: int = girsh.main()
            # If installed is empty, uninstall_all branch should not be called.
            self.assertEqual(ret, 0)
            mock_uninstall.assert_called_with(repositories=[], installed={}, dry_run=True)
            mock_show.assert_not_called()
            mock_save.assert_called_once_with("dummy_installed_file", dummy_installed)

    def test_uninstall_all_nonempty_installed(self) -> None:
        dummy_args = DummyArgs(uninstall_all=True, dry_run=False, config="config.yaml")
        dummy_installed: dict[Any, Any] = {"repo": {"tag": "v1"}}
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.load_yaml_config", side_effect=dummy_load_yaml_config_empty),
            patch("girsh.girsh.load_installed", return_value=(dummy_installed)),
            patch("girsh.girsh.uninstall") as mock_uninstall,
            patch("girsh.girsh.save_installed", side_effect=dummy_save_installed) as mock_save,
        ):
            ret: int = girsh.main()
            self.assertEqual(ret, 0)
            mock_uninstall.assert_called_once_with(repositories=[], installed={"repo": {"tag": "v1"}}, dry_run=False)
            mock_save.assert_called_once_with("dummy_installed_file", dummy_installed)

    def test_default_branch_no_repositories(self) -> None:
        dummy_args = DummyArgs(config="config.yaml")

        dummy_installed: dict[Any, Any] = {}
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.load_yaml_config", side_effect=dummy_load_yaml_config_empty),
            patch("girsh.girsh.load_installed", return_value=(dummy_installed)),
            patch("girsh.girsh.save_installed", side_effect=dummy_save_installed) as mock_save,
        ):
            ret: int = girsh.main()
            self.assertEqual(ret, 0)
            mock_save.assert_called()

    def test_proxy_argument(self) -> None:
        """Test that CLI proxy argument overrides config file and sets both HTTP and HTTPS."""
        dummy_args = DummyArgs(config="config.yaml", proxy="http://proxy.example.com:8080")
        # Proxy in yaml config is expected to be overwritten by CLI argument
        general, repos = dummy_load_yaml_config("config.yaml")
        general.proxy = "http://proxy.yaml.com:8080"  # type: ignore[attr-defined]
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.load_yaml_config", return_value=(general, repos)),
            patch.dict("os.environ", {}, clear=False),
            patch("girsh.girsh.process_repositories", return_value=(None, {})),
            patch("girsh.girsh.load_installed", return_value={}),
            patch("girsh.girsh.save_installed"),
        ):
            import os

            girsh.main()
            # CLI argument should override config file proxy
            assert os.environ.get("https_proxy") == "http://proxy.example.com:8080"
            assert os.environ.get("http_proxy") == "http://proxy.example.com:8080"

    def test_proxy_config_yaml(self) -> None:
        """Test that config file proxy is used when CLI argument not provided."""
        dummy_args = DummyArgs(config="config.yaml")
        general, repos = dummy_load_yaml_config("config.yaml")
        general.proxy = "http://proxy.yaml.com:8080"  # type: ignore[attr-defined]
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.load_yaml_config", return_value=(general, repos)),
            patch.dict("os.environ", {}, clear=False),
            patch("girsh.girsh.process_repositories", return_value=(None, {})),
            patch("girsh.girsh.load_installed", return_value={}),
            patch("girsh.girsh.save_installed"),
        ):
            import os

            girsh.main()
            # Config file proxy should be used
            assert os.environ.get("https_proxy") == "http://proxy.yaml.com:8080"
            assert os.environ.get("http_proxy") == "http://proxy.yaml.com:8080"


class ProxyValidationTest(unittest.TestCase):
    """Test proxy URL validation function."""

    def test_valid_proxy_http(self) -> None:
        """Test valid HTTP proxy URL."""
        from girsh.core.config import validate_proxy_url

        result = validate_proxy_url("http://proxy.example.com:8080")
        self.assertEqual(result, "http://proxy.example.com:8080")

    def test_valid_proxy_https(self) -> None:
        """Test valid HTTPS proxy URL."""
        from girsh.core.config import validate_proxy_url

        result = validate_proxy_url("https://proxy.example.com:8080")
        self.assertEqual(result, "https://proxy.example.com:8080")

    def test_valid_proxy_uppercase_scheme(self) -> None:
        """Test proxy with uppercase scheme (case-insensitive)."""
        from girsh.core.config import validate_proxy_url

        result = validate_proxy_url("HTTP://proxy.example.com:8080")
        self.assertEqual(result, "HTTP://proxy.example.com:8080")

    def test_valid_proxy_with_auth(self) -> None:
        """Test proxy with username and password."""
        from girsh.core.config import validate_proxy_url

        result = validate_proxy_url("http://user:pass@proxy.example.com:3128")
        self.assertEqual(result, "http://user:pass@proxy.example.com:3128")

    def test_valid_proxy_no_scheme(self) -> None:
        """Test proxy without scheme defaults to http://."""
        from girsh.core.config import validate_proxy_url

        result = validate_proxy_url("proxy.example.com:8080")
        self.assertEqual(result, "http://proxy.example.com:8080")

    def test_invalid_proxy_empty_string(self) -> None:
        """Test empty proxy string raises ValueError."""
        from girsh.core.config import validate_proxy_url

        with self.assertRaises(ValueError) as context:
            validate_proxy_url("")
        self.assertIn("empty", str(context.exception).lower())

    def test_invalid_proxy_unsupported_scheme(self) -> None:
        """Test unsupported proxy scheme raises ValueError."""
        from girsh.core.config import validate_proxy_url

        with self.assertRaises(ValueError) as context:
            validate_proxy_url("ftp://proxy.example.com:8080")
        self.assertIn("unsupported", str(context.exception).lower())

    def test_invalid_proxy_socks_not_supported(self) -> None:
        """Test that SOCKS proxies are not supported."""
        from girsh.core.config import validate_proxy_url

        # SOCKS4 should be rejected
        with self.assertRaises(ValueError) as context:
            validate_proxy_url("socks4://proxy.example.com:1080")
        self.assertIn("unsupported", str(context.exception).lower())

        # SOCKS5 should be rejected
        with self.assertRaises(ValueError) as context:
            validate_proxy_url("socks5://proxy.example.com:1080")
        self.assertIn("unsupported", str(context.exception).lower())

    def test_invalid_proxy_no_host(self) -> None:
        """Test proxy URL without host raises ValueError."""
        from girsh.core.config import validate_proxy_url

        with self.assertRaises(ValueError) as context:
            validate_proxy_url("http://")
        self.assertIn("hostname", str(context.exception).lower())

    def test_invalid_proxy_port_zero(self) -> None:
        """Test port zero raises ValueError."""
        from girsh.core.config import validate_proxy_url

        with self.assertRaises(ValueError) as context:
            validate_proxy_url("http://proxy.example.com:0")
        self.assertIn("port", str(context.exception).lower())

    def test_invalid_proxy_port_out_of_range(self) -> None:
        """Test port out of range raises ValueError."""
        from girsh.core.config import validate_proxy_url

        with self.assertRaises(ValueError) as context:
            validate_proxy_url("http://proxy.example.com:99999")
        self.assertIn("port", str(context.exception).lower())

    def test_invalid_proxy_non_numeric_port(self) -> None:
        """Test non-numeric port raises ValueError."""
        from girsh.core.config import validate_proxy_url

        with self.assertRaises(ValueError) as context:
            validate_proxy_url("http://proxy.example.com:abc")
        self.assertIn("port", str(context.exception).lower())

    def test_general_config_proxy_validation(self) -> None:
        """Test that General config validates proxy on assignment."""
        from girsh.core.config import General

        config = General()
        # Valid proxy should be accepted
        config.proxy = "http://proxy.example.com:8080"
        self.assertEqual(config.proxy, "http://proxy.example.com:8080")

        # Invalid proxy should raise ValueError
        with self.assertRaises(ValueError):
            config.proxy = "ftp://invalid:scheme"


class ProxyTestingTest(unittest.TestCase):
    """Test proxy testing/validation command."""

    def test_test_proxy_command_no_proxy_configured(self) -> None:
        """Test --test-proxy command with no proxy configured."""
        dummy_args = DummyArgs(config="config.yaml", test_proxy=True)
        general, repos = dummy_load_yaml_config("config.yaml")
        general.proxy = None  # type: ignore[attr-defined]
        with (
            patch("girsh.girsh.get_arguments", return_value=dummy_args),
            patch("girsh.girsh.load_yaml_config", return_value=(general, repos)),
            patch("girsh.girsh.logger") as mock_logger,
        ):
            ret: int | None = girsh.main()
            self.assertEqual(ret, 1)
            mock_logger.error.assert_called_once()

    @patch("girsh.core.utils.requests.head")
    def test_test_proxy_command_successful(self, mock_head: unittest.mock.Mock) -> None:
        """Test --test-proxy command with successful proxy."""
        from girsh.core.utils import test_proxy

        mock_response = unittest.mock.Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        result = test_proxy("http://proxy.example.com:8080")
        self.assertTrue(result)
        mock_head.assert_called_once()

    @patch("girsh.core.utils.requests.head")
    def test_test_proxy_command_proxy_error(self, mock_head: unittest.mock.Mock) -> None:
        """Test --test-proxy command with proxy error."""
        import requests.exceptions

        from girsh.core.utils import test_proxy

        mock_head.side_effect = requests.exceptions.ProxyError("Proxy connection failed")

        result = test_proxy("http://proxy.example.com:8080")
        self.assertFalse(result)

    @patch("girsh.core.utils.requests.head")
    def test_test_proxy_command_timeout(self, mock_head: unittest.mock.Mock) -> None:
        """Test --test-proxy command with timeout."""
        import requests.exceptions

        from girsh.core.utils import test_proxy

        mock_head.side_effect = requests.exceptions.ConnectTimeout("Connection timeout")

        result = test_proxy("http://proxy.example.com:8080")
        self.assertFalse(result)


class ElevatePrivilegesTest(unittest.TestCase):
    @patch("os.geteuid", return_value=0)
    def test_elevate_privileges_already_root(self, mock_geteuid: unittest.mock.Mock) -> None:
        with patch("builtins.print") as mock_print, patch("os.execvp") as mock_execvp:
            girsh.elevate_privileges()
            mock_print.assert_not_called()
            mock_execvp.assert_not_called()

    @patch("os.geteuid", return_value=1000)
    def test_elevate_privileges_not_root(self, mock_geteuid: unittest.mock.Mock) -> None:
        with patch("builtins.print") as mock_print, patch("os.execvp") as mock_execvp:
            girsh.elevate_privileges()
            mock_print.assert_called_once_with("Re-running with elevated privileges...")
            command = ["sudo", sys.executable, *sys.argv]
            mock_execvp.assert_called_once_with("/usr/bin/sudo", command)


class ShowSummaryTest(unittest.TestCase):
    @patch("girsh.girsh.logger")
    def test_show_summary_with_data(self, mock_logger: unittest.mock.Mock) -> None:
        install_summary = {DummyRepoResult.result1: 3, DummyRepoResult.result2: 1}
        uninstall_summary = {DummyRepoResult.fail1: 2, DummyRepoResult.fail2: 1}

        girsh.show_summary(install_summary, uninstall_summary)  # ty: ignore[invalid-argument-type]

        mock_logger.success.assert_any_call("===============================")
        mock_logger.success.assert_any_call("Summary:")
        mock_logger.success.assert_any_call("  result1: 3")
        mock_logger.success.assert_any_call("  result2: 1")
        mock_logger.success.assert_any_call("  fail1: 2")
        mock_logger.success.assert_any_call("  fail2: 1")

    @patch("girsh.girsh.logger")
    def test_show_summary_empty(self, mock_logger: unittest.mock.Mock) -> None:
        install_summary: dict = {}
        uninstall_summary: dict = {}

        girsh.show_summary(install_summary, uninstall_summary)

        mock_logger.success.assert_any_call("===============================")
        mock_logger.success.assert_any_call("Summary:")


if __name__ == "__main__":
    unittest.main()
