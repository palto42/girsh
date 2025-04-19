import shutil
from collections import defaultdict
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

import requests
from loguru import logger

from girsh.core import utils
from girsh.core.files import (
    copy_to_bin,
    download_github_release,
    extract_package,
    find_binary,
    move_to_packages,
)


class RepoResult(Enum):
    # Installation status changed
    installed = 1
    uninstalled = 2
    updated = 3
    # No change requested
    skipped = 11
    dry_run_install = 12
    dry_run_uninstall = 13
    cancelled = 14
    # Installation or update failed
    update_failed = 91
    install_failed = 92
    uninstall_failed = 93
    pre_commands_failed = 94
    post_commands_failed = 95
    exception = 99


class GeneralConfig(Protocol):
    download_dir: Path
    package_base_folder: Path
    bin_base_folder: Path
    package_pattern: str


class RepositoryConfig(Protocol):
    comment: str
    version: str | None
    package_pattern: str | None
    download_url: str | None
    filter_pattern: str | None
    binary_name: str | None
    multi_file: bool
    pre_update_commands: list[str | None] | None
    post_update_commands: list[str | None] | None


def fetch_release_info(repo: str, version: str | None, reinstall: bool) -> dict[Any, Any] | None:
    """
    Fetch the release information for a given repository from GitHub.

    Args:
        repo (str): The repository identifier, in the format 'owner/repo'.
        version (str | None): The repository version
        reinstall (bool): A flag to force reinstall even if no new version is detected.

    Returns:
        dict | None: The release information in JSON format, or None if an error occurs.
    """
    releases_url = (
        f"https://api.github.com/repos/{repo}/releases/latest"
        if version is None
        else f"https://api.github.com/repos/{repo}/releases/tags/{version}"
    )
    logger.debug(f"Get release info from {releases_url}")
    try:
        response = requests.get(
            releases_url,
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10,
        )
        response.raise_for_status()
        release_info = response.json()
        if isinstance(release_info, dict):
            return release_info
        else:
            logger.error(f"Received unexpected release info data: {release_info}")
    except requests.RequestException as e:
        logger.error(f"Error fetching release info for {repo}: {e}")
    return None


def is_new_version(installed_tag: str | None, tag: str, reinstall: bool) -> RepoResult:
    """
    Determine if the current version is different from the installed version or if a reinstall is forced.

    Args:
        installed_tag (str | None): The installed version of the repository.
        tag (str): The new version's tag name from the release info.
        reinstall (bool): A flag to force reinstall even if no new version is detected.

    Returns:
        RepoResult: Target action based on version info and reinstall flag
    """
    if installed_tag is None or reinstall:
        return RepoResult.installed
    elif installed_tag != tag:
        return RepoResult.updated
    return RepoResult.skipped


def check_repo_release(
    repo: str, target_version: str | None, current_version: str | None, reinstall: bool
) -> tuple[RepoResult, dict[Any, Any]]:
    """
    Check the release information of a repository and determine the appropriate action.

    This function fetches release information for a given repository from GitHub,
    checks if a new version is available, and determines whether to skip, reinstall,
    or proceed with the release.

    Args:
        repo (str): The name of the repository to check.
        target_version (str | None): The target version to check for. If None, the latest version is used.
        current_version (str | None): The currently installed version. If None, it assumes no version is installed.
        reinstall (bool): Whether to force reinstallation even if the current version matches the target version.

    Returns:
        RepoResult | dict[Any, Any]:
            - A dictionary containing release information if a new version is available or reinstall is forced.
            - A RepoResult enum value indicating the action taken (e.g., skipped or install_failed).
    """
    # Fetch the release information from GitHub
    release_info = fetch_release_info(repo, target_version, reinstall)
    logger.debug(
        f"Received release info url: {release_info.get('url') if isinstance(release_info, dict) else release_info}"
    )
    if not isinstance(release_info, dict):
        logger.error("No valid release info received")
        return RepoResult.install_failed, {}

    # Get the tag of the latest release
    tag = release_info.get("tag_name", "unknown")

    # Check if a new version is available or if reinstall is forced
    action = is_new_version(current_version, tag, reinstall)
    if action == RepoResult.skipped:
        logger.info(f"{repo}: No newer version than {tag} found, skipping.")
        return RepoResult.skipped, {}
    return action, release_info


def process_repository(
    repo: str,
    repo_config: RepositoryConfig,
    general: GeneralConfig,
    installed_tag: str | None,
    reinstall: bool = False,
    dry_run: bool = False,
) -> tuple[RepoResult, dict[str, str]]:
    """
    Process a single repository by checking for updates, downloading the latest release, extracting,
    optionally renaming the binary, and installing it. Updates the installed with the latest version
    information if a new version is installed.

    Args:
        repo (str): The repository identifier, in the format 'owner/repo'.
        repo_config (RepositoryConfig): The repository configuration, containing version info and other settings.
        general (GeneralConfig): General configuration settings.
        installed_tag (str | None): Tag of installed version.
        reinstall (bool): A flag to force reinstall even if the current version is up-to-date (default: False).
        dry_run (bool): A flag to simulate the process without installing the binary (default: False).

    Returns:
        tuple[RepoResult, dict[str, str]]: Result of repo installation, Repo installation data
    """
    logger.info(f"Processing '{repo}': {repo_config.comment}")

    action, release_info = check_repo_release(
        repo=repo,
        target_version=repo_config.version,
        current_version=installed_tag,
        reinstall=reinstall,
    )
    if not release_info:
        return action, {}
    tag = release_info.get("tag_name", "unknown")

    # Download the release package
    result = download_github_release(
        "",
        repo_config.package_pattern if repo_config.package_pattern is not None else general.package_pattern,
        general.download_dir,
        release_info=release_info,
        download_url=repo_config.download_url,
    )
    if not result:
        return RepoResult.install_failed, {}

    package_path, downloaded_tag = result
    repo_name = repo.split("/")[1]

    # Extract the package contents
    extract_dir = general.download_dir / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    extract_package(file_path=package_path, extract_to=extract_dir, package_name=repo_name)

    # Find the binary based on the configuration
    binary_path = find_binary(extract_dir, repo_config.filter_pattern)
    if not binary_path:
        return RepoResult.install_failed, {}

    # Dry-run mode: Only check for updates without installing
    if dry_run:
        logger.info(f"Dry-run: Found {repo} version {tag}, extracted binary {binary_path}, skipping installation.")
        return RepoResult.dry_run_install, {}

    # Run pre-update commands
    if not utils.run_commands(repo_config.pre_update_commands, "repo: pre-update"):
        return RepoResult.pre_commands_failed, {}

    # Install the binary to the specified bin directory
    if repo_config.multi_file:
        install_path = move_to_packages(
            package_source=extract_dir / repo_name,
            package_base_folder=general.package_base_folder,
            bin_base_folder=general.bin_base_folder,
            binary_path=binary_path,
            binary_name=repo_config.binary_name,
        )
    else:
        install_path = copy_to_bin(
            binary_path=binary_path, bin_base_folder=general.bin_base_folder, binary_name=repo_config.binary_name
        )
    logger.info(f"{repo}: Installed {install_path.name} version {tag} to {install_path.parent}")

    # Clean up the extracted directory after installation
    shutil.rmtree(extract_dir)

    # Update the installed with the new version and binary information
    install_data = {
        "tag": tag,
        "binary": str(install_path.name),
        "path": str(install_path.parent),
        "pre_update_commands": repo_config.pre_update_commands,
    }
    if repo_config.multi_file:
        install_data["package_path"] = str(general.package_base_folder / repo_name)

    # Run post-update commands
    if not utils.run_commands(repo_config.post_update_commands, "repo: post-update"):
        return RepoResult.post_commands_failed, install_data

    return action, install_data


def process_repositories(
    repositories: Mapping[str, RepositoryConfig],
    general: GeneralConfig,
    installed: dict[str, dict],
    reinstall: list[str],
    dry_run: bool = False,
) -> tuple[dict[str, dict], dict[RepoResult, int]]:
    """
    Processes a list of repositories, installs or updates them if necessary,
    and saves the updated installation data.

    Parameters:
        repositories (Mapping[str, RepositoryConfig]): A dictionary of repository names and their corresponding Repository objects.
        general (GeneralConfig): General configuration settings.
        installed (dict[str, dict]): A dictionary containing the current installation data of the repositories.
        reinstall (list[str]): List of repositories to reinstall.
        dry_run (bool, optional): A flag to perform a dry run (no changes are actually made). Defaults to False.

    Returns:
        dict[str, dict] | None: Updated install data or None
        dict[RepoResult, int]: Summary of the installation process
    Logs:
    - Warnings and errors related to repository processing.
    - A summary of the installation or update process, including the number of repositories processed for each result type.
    """
    if not repositories:
        logger.warning("No repositories defined in config")
        return installed, {}
    # Ensure that the download folder exists
    try:
        general.download_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.error(f"Permission denied when creating download folder '{general.download_dir}'")
        return installed, {RepoResult.exception: 1}

    summary: dict[RepoResult, int] = defaultdict(int)
    for repo, repo_config in repositories.items():
        if reinstall and repo not in reinstall:
            logger.debug(f"Skipping {repo} as it is not in the reinstall list")
            continue
        current_version = installed.get(repo, {}).get("tag")
        result, install_data = process_repository(
            repo, repo_config, general, current_version, reinstall=repo in reinstall, dry_run=dry_run
        )
        summary[result] += 1
        if result == RepoResult.updated:
            logger.success(f"{repo} updated from {current_version} to {install_data.get('tag')}")
        elif result == RepoResult.installed:
            logger.success(f"{repo} installed version {install_data.get('tag')}")
        else:
            logger.success(f"{repo}: {result.name}")
        if install_data:
            installed[repo] = install_data

    return installed, summary


def remove_binary(repo: str, info: dict[Any, Any], dry_run: bool) -> None:
    """
    Remove the binary file associated with a repository.

    Args:
        repo (str): Repository name.
        info (dict[Any, Any]): Installation info containing 'path' and 'binary'.
        dry_run (bool): Simulate removal if True.
    """
    binary_path = Path(info["path"]) / info["binary"]
    version = info.get("tag")
    if binary_path.exists():
        if dry_run:
            logger.info(f"Dry-run: {repo}: Would uninstall {binary_path.name} {version} from {binary_path}")
        else:
            try:
                binary_path.unlink()
                logger.info(f"Uninstalled {binary_path.name} {version} from {binary_path} originated from {repo}")
            except PermissionError:
                logger.error(f"Permission denied when trying to uninstall {binary_path}")


def remove_package(repo: str, info: dict[Any, Any], dry_run: bool) -> None:
    """
    Remove the package directory if it exists.

    Args:
        repo (str): Repository name.
        info (dict[Any, Any]): Installation info that may contain 'package_path'.
        dry_run (bool): Simulate removal if True.
    """
    package_path_str = info.get("package_path")
    if package_path_str:
        package_path = Path(package_path_str)
        if package_path.is_dir():
            if dry_run:
                logger.info(f"Dry-run: {repo}: Would delete package folder {package_path}")
            else:
                try:
                    shutil.rmtree(package_path)
                    logger.info(f"Deleted package folder {package_path}")
                except PermissionError:
                    logger.error(f"Permission denied when trying to delete {package_path}")


def uninstall_binary(repo: str, install_data: dict, dry_run: bool) -> RepoResult:
    """
    Uninstalls a binary file associated with a given repository.

    Args:
        repo (str): The name of the repository associated with the binary.
        install_data (dict): A dictionary containing install information about the binary.
        dry_run (bool): If True, simulates the uninstallation process without making any changes.

    Returns:
        RepoResult: An enumeration indicating the result of the uninstallation process.
            Possible values:
                - RepoResult.dry_run_uninstall: Indicates a successful dry-run.
                - RepoResult.uninstalled: Indicates the binary was successfully uninstalled.
                - RepoResult.uninstall_failed: Indicates the uninstallation failed due to permission issues.
    """

    binary_path = Path(install_data["path"], install_data["binary"])
    if binary_path.exists():
        if dry_run:
            logger.success(f"Dry-run: {repo}: Would uninstall {binary_path.name} from {binary_path}.")
            # summary[RepoResult.dry_run_uninstall] += 1
            return RepoResult.dry_run_uninstall
        else:
            utils.run_commands(install_data.get("pre_update_commands"), "repo: pre-uninstall")
            try:
                binary_path.unlink()
                logger.success(f"Uninstalled {binary_path.name} from {binary_path} originated from {repo}")
                # uninstall_repos.append(repo)
                # summary[RepoResult.uninstalled] += 1
            except PermissionError:
                logger.error(f"Permission denied when trying to uninstall {binary_path}")
                # summary[RepoResult.uninstall_failed] += 1
                return RepoResult.uninstall_failed
            # else:
            #     return RepoResult.uninstalled
    return RepoResult.uninstalled


def uninstall(repositories: list[str], installed: dict[Any, Any], dry_run: bool = False) -> dict[RepoResult, int]:
    """
    Uninstall binaries which are not present in the repositories config anymore.
    If repositories is empty, all binaries will be uninstalled.
    This function will also remove the package folder if it exists.

    Args:
        repositories (list[str]): A list of repository names.
        installed (dict[Any, Any]): installed tracking installed versions and binaries.
        dry_run (bool): A flag to simulate the process without removing the binary (default: False).
    """
    if not installed:
        logger.log("INFO" if dry_run else "SUCCESS", "No binaries installed.")
        return {}
    if dry_run:
        logger.info("Check for repos to uninstall")
    elif repositories:
        logger.info("Uninstall binaries no longer in config.")
    elif utils.confirm_default_no("Are you sure that all programs should be uninstalled?"):
        logger.info("Uninstall all binaries.")
    else:
        logger.info("Uninstall cancelled.")
        return {RepoResult.cancelled: 1}
    uninstall_repos = []
    summary: dict[RepoResult, int] = defaultdict(int)
    for repo, install_data in installed.items():
        if repo not in repositories:
            uninstall_result = uninstall_binary(repo=repo, install_data=install_data, dry_run=dry_run)
            if uninstall_result == RepoResult.uninstalled:
                uninstall_repos.append(repo)
            summary[uninstall_result] += 1
    for repo in uninstall_repos:
        del installed[repo]
    return summary
