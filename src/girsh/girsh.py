import os
import sys

from loguru import logger

from girsh.core.config import edit_config, get_arguments, load_yaml_config
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
        os.execvp("/usr/bin/sudo", command)  # Replace current process with sudo call  # noqa: S606


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

    if args.edit:
        return edit_config(args.config)

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

    if args.clean:
        return clean_downloads_folder(general.download_dir)

    installed: dict[str, dict] = load_installed(general.installed_file)
    logger.debug(f"Current installed: {installed}")

    if args.show:
        return show_installed(installed, repositories)

    if args.uninstall_all:
        uninstall_summary = uninstall(repositories=[], installed=installed, dry_run=args.dry_run)
    else:
        uninstall_summary = uninstall(
            repositories=list(repositories), installed=installed, dry_run=args.dry_run if args.uninstall else True
        )
    if args.uninstall or args.uninstall_all:
        save_installed(general.installed_file, installed)
        return 1 if RepoResult.uninstall_failed in uninstall_summary else 0

    # Determine binaries to reinstall using a ternary operator
    reinstall_repos = (
        [repo for repo in installed if installed[repo].get("binary") in args.reinstall] if args.reinstall else []
    )

    installed, summary = process_repositories(
        repositories, general, installed, reinstall=reinstall_repos, dry_run=args.dry_run
    )

    show_summary(summary, uninstall_summary)

    if repositories and not installed:
        # Nothing installed
        return 3
    has_errors = summary.get(RepoResult.install_failed, 0) > 0
    # Update the installed with the new version
    return save_installed(general.installed_file, installed) + has_errors


if __name__ == "__main__":
    sys.exit(main())
