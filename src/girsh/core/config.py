import argparse
import os
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from importlib import resources
from importlib.metadata import version
from pathlib import Path
from types import UnionType
from typing import Any, get_args, get_origin

import yaml
from loguru import logger

__version__ = version("girsh")


class ConversionError(TypeError):
    def __init__(self, value: Any, expected_type: type) -> None:
        super().__init__(f"Cannot convert {value!r} to {expected_type.__name__}")
        self.value = value
        self.expected_type = expected_type


def convert_to_bool(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    elif isinstance(value, str) and value.lower() in ["true", "false"]:
        return value.lower() == "true"
    else:
        raise ValueError


@dataclass
class General:
    bin_base_folder: Path = Path("/usr/local/bin") if os.geteuid() == 0 else Path.home() / ".local/bin"
    installed_file: Path = (
        Path("/etc/girsh/installed.yaml") if os.geteuid() == 0 else Path.home() / ".config" / "girsh" / "installed.yaml"
    )
    download_dir: Path = Path.home() / ".cache" / "girsh" / "downloads"
    package_pattern: str = r".*x86_64.*(gz|zip)$"  # Regex to find the desired package in the release assets
    package_base_folder: Path = Path("/opt/girsh") if os.geteuid() == 0 else Path.home() / ".local/share/girsh"
    proxy: str | None = None  # Proxy URL for downloading files

    def __setattr__(self, name: str, value: Any) -> None:
        expected_type = self.__annotations__.get(name)
        if expected_type is not None and not isinstance(value, expected_type):
            try:
                value = expected_type(value)
            except (TypeError, ValueError) as e:
                raise ConversionError(value, expected_type) from e
        super().__setattr__(name, value)


@dataclass
class Repository:
    comment: str = ""  # Description of the package
    package_pattern: str | None = None  # Regex to find the desired package in the release assets
    filter_pattern: str | None = None  # Regex to find the program file in extracted files
    binary_name: str | None = None  # Rename extracted binary file
    multi_file: bool = False  # Package requires all package files (not single binary)
    version: str | None = None  # Pin program to defined version
    download_url: str | None = None  # Optional download URL template, can contain `{version}` as a variable
    pre_update_commands: list[str | None] | None = None  # Command to run before updating the package
    post_update_commands: list[str | None] | None = None  # Command to run after updating the package

    def __setattr__(self, name: str, value: Any) -> None:
        expected_type: type | None = self.__annotations__.get(name)
        expected_type = get_args(expected_type)[0] if get_origin(expected_type) is UnionType else expected_type
        if get_origin(expected_type) is not None:  # type is a parameterized generic
            expected_type = get_origin(expected_type)
        logger.trace(f"Setting {name} to {value} of type {expected_type}")
        if value is not None and expected_type is not None and not isinstance(value, expected_type):
            try:
                value = convert_to_bool(value) if expected_type is bool else expected_type(value)
            except (TypeError, ValueError) as e:
                raise ConversionError(value, expected_type) from e
        super().__setattr__(name, value)


def update_general_config(general_config: General, data: dict) -> General:
    """
    Update a General dataclass instance with values from a dictionary.

    This function looks for a 'general' key in the provided data and updates
    the configuration fields if they exist, triggering any type conversions
    defined in __setattr__.

    Args:
        general_config (General): The current configuration instance.
        data (dict): Dictionary containing configuration data, e.g., from a YAML file.

    Returns:
        General: The updated configuration instance.
    """
    general_updates = data.get("general")
    if not isinstance(general_updates, dict):
        if general_updates is not None:
            logger.error(f"General config format is not dict: {data}")
        return general_config

    for key, value in general_updates.items():
        if key in general_config.__annotations__:
            setattr(general_config, key, value)
        else:
            logger.warning(f"Skipped general config entry {key}: {value}")
    return general_config


def update_repositories_config(
    repo_config: dict[str, Repository], data: dict, default_pattern: str
) -> dict[str, Repository]:
    """
    Update repository configurations using YAML data.

    This function extracts repository configurations from the "repositories" key in the provided
    YAML data. For each repository, it creates a new Repository instance (or a default one if the
    configuration is None) and ensures that a default package pattern is set if missing.

    Args:
        repo_config (dict[str, Repository]): Existing repository configuration mapping.
        data (dict): Loaded configuration data from a YAML file.
        default_pattern (str): Default package pattern to use when not specified.

    Returns:
        dict[str, Repository]: The updated repository configuration mapping.
    """
    repositories_data = data.get("repositories")
    if repositories_data is None:
        logger.warning(f"No repositories configured.{data}")
        return repo_config

    if not isinstance(repositories_data, dict):
        logger.error("The 'repositories' YAML config is not a dictionary.")
        return repo_config

    for repo_name, repo_data in repositories_data.items():
        try:
            repository = Repository(**repo_data) if repo_data is not None else Repository()
        except TypeError as e:
            logger.error(f"Repository '{repo_name}': {e}")
            continue
        if repository.package_pattern is None:
            repository.package_pattern = default_pattern

        repo_config[repo_name] = repository

    return repo_config


def load_yaml_config(file_path: str) -> tuple[General, dict[str, Repository]]:
    """
    Load and parse the YAML configuration file and update the general and repositories config.

    Args:
        file_path (str): Path to the YAML configuration file.

    Returns:
        tuple[General, dict[str, Repository]]: A tuple containing the updated General instance
            and a dictionary mapping repository names to Repository instances.
    """
    config_path = Path(file_path)
    try:
        with config_path.open("r") as file:
            data = yaml.safe_load(file)
            if not isinstance(data, dict):
                logger.warning(f"No valid configuration data found in '{file_path}'.")
                return General(), {}
    except FileNotFoundError:
        logger.error(f"Config file '{file_path}' not found.")
        sys.exit(1)
    except PermissionError:
        logger.error(f"Permission denied when reading config file '{file_path}'.")
        sys.exit(1)
    except (yaml.scanner.ScannerError, yaml.parser.ParserError) as err:
        logger.error(f"YAML syntax error in config file '{file_path}': {err}")
        sys.exit(1)

    logger.trace(f"Loaded config: {data}")
    general = update_general_config(General(), data)
    logger.trace(f"General config: {general}")

    repositories: dict[str, Repository] = defaultdict(Repository)
    repositories = update_repositories_config(repositories, data, general.package_pattern)
    logger.trace(f"Repositories config: {repositories}")

    # Check if there are other unexpected keys in the yaml config
    unexpected = set(data.keys()) - {"general", "repositories"}
    if unexpected:
        logger.warning(f"Config YAML contains unexpected keys: {unexpected}")

    return general, repositories


def edit_config(config_path: Path) -> int:
    """
    Open the specified config file in the user's default terminal editor.

    Args:
        config_path (Path): Path to the configuration file to edit.

    Returns:
        int: error code
    """
    # Ensure the config file exists or ask to create an empty one if not found
    if not config_path.exists():
        create_file = (
            input(f"The file '{config_path}' does not exist. Do you want to create it? (y/N): ").strip().lower()
        )
        if create_file == "y":
            logger.info("Create config file from template")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_template = resources.files("girsh.templates").joinpath("config_template.yaml")
            with resources.as_file(config_template) as template_file:
                config_content = template_file.read_text()
                config_path.write_text(config_content)
        else:
            logger.error("Operation aborted. No file was created.")
            return 0

    # Record the file's last modification time
    original_mod_time = config_path.stat().st_mtime

    # Get the user's default editor from environment variables
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"

    try:
        # Open the file in the chosen editor
        subprocess.run([editor, str(config_path)], check=True)  # noqa: S603
        # Check if the file modification time changed after editing
        updated_mod_time = config_path.stat().st_mtime
        if updated_mod_time != original_mod_time:
            logger.info("The config file was modified.")
        else:
            logger.info("No changes were made to the config file.")
    except FileNotFoundError:
        logger.error(f"Error: Editor '{editor}' not found. Please set the EDITOR environment variable.")
        return 1
    except subprocess.CalledProcessError as e:
        logger.error(f"Error: Failed to open {config_path} in {editor}. {e!s}")
        return 1
    return 0


def get_arguments() -> argparse.Namespace:
    """
    Parse the command line arguments

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="Git Install Released Software Helper")

    # Add mutually exclusive group for commands, default command is install/update
    commands = parser.add_mutually_exclusive_group(required=False)
    commands.add_argument(
        "-r", "--reinstall", nargs="+", metavar="BINARY", help="Force re-installation even if version unchanged"
    )
    commands.add_argument(
        "-u",
        "--uninstall",
        action="store_true",
        help="Uninstall previously installed binary if not present in config anymore",
    )
    commands.add_argument("--uninstall-all", action="store_true", help="Uninstall all previously installed binaries")
    commands.add_argument("--clean", action="store_true", help="Remove the downloads folder and exit")
    commands.add_argument("-s", "--show", action="store_true", help="Show config and currently installed binaries")
    commands.add_argument("-e", "--edit", action="store_true", help="Open the config file in the default editor")

    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("/etc/girsh/settings.yaml")
        if os.geteuid() == 0
        else Path.home() / ".config" / "girsh" / "settings.yaml",
        help="Path to config file, defaults to ~/.config/girsh.yaml",
    )
    parser.add_argument(
        "-d", "--dry-run", action="store_true", help="Run without actually installing or removing any files."
    )
    parser.add_argument("-p", "--proxy", type=str, help="Proxy URL for downloading files")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase output verbosity (up to 3 times)")
    parser.add_argument("-g", "--global", dest="system", action="store_true", help="Install as root at system level")
    parser.add_argument("-V", "--version", action="version", version=f"girsh {__version__}")
    return parser.parse_args()
