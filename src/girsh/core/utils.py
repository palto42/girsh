import shlex
import subprocess

import psutil
from loguru import logger


def confirm_default_no(question: str | None) -> bool:
    """
    Prompts the user with a yes/no question and returns True if the user explicitly answers "y" (yes).
    Args:
        question (str): The question to display to the user.
    Returns:
        bool: True if the user answers "y", otherwise False.
    """
    answer = input(f"{question if question else 'Confirm?'} (y/N): ").strip().lower()
    return answer == "y"


def confirm_default_yes(question: str | None) -> bool:
    """
    Prompts the user with a yes/no question and returns True if the user doesn't explicitly answers "n" (no).
    Args:
        question (str): The question to display to the user.
    Returns:
        bool: True if the user doesn't answers "n", otherwise False.
    """
    answer = input(f"{question if question else 'Confirm?'} (Y/n): ").strip().lower()
    return answer != "n"


def get_processes(program_name: str) -> list[psutil.Process]:
    """Search for matches in the process name

    Args:
        program_name (str): Name of the program

    Returns:
        list[int]: List of processes
    """
    return [proc for proc in psutil.process_iter(["pid", "name", "username"]) if proc.info["name"] == program_name]


def stop_processes(program_name: str | None) -> bool:
    """
    Terminate all running processes for of given program

    Args:
        program_name (str): Name of the program

    Returns:
        bool: True if all processes have been terminated.
    """
    if program_name is None:
        logger.error("To stop a process, the program name must be specified!")
        return False
    processes = get_processes(program_name)
    if not processes:
        return True
    if not confirm_default_no(f"Terminate all running processes of '{program_name}'?"):
        logger.warning(f"Can't install or update {program_name} due to running processes.")
        return False
    for process in processes:
        process.terminate()
    # Check if all have been stopped
    processes = get_processes(program_name)
    if not processes:
        logger.warning(f"Successfully stopped all processes of {program_name}")
        return True
    logger.warning(f"Failed to stop all running processes of {program_name}")
    logger.debug(f"Failed to terminate processes: {[proc.info for proc in processes]}")
    if not confirm_default_no(f"Kill all running processes of '{program_name}'?"):
        logger.warning(f"Can't install or update {program_name} due to running processes.")
        return False
    for process in processes:
        process.kill()
    processes = get_processes(program_name)
    if not processes:
        logger.info(f"Successfully killed all running processes of {program_name}")
        return True
    logger.error(f"Failed to kill processes: {[proc.info for proc in processes]}")
    return False


def run_macro(command: str) -> bool:
    """
    Executes a command macro if it is found in the command string.
    The command macros are defined in the `command_macros` dictionary.

    Args:
        command (str): The command string.

    Returns:
        bool | None: True if macro was found and successfully executed,
                     False if macro was not found or failed.
    """
    command_macros = {
        r"%confirm_default_yes%": confirm_default_yes,
        r"%confirm_default_no%": confirm_default_no,
        r"%stop_processes%": stop_processes,
    }
    if " " in command:
        macro, macro_args = command.split(" ", 1)
    else:
        macro = command
        macro_args = None

    if macro in command_macros:
        logger.debug(f"Run macro: {macro}")
        return command_macros[macro](macro_args)

    logger.error(f"Unknown command macro: {macro}")
    return False


def run_commands(command_list: list[str | None] | None, info: str) -> bool:
    """
    Executes a list of shell commands and logs their output.

    Args:
        command_list (list[str|None] | None): A list of shell commands to execute. If None, no commands are run.
        info (str): A descriptive string used for logging purposes.

    Returns:
        bool: True if all commands execute successfully or if the command list is None.
              False if any command fails.
    """
    # Define dict of command macros
    # The command macro functions must take one optional string argument and return True if successfully executed.
    if command_list:
        logger.info(f"Running commands for {info}")
        for command in command_list:
            if command is None or command.startswith("#"):
                logger.debug(f"Skipping command: {command}")
                continue
            logger.debug(f"Running command: {command}")
            if command.startswith("%"):
                return run_macro(command)
            # Command was no macro, so try to execute it
            if command.startswith("|"):
                fail_on_error = False
                command = command[1:]
            else:  # default is to fail on error
                fail_on_error = True
            try:
                if command.startswith("*"):
                    # If the command starts with "*", it is executed in a shell
                    command = command[1:]
                    cmd_result = subprocess.run(command, shell=True, capture_output=True, text=True)  # noqa: S602
                else:
                    cmd_result = subprocess.run(shlex.split(command), capture_output=True, text=True)  # noqa: S603
            except Exception as e:
                logger.error(f"Command failed: {command}, error: {e}")
                return False

            logger.debug(
                f"Command output: {cmd_result.stdout}, error: {cmd_result.stderr}, error code: {cmd_result.returncode}"
            )
            if fail_on_error and cmd_result.returncode != 0:
                logger.error(f"Commands for {info} failed: {command}, error code: {cmd_result.returncode}")
                logger.error(f"Command error message: {cmd_result.stderr}")
                return False
    return True
