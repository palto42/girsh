import bz2
import os
import re
import shutil
import sys
import tarfile
import zipfile
from http import HTTPStatus
from pathlib import Path
from typing import Any

import requests
from loguru import logger


def clean_downloads_folder(download_dir: Path) -> int:
    """
    Remove the downloads folder and exit.

    Args:
        download_dir (Path): The download folder path

    Returns:
        int: error code
    """
    try:
        if download_dir.exists() and download_dir.is_dir():
            logger.debug(f"Removing downloads folder: {download_dir}")
            shutil.rmtree(download_dir)
            logger.info("Downloads folder removed.")
        else:
            logger.info(f"Download folder {download_dir} doesn't exist.")
    except PermissionError:
        logger.error(f"No permission to delete the download folder {download_dir}")
        return 1
    return 0


def get_filename_from_cd(content_disposition: str | None) -> str | None:
    """
    Extract filename from Content-Disposition header.

    Args:
        content_disposition (str): The Content-Disposition header value.

    Returns:
        str: The filename if found, otherwise None.
    """
    if not content_disposition:
        return None

    # The header might look like: 'attachment; filename="archive.tar.gz"'
    logger.debug(f"Download content-disposition: {content_disposition}")
    try:
        filename_match = content_disposition.split("filename=")[1].split(";")[0]
    except IndexError:
        return None
    else:
        logger.debug(f"Matched content-disposition: {filename_match}")
        return filename_match


def download_package(download_url: str, output_dir: Path, filename: str | None = None) -> Path | None:
    """
    Downloads a file from the given URL and saves it to the specified output directory.

    Args:
        download_url (str): The URL to download the file from.
        output_dir (Path): The directory where the downloaded file will be saved.
        filename (str | None, optional): The name to save the file as. If not provided, the filename will be
                                         extracted from the Content-Disposition header or the URL.

    Returns:
        Path | None: The path to the downloaded file, or None if the download failed.
    """
    logger.debug(f"Downloading from {download_url}")
    binary_response = requests.get(download_url, stream=True, allow_redirects=True, timeout=30)
    if binary_response.ok:
        filename = filename if filename else get_filename_from_cd(binary_response.headers.get("content-disposition"))
        output_path = output_dir / (filename if filename else download_url.rsplit("/", 1)[1])
        if not output_path.is_file():
            with output_path.open("wb") as f:
                for chunk in binary_response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            logger.info(f"Downloaded: {output_path}")
        else:
            logger.info(f"Asset already downloaded: {output_path}")
        return output_path
    else:
        logger.error(f"Download of {download_url} failed with status: {HTTPStatus(binary_response.status_code)}")
    return None


def download_github_release(
    url: str,
    package_pattern: str,
    output_dir: Path,
    release_info: dict[Any, Any] | None = None,
    download_url: str | None = None,
) -> tuple[Path, str] | None:
    """
    Download a matching release asset from a GitHub repository.

    Args:
        url (str): GitHub API release URL.
        package_pattern (str): Regex pattern to match the desired asset.
        output_dir (Path): Directory to save the downloaded asset.
        release_info (dict[Any, Any] | None): Optionally provide release JSON to avoid duplicate API calls.
        download_url (str|None): Optional download URL template

    Returns:
        tuple[Path, str] | None: Tuple of path to the downloaded file and the release tag, or None if no match.
    """

    if release_info is None:
        try:
            response = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"}, timeout=10)
            response.raise_for_status()
            release_info = response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch release info: {e}")
            return None

    logger.trace(f"Release info: {release_info}")
    tag = release_info.get("tag_name", "unknown")
    assets = release_info.get("assets", [])

    if download_url:
        download_url = download_url.replace("{version}", tag)
        result = download_package(download_url, output_dir)
        return (result, tag) if result else None

    logger.debug(f"Searching for package matching pattern: {package_pattern}")
    for asset in assets:
        asset_name = asset.get("name", "")
        if re.search(package_pattern, asset_name) or not package_pattern:
            download_url = asset.get("browser_download_url")
            if download_url:
                logger.debug(f"Downloading asset: {asset_name} from {download_url}")
                result = download_package(download_url, output_dir, asset_name)
                return (result, tag) if result else None
            else:
                logger.warning(f"No download URL found for asset: {asset_name}")
                return None

    logger.info("No matching asset found.")
    return None


def get_common_prefix(names: list[str]) -> str | None:
    """
    Determine the common top-level folder from a list of archive member names.

    Args:
        names (list[str]): List of member paths (as strings) from the archive.

    Returns:
        str | None: The common top-level folder if all names share one; otherwise, None.
    """
    prefixes = {name.lstrip("./").split("/", 1)[0] for name in names if name.lstrip("./")}
    return prefixes.pop() if len(prefixes) == 1 else None


def is_safe_path(base: Path, target: Path) -> bool:
    """
    Check if the resolved target path is within the resolved base directory to prevent path traversal.

    Args:
        base (Path): The intended base directory.
        target (Path): The target path to be validated.

    Returns:
        bool: True if the target is within the base directory; False otherwise.
    """
    try:
        return target.resolve().is_relative_to(base.resolve())
    except OSError:
        # General OS-related errors (e.g., invalid paths)
        return False


def extract_zip_archive(archive: zipfile.ZipFile, base: Path) -> None:
    """
    Extract members from a zip archive into the given base directory, skipping unsafe paths.

    Args:
        archive (zipfile.ZipFile): The zip archive to extract.
        base (Path): The base directory where files will be extracted.

    Returns:
        None
    """
    for name in archive.namelist():
        target = base / name
        if is_safe_path(base, target):
            archive.extract(name, base)
        else:
            logger.warning(f"Skipping unsafe member: {name}")


def extract_tar_archive(archive: tarfile.TarFile, base: Path) -> None:
    """
    Extract members from a tar archive into the given base directory, skipping unsafe paths.

    Args:
        archive (tarfile.TarFile): The tar archive to extract.
        base (Path): The base directory where files will be extracted.

    Returns:
        None
    """
    archive.extraction_filter = getattr(
        tarfile, "tar_filter", (lambda member, path: member)
    )  # Use the 'tar' filter if available, but revert to Python 3.11 behavior ('fully_trusted') if this feature is not available
    for member in archive.getmembers():
        target = base / member.name
        if is_safe_path(base, target):
            archive.extract(member, base)
        else:
            logger.warning(f"Skipping unsafe member: {member.name}")


def extract_bz2_archive(file_path: Path, extract_to: Path, package_name: str) -> None:
    """
    Extract a pure bz2 compressed file (non-tar archive) into a subfolder.

    The function decompresses a .bz2 file and writes the output into a folder
    named after package_name within extract_to.

    Args:
        file_path (Path): The path to the .bz2 file.
        extract_to (Path): The base directory where the file should be extracted.
        package_name (str): The name for the package folder.
    """
    target_folder = extract_to / package_name
    target_folder.mkdir(parents=True, exist_ok=True)
    # Remove the .bz2 suffix to obtain the original filename.
    output_file = target_folder / file_path.with_suffix("").name
    with bz2.open(file_path, "rb") as f_in, output_file.open("wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    logger.info(f"Extracted bz2 file to: {output_file}")


def extract_archive(file_path: Path, extract_to: Path, package_name: str) -> str | None:
    """
    Extract the archive based on its extension and return the common top-level folder name
    if one is detected. For pure bz2 files, extraction is done directly.

    Args:
        file_path (Path): The path to the archive.
        extract_to (Path): The base extraction directory.
        package_name (str): The package folder name used when a common folder is not found.

    Returns:
        str | None: The common top-level folder name if detected; otherwise, None.
    """
    common = None

    if file_path.suffix == ".zip":
        with zipfile.ZipFile(file_path, "r") as archive:
            names = archive.namelist()
            common = get_common_prefix(names)
            base = extract_to if common else extract_to / package_name
            if not common:
                base.mkdir(parents=True, exist_ok=True)
            extract_zip_archive(archive, base)

    elif file_path.suffixes[-2:] == [".tar", ".gz"] or file_path.suffix == ".tgz":
        with tarfile.open(file_path, "r:gz") as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            common = get_common_prefix(names)
            base = extract_to if common else extract_to / package_name
            if not common:
                base.mkdir(parents=True, exist_ok=True)
            extract_tar_archive(archive, base)

    elif file_path.suffixes[-2:] == [".tar", ".bz2"]:
        with tarfile.open(file_path, "r:bz2") as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            common = get_common_prefix(names)
            base = extract_to if common else extract_to / package_name
            if not common:
                base.mkdir(parents=True, exist_ok=True)
            extract_tar_archive(archive, base)

    elif file_path.suffix == ".bz2":
        # Handle pure bz2 compressed files.
        extract_bz2_archive(file_path, extract_to, package_name)
        return None  # Pure bz2 extraction does not yield a common folder.

    else:  # Assume that the file is a binary
        logger.info("Downloaded file is not a known archive, assume it is a binary.")
        # Move downloaded file to extract folder
        file_path.rename(extract_to / file_path.name)
        return None

    return common


def extract_package(file_path: Path, extract_to: Path, package_name: str) -> None:
    """
    Extract a compressed package file into a controlled folder structure.
    This function now delegates the extraction process to `extract_archive` to reduce complexity.

    Args:
        file_path (Path): The path to the compressed package file.
        extract_to (Path): The base directory where the package should be extracted.
        package_name (str): The name for the package folder.

    Returns:
        None
    """
    logger.info(f"Extracting {file_path} into {extract_to}")
    common = extract_archive(file_path, extract_to, package_name)

    # If a common top-level folder was detected during extraction, rename it.
    if common:
        common_folder = extract_to / common
        new_folder = extract_to / package_name
        try:
            if new_folder.exists():
                logger.debug(f"Target folder {new_folder} already exists; skipping rename.")
            else:
                common_folder.rename(new_folder)
                logger.info(f"Renamed {common_folder} to {new_folder}")
        except PermissionError as pe:
            logger.error(f"Failed to rename {common_folder} to {new_folder}: {pe}")
            return
        except OSError as oe:
            logger.error(f"Failed to rename {common_folder} to {new_folder}: {oe}")
            return
    logger.debug(f"Extraction complete. Files are in: {extract_to / package_name}")


def find_binary(extract_dir: Path, filter_pattern: str | None) -> Path | None:
    """
    Search for the binary in the extracted directory and rename it if necessary.

    Args:
        extract_dir (Path): The directory where the package was extracted.
        filter_pattern (str | None): A pattern to filter and match the binary file.

    Returns:
        Path | None: The path to the binary if found, or None if no binary is found.
    """
    if filter_pattern:
        logger.trace(f"Find {filter_pattern} in {[str(n) for n in extract_dir.rglob('*')][:3]} ...")
        for file_path in extract_dir.rglob("*"):
            if file_path.is_file() and re.search(filter_pattern, str(file_path)):
                logger.debug(f"Found matching file {file_path!s}")
                return file_path
    else:
        candidates = [p for p in extract_dir.rglob("*") if p.is_file() and os.access(p, os.X_OK)]
        if len(candidates) > 1:
            logger.info(f"Found multiple binaries, will install first one: {candidates}")
        if candidates:
            return candidates[0]
        all_files = [p for p in extract_dir.rglob("*") if p.is_file()]
        logger.warning(f"No executable binary found in {extract_dir}: {candidates}: {all_files}")
    logger.debug(f"Binary not found in {extract_dir}")
    return None


def copy_to_bin(binary_path: Path, bin_base_folder: Path, binary_name: str | None = None) -> Path:
    """
    Copy the binary file to the system or user binary directory.

    Args:
        binary_path (Path): Path to the binary file to be copied.
        bin_base_folder (Path): The binaries base folder path.
        binary_name (str | None): Optional binary name, defaults to the name from binary path

    Returns:
        Path: Path to installed binary file
    """
    try:
        bin_base_folder.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.error(f"Permission denied when creating bin folder '{bin_base_folder}'.")
        sys.exit(1)
    dest_path = bin_base_folder / (Path(binary_name).name if binary_name else binary_path.name)
    try:
        shutil.copy2(binary_path, dest_path)
        logger.info(f"Copied binary to: {dest_path}")
        # make executable
        dest_path.chmod(0o755)
    except PermissionError:
        logger.error(f"Permission denied to install '{dest_path}'.")
        sys.exit(1)
    except OSError as err:
        logger.error(f"Copy binary to '{dest_path}' failed with error: {err.strerror}")
        sys.exit(1)
    return dest_path


def move_to_packages(
    package_source: Path,
    package_base_folder: Path,
    bin_base_folder: Path,
    binary_path: Path,
    binary_name: str | None = None,
) -> Path:
    """
    Move the extracted package to the packages base folder and
    symlink the binary file to the system or user binary directory.

    Args:
        package_source (Path): Path to the extracted package
        package_base_folder (Path): The base package folder path.
        bin_base_folder (Path): The binaries base folder path.
        binary_path (Path): Path to the binary file to be linked.
        binary_name (str | None): Optional symlink name, defaults to the name from binary path

    Returns:
        Path: Path to installed binary file
    """
    package_path = package_base_folder / package_source.name
    dest_bin_path = bin_base_folder / (Path(binary_name).name if binary_name else binary_path.name)

    # Create package base folder if it doesn't exist
    try:
        package_base_folder.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.error(f"Permission denied when creating packages folder '{package_base_folder}'.")
        sys.exit(1)

    # Delete existing package folder if it exists
    if package_path.is_dir():
        logger.debug(f"Delete old package folder {package_path}")
        shutil.rmtree(package_path)

    # Move source package folder to package base folder
    try:
        package_source.rename(package_path)
        logger.info(f"Moved package to: {package_path}")
    except PermissionError:
        logger.error(f"Permission denied to move package to '{package_path}'.")
        sys.exit(1)
    except OSError as err:
        logger.error(f"Move package to '{package_path}' failed with error: {err.strerror}")
        sys.exit(1)

    # Create symlink to binary
    try:
        logger.debug(f"Create symlink from {dest_bin_path} to {package_path / binary_path.relative_to(package_source)}")
        dest_bin_path.unlink(missing_ok=True)
        dest_bin_path.symlink_to(package_path / binary_path.relative_to(package_source))
    except PermissionError:
        logger.error(f"Permission denied to create symlink to '{dest_bin_path}'.")
        sys.exit(1)
    except OSError as err:
        logger.error(f"Symlink moved package to '{dest_bin_path}' failed with error: {err.strerror}")
        sys.exit(1)
    return dest_bin_path
