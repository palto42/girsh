import sys
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from girsh.core.config import Repository


def load_installed(installed_file: Path) -> dict[str, dict]:
    """
    Load the version installed from a YAML file.

    Args:
        installed_file (Path): Path to the installed file.

    Returns:
        dict[str, str]: Dict of installed software details.
    """
    # Ensure that the folder for the installed file exists, so that updates can be saved later
    try:
        installed_file.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.error(f"Permission denied when creating installed folder '{installed_file.parent}'.")
        sys.exit(1)
    try:
        if installed_file.exists():
            with installed_file.open("r") as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {}
        else:
            logger.info(f"Installed packages file '{installed_file}' not found. Proceeding with empty installed.")
    except PermissionError:
        logger.error(
            f"Warning: Permission denied when reading installed file '{installed_file}'. Proceeding with empty installed."
        )
    return {}


def save_installed(installed_file: Path, data: dict[Any, Any]) -> int:
    """
    Save the version installed to a YAML file.

    Args:
        installed_file (Path): Path to the installed file.
        data (dict[Any, Any]): Version installed data to save.

    Returns:
        int: error code
    """
    try:
        with installed_file.open("w") as f:
            yaml.safe_dump(data, f)
    except PermissionError:
        logger.error(f"Permission denied when writing to installed file '{installed_file}'.")
        return 1
    except FileNotFoundError:
        logger.error(f"installed file '{installed_file}' not found and cannot be created.")
        return 1
    return 0


def get_comment(repo: str, repositories: dict[str, Repository]) -> str:
    """
    Get the comment from the repository config.
    If the repository is not found, return a default message.

    Args
        repo (str): Name of the repository

    Returns:
        str: Comment from repository config
    """
    if repo in repositories:
        return repositories[repo].comment
    logger.debug(f"The repository {repo} is not present in current config.")
    return "Not found in config."


def show_installed(data: dict[Any, Any], repositories: dict[str, Repository]) -> int:
    """
    Display installed binaries in a table format with auto-fitted column widths.

    Args:
        data (dict[Any, Any]): Dictionary containing installed binaries with metadata.

    Returns:
        int: Error code (0 for success).
    """
    if not data:
        logger.success("Nothing installed via `girsh`")
        return 0

    # Table headers
    headers = ["Repository", "Comment", "Binary", "Tag"]

    # Gather row data
    rows = [(repo, get_comment(repo, repositories), status["binary"], status["tag"]) for repo, status in data.items()]

    # Calculate max column widths
    col_widths = [max(len(str(row[i])) for row in [headers, *rows]) for i in range(len(headers))]

    # Format line separator
    separator = "+".join("-" * (w + 2) for w in col_widths)
    separator = f"+{separator}+"

    # Print table
    logger.success("Currently installed binaries:")
    logger.success(separator)
    logger.success("| " + " | ".join(f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers))) + " |")
    logger.success(separator)

    for row in rows:
        logger.success("| " + " | ".join(f"{row[i]:<{col_widths[i]}}" for i in range(len(row))) + " |")

    logger.success(separator)

    return 0
