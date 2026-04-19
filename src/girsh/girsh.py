import argparse
import os
import sys

from loguru import logger

from girsh.core.config import General, edit_config, get_arguments, load_yaml_config
from girsh.core.files import clean_downloads_folder
from girsh.core.installed import load_installed, save_installed, show_installed
from girsh.core.repos import RepoResult, process_repositories, uninstall

GITHUB_API_RELEASES = "https://api.github.com/repos/{repo}/releases"

logger.remove(0)
logger.add(sys.stdout, colorize=True, format="<level>{message}</level>", level="SUCCESS")


def elevate_privileges() -> None:
    """
    Elevate the privileges of the current process to root using sudo.
    If the current process is not running as the root user, this function
    will re-run the script with elevated privileges by invoking sudo.
    Raises:
        OSError: If there is an error executing the sudo command.
    """

    if os.geteuid() != 0:
        print("Re-running with elevated privileges...")
        command = ["sudo", sys.executable, *sys.argv]
        # Replace current process with sudo call
        os.execvp("/usr/bin/sudo", command)  # noqa:  S606


def show_summary(install_summary: dict[RepoResult, int], uninstall_summary: dict[RepoResult, int]) -> None:
    """
    Display a summary of the repository processing results.

    Args:
        install_summary (dict[RepoResult, int]): A dictionary where the keys are
            RepoResult instances and the values are counts of occurrences.
        uninstall_summary (dict[RepoResult, int]): A dictionary where the keys are
            RepoResult instances and the values are counts of occurrences.
    """
    logger.success("===============================")
    logger.success("Summary:")
    for result, count in install_summary.items():
        logger.success(f"  {result.name}: {count}")
    for result, count in uninstall_summary.items():
        logger.success(f"  {result.name}: {count}")


def set_logger_level(verbosity: int) -> None:
    """
    Set the logger level based on the verbosity argument.

    Args:
        verbosity (int): The verbosity level (0-3).
    """
    if verbosity == 0:
        return
    levels = ["INFO", "DEBUG", "TRACE"]
    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format="<level>{message}</level>",
        level=levels[verbosity - 1 if verbosity < 4 else 2],
    )


def handle_early_operations(args: argparse.Namespace) -> int | None:
    """
    Handle operations that can return early without full setup.

    Args:
        args: Parsed command-line arguments

    Returns:
        int | None: Exit code if operation completed, None to continue
    """
    if args.edit:
        return edit_config(args.config)

    if args.clean:
        general, _ = load_yaml_config(args.config)
        return clean_downloads_folder(general.download_dir)

    if args.show:
        general, repositories = load_yaml_config(args.config)
        installed = load_installed(general.installed_file)
        return show_installed(installed, repositories)

    if args.test_proxy:
        general, _ = load_yaml_config(args.config)
        if args.proxy:
            general.proxy = args.proxy

        if general.proxy:
            from girsh.core.utils import test_proxy

            success = test_proxy(general.proxy)
            return 0 if success else 1
        else:
            logger.error("No proxy configured. Use -p/--proxy or set proxy in config file.")
            return 1

    return None


def setup_configuration(args: argparse.Namespace) -> tuple[General, dict]:
    """
    Load and setup configuration with proxy and logging.

    Args:
        args: Parsed command-line arguments

    Returns:
        tuple[object, dict]: General config and repositories config
    """
    set_logger_level(args.verbose)
    logger.debug(f"CLI args: {args}")

    general, repositories = load_yaml_config(args.config)
    if args.proxy:
        general.proxy = args.proxy

    logger.debug(f"General config: {general}")
    logger.debug(f"Repositories config: {repositories}")

    if general.proxy:
        logger.debug(f"Using proxy: {general.proxy}")
        os.environ["https_proxy"] = general.proxy
        os.environ["http_proxy"] = general.proxy

    return general, repositories


def handle_uninstall_operations(
    args: argparse.Namespace, general: General, repositories: dict, installed: dict[str, dict]
) -> tuple[int | None, dict]:
    """
    Handle uninstall and uninstall_all operations.

    Args:
        args: Parsed command-line arguments
        general: General configuration
        repositories: Repository configurations
        installed: Currently installed packages

    Returns:
        tuple[int | None, dict]: Exit code if uninstall operation completed (or None to continue), and uninstall summary
    """
    if not (args.uninstall or args.uninstall_all):
        return None, {}

    if args.uninstall_all:
        uninstall_summary = uninstall(repositories=[], installed=installed, dry_run=args.dry_run)
    else:
        uninstall_summary = uninstall(
            repositories=list(repositories),
            installed=installed,
            dry_run=args.dry_run if args.uninstall else True,
        )

    save_installed(general.installed_file, installed)
    exit_code = 1 if RepoResult.uninstall_failed in uninstall_summary else 0
    return exit_code, uninstall_summary


def handle_installation(
    args: argparse.Namespace, general: General, repositories: dict, installed: dict[str, dict]
) -> tuple[dict[str, dict], dict]:
    """
    Handle repository installation and processing.

    Args:
        args: Parsed command-line arguments
        general: General configuration
        repositories: Repository configurations
        installed: Currently installed packages

    Returns:
        tuple[dict[str, dict], dict]: Updated installed dict and processing summary
    """
    # Determine binaries to reinstall
    reinstall_repos = (
        [repo for repo in installed if installed[repo].get("binary") in args.reinstall] if args.reinstall else []
    )

    installed, summary = process_repositories(
        repositories,
        general,
        installed,
        reinstall=reinstall_repos,
        dry_run=args.dry_run,
    )

    return installed, summary


def determine_exit_code(
    general: General, repositories: dict, installed: dict[str, dict], summary: dict, uninstall_summary: dict
) -> int:
    """
    Determine the final exit code based on operation results.

    Args:
        general: General configuration
        repositories: Repository configurations
        installed: Currently installed packages
        summary: Installation summary
        uninstall_summary: Uninstall summary

    Returns:
        int: Exit code
    """
    show_summary(summary, uninstall_summary)

    if repositories and not installed:
        # Nothing installed
        return 3

    has_errors = summary.get(RepoResult.install_failed, 0) > 0
    # Update the installed with the new version
    return save_installed(general.installed_file, installed) + has_errors


def main() -> int:
    """
    The main entry point for the application.

    This function processes command-line arguments, manages configurations,
    and orchestrates the execution of various operations such as editing
    configurations, cleaning the downloads folder, showing installed items,
    uninstalling repositories, and processing repositories for installation.

    Returns:
        int: Exit code indicating the result of the operation.
             - 0: Success
             - 1: Uninstall operation failed
             - 3: No repositories installed
             - Other non-zero values indicate errors or specific conditions
    """

    args = get_arguments()

    if args.system:
        elevate_privileges()

    # Handle operations that can return early
    early_result = handle_early_operations(args)
    if early_result is not None:
        return early_result

    # Setup configuration and logging
    general, repositories = setup_configuration(args)

    # Load installed packages
    installed = load_installed(general.installed_file)
    logger.debug(f"Current installed: {installed}")

    # Handle uninstall operations
    uninstall_result, uninstall_summary = handle_uninstall_operations(args, general, repositories, installed)
    if uninstall_result is not None:
        return uninstall_result

    # Handle installation
    installed, summary = handle_installation(args, general, repositories, installed)

    # Determine final exit code
    return determine_exit_code(general, repositories, installed, summary, uninstall_summary)


if __name__ == "__main__":
    sys.exit(main())
