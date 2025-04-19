import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from loguru import logger

from girsh.core import utils


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
# Tests for confirm
# -------------------------------
class TestConfirmYesNo(unittest.TestCase):
    def test_confirm_default_no_y(self) -> None:
        responses = ["y", "Y"]
        with patch("builtins.input", side_effect=responses):
            for _ in responses:
                self.assertTrue(utils.confirm_default_no("dummy"))

    def test_confirm_default_no_x(self) -> None:
        responses = ["n", "N", "x", ""]
        with patch("builtins.input", side_effect=responses):
            for _ in responses:
                self.assertFalse(utils.confirm_default_no("dummy"))

    def test_confirm_default_yes_n(self) -> None:
        responses = ["n", "N"]
        with patch("builtins.input", side_effect=responses):
            for _ in responses:
                self.assertFalse(utils.confirm_default_yes("dummy"))

    def test_confirm_default_yes_x(self) -> None:
        responses = ["y", "Y", "x", ""]
        with patch("builtins.input", side_effect=responses):
            for _ in responses:
                self.assertTrue(utils.confirm_default_yes("dummy"))


# -------------------------------
# Dummy classes used for testing
# -------------------------------
class DummyProcess:
    def __init__(self, name: str) -> None:
        self.info: dict[str, Any] = {"name": name, "cmdline": ["dummy", "command"], "pid": 42}

    def terminate(self) -> None:
        return

    def kill(self) -> None:
        return


# -------------------------------
# Tests for get_processes
# -------------------------------
class TestGetProcesses(unittest.TestCase):
    def test_get_processes(self) -> None:
        dummy1 = DummyProcess("my_prog")
        dummy2 = DummyProcess("other")
        with patch("psutil.process_iter", return_value=[dummy1, dummy2]):
            processes: list[DummyProcess] = utils.get_processes("my_prog")  # type: ignore[assignment]
        self.assertEqual(processes, [dummy1])


# -------------------------------
# Tests for stop_processes
# -------------------------------
class TestStopProcesses(unittest.TestCase):
    def setUp(self) -> None:
        # Disable loguru logger output

        logger.remove()

    def test_stop_processes_no_processes(self) -> None:
        with patch("girsh.core.utils.get_processes", return_value=[]):
            result: bool = utils.stop_processes("prog")
        self.assertTrue(result)

    def test_stop_processes_cancel_termination(self) -> None:
        dummy = DummyProcess("prog")
        with patch("girsh.core.utils.get_processes", return_value=[dummy]), patch("builtins.input", return_value="n"):
            result: bool = utils.stop_processes("prog")
        self.assertFalse(result)

    def test_stop_processes_success(self) -> None:
        dummy = DummyProcess("prog")
        with (
            patch("girsh.core.utils.get_processes", side_effect=[[dummy], []]),
            patch("builtins.input", return_value="y"),
        ):
            result: bool = utils.stop_processes("prog")
        self.assertTrue(result)

    def test_stop_processes_fail_then_cancel(self) -> None:
        dummy = DummyProcess("prog")
        with (
            patch("girsh.core.utils.get_processes", side_effect=[[dummy], [dummy]]),
            patch("builtins.input", side_effect=["y", "n"]),
        ):
            result: bool = utils.stop_processes("prog")
        self.assertFalse(result)

    def test_stop_processes_fail_then_kill(self) -> None:
        dummy = DummyProcess("prog")
        with (
            patch("girsh.core.utils.get_processes", side_effect=[[dummy], [dummy], []]),
            patch("builtins.input", side_effect=["y", "y"]),
        ):
            result: bool = utils.stop_processes("prog")
        self.assertTrue(result)

    def test_stop_processes_fail_then_kill_failed(self) -> None:
        dummy = DummyProcess("prog")
        with (
            patch("girsh.core.utils.get_processes", side_effect=[[dummy], [dummy], [dummy]]),
            patch("builtins.input", side_effect=["y", "y"]),
        ):
            result: bool = utils.stop_processes("prog")
        self.assertFalse(result)

    def test_stop_processes_none(self) -> None:
        result: bool = utils.stop_processes(None)
        self.assertFalse(result)


# -------------------------------
# Tests for running commands
# -------------------------------
class TestRunCommands(unittest.TestCase):
    @patch("girsh.core.utils.logger")
    def test_run_commands_success(self, mock_logger: MagicMock) -> None:
        self.assertTrue(utils.run_commands(["echo 'command 1'", "echo 'command 2'"], "test commands"))
        mock_logger.debug.assert_called_with("Command output: command 2\n, error: , error code: 0")

    @patch("girsh.core.utils.logger")
    def test_run_commands_failure(self, mock_logger: MagicMock) -> None:
        self.assertFalse(
            utils.run_commands(["sh -c 'echo failure;echo error >&2;exit 1'", "echo 'command 2'"], "test commands")
        )
        mock_logger.debug.assert_called_with("Command output: failure\n, error: error\n, error code: 1")
        mock_logger.error.assert_called_with("Command error message: error\n")

    @patch("girsh.core.utils.logger")
    @patch("girsh.core.utils.confirm_default_no", return_value=True)
    def test_run_commands_macro_confirm(self, mock_confirm: MagicMock, mock_logger: MagicMock) -> None:
        self.assertTrue(
            utils.run_commands([r"%confirm_default_no% Dummy confirm", "echo 'command 1'"], "test commands")
        )
        mock_confirm.assert_called_once_with("Dummy confirm")
        mock_logger.debug.assert_called_with("Run macro: %confirm_default_no%")

    @patch("girsh.core.utils.logger")
    @patch("subprocess.run")
    @patch("girsh.core.utils.confirm_default_no", return_value=False)
    def test_run_commands_macro_confirm_false(
        self, mock_confirm: MagicMock, mock_run: MagicMock, mock_logger: MagicMock
    ) -> None:
        self.assertFalse(
            utils.run_commands([r"%confirm_default_no% Dummy confirm", "echo 'command 1'"], "test commands")
        )
        mock_confirm.assert_called_once_with("Dummy confirm")
        mock_run.assert_not_called()

    @patch("girsh.core.utils.logger")
    @patch("girsh.core.utils.confirm_default_no", return_value=True)
    def test_run_commands_macro_confirm_no_question(self, mock_confirm: MagicMock, mock_logger: MagicMock) -> None:
        self.assertTrue(utils.run_commands([r"%confirm_default_no%", "echo 'command 1'"], "test commands"))
        mock_confirm.assert_called_once_with(None)
        mock_logger.debug.assert_called_with("Run macro: %confirm_default_no%")

    @patch("girsh.core.utils.logger")
    @patch("subprocess.run")
    @patch("girsh.core.utils.confirm_default_no")
    def test_run_commands_macro_no_close(
        self, mock_confirm: MagicMock, mock_run: MagicMock, mock_logger: MagicMock
    ) -> None:
        self.assertFalse(
            # Try incorrect macro where there is no closing %
            utils.run_commands([r"%confirm_default_no Dummy confirm", "echo 'command 1'"], "test commands")
        )
        mock_confirm.assert_not_called()
        mock_run.assert_not_called()
        mock_logger.error.assert_called_once_with(r"Unknown command macro: %confirm_default_no")

    @patch("girsh.core.utils.logger")
    @patch("subprocess.run")
    def test_run_commands_unknown_macro(self, mock_run: MagicMock, mock_logger: MagicMock) -> None:
        self.assertFalse(
            # Unknown macro
            utils.run_commands([r"%unknown_macro% Dummy confirm", "echo 'command 1'"], "test commands")
        )
        mock_run.assert_not_called()
        mock_logger.error.assert_called_once_with(r"Unknown command macro: %unknown_macro%")

    @patch("girsh.core.utils.logger")
    def test_run_commands_comment(self, mock_logger: MagicMock) -> None:
        self.assertTrue(
            utils.run_commands(
                ["#sh -c 'echo failure;echo error >&2;exit 1'", None, "echo 'command 2'"], "test commands"
            )
        )
        mock_logger.debug.assert_any_call("Skipping command: #sh -c 'echo failure;echo error >&2;exit 1'")
        mock_logger.debug.assert_any_call("Skipping command: None")
        mock_logger.debug.assert_called_with("Command output: command 2\n, error: , error code: 0")
        mock_logger.error.assert_not_called()

    @patch("girsh.core.utils.logger")
    def test_run_commands_suppress_error(self, mock_logger: MagicMock) -> None:
        self.assertTrue(
            utils.run_commands(
                ["|sh -c 'echo failure;echo error >&2;exit 1'", "echo 'command 2'"],
                "test commands",
            )
        )
        mock_logger.debug.assert_any_call("Command output: failure\n, error: error\n, error code: 1")
        mock_logger.debug.assert_called_with("Command output: command 2\n, error: , error code: 0")
        mock_logger.error.assert_not_called()

    @patch("girsh.core.utils.logger")
    @patch("girsh.core.utils.subprocess.run", side_effect=Exception("Test Exception"))
    def test_run_commands_exception(self, mock_run: MagicMock, mock_logger: MagicMock) -> None:
        self.assertFalse(
            utils.run_commands(
                ["faulty_command"],
                "test commands",
            )
        )
        mock_logger.error.assert_called_once_with("Command failed: faulty_command, error: Test Exception")


if __name__ == "__main__":
    unittest.main()
