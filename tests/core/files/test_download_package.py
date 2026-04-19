import tempfile
import unittest
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path
from unittest.mock import Mock, patch

from loguru import logger

# Import the module using the new submodule path
from girsh.core import files

# -------------------------------
# FakeResponse for download_package tests
# -------------------------------


class FakeResponse:
    def __init__(self, headers: dict[str, str], content_chunks: list[bytes], status_code: int = 200) -> None:
        self.headers = headers
        self.status_code = status_code
        self._content_chunks = content_chunks
        self.ok = self.status_code < 400

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        yield from self._content_chunks


def fake_requests_get_success(url: str, stream: bool, allow_redirects: bool, timeout: int) -> FakeResponse:
    headers = {"content-disposition": 'attachment; filename="testfile.txt"'}
    return FakeResponse(headers, [b"data"])


# -------------------------------
# Tests for download_package
# -------------------------------


class DownloadPackageTest(unittest.TestCase):
    def setUp(self) -> None:
        logger.remove()  # Remove all loguru handlers to silence logging output
        self.temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
        self.output_dir: Path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_download_package_request_unauthorized(self) -> None:
        def fake_get(url: str, stream: bool, allow_redirects: bool, timeout: int) -> FakeResponse:
            return FakeResponse({}, [b"chunk"], status_code=401)

        download_url = "http://example.com/file"
        with patch("requests.get", side_effect=fake_get), patch.object(logger, "error") as mock_logger:
            files.download_package(download_url, self.output_dir)
            mock_logger.assert_called_once_with(f"Download of {download_url} failed with status: {HTTPStatus(401)}")

    def test_download_package_error_handling(self) -> None:
        import requests

        download_url = "http://example.com/file"

        # Test cases for HTTP status code errors
        status_error_cases = [
            (407, f"Proxy authentication required for {download_url}. Check proxy credentials."),
            (403, f"Access denied downloading {download_url}: {HTTPStatus(403).phrase}"),
        ]

        for status_code, expected_message in status_error_cases:
            with self.subTest(status_code=status_code):
                fake_response = FakeResponse({}, [b"chunk"], status_code=status_code)
                with patch("requests.get", return_value=fake_response), patch.object(logger, "error") as mock_logger:
                    files.download_package(download_url, self.output_dir)
                    mock_logger.assert_called_once_with(expected_message)

        # Test cases for exception errors
        exception_error_cases = [
            (
                requests.exceptions.ProxyError("Proxy connection failed"),
                f"Proxy error downloading {download_url}: Proxy connection failed. Check proxy configuration.",
            ),
            (
                requests.exceptions.ConnectionError("Connection refused"),
                f"Connection error downloading {download_url}: Connection refused",
            ),
            (
                requests.exceptions.ConnectTimeout("Connection timeout"),
                f"Connection timeout downloading {download_url}: Connection timeout. Check proxy/network.",
            ),
            (
                requests.exceptions.ReadTimeout("Read timeout"),
                f"Read timeout downloading {download_url}: Read timeout",
            ),
            (
                requests.exceptions.RequestException("Generic error"),
                f"Error downloading {download_url}: Generic error",
            ),
        ]

        for exc, expected_message in exception_error_cases:
            with (
                self.subTest(exception=type(exc).__name__),
                patch("requests.get", side_effect=exc),
                patch.object(logger, "error") as mock_logger,
            ):
                files.download_package(download_url, self.output_dir)
                mock_logger.assert_called_once_with(expected_message)

    def test_download_package_with_filename(self) -> None:
        with patch("requests.get", side_effect=fake_requests_get_success):
            result = files.download_package("http://example.com/file", self.output_dir, "explicit.txt")
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result.name, "explicit.txt")
            self.assertTrue(result.exists())
            self.assertEqual(result.read_bytes(), b"data")

    def test_download_package_without_filename(self) -> None:
        with patch("requests.get", side_effect=fake_requests_get_success):
            result = files.download_package("http://example.com/file", self.output_dir)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result.name, '"testfile.txt"')
            self.assertTrue(result.exists())
            self.assertEqual(result.read_bytes(), b"data")

    def test_download_package_no_header(self) -> None:
        def fake_get(url: str, stream: bool, allow_redirects: bool, timeout: int) -> FakeResponse:
            return FakeResponse({}, [b"chunk"])

        with patch("requests.get", side_effect=fake_get):
            result = files.download_package("http://example.com/file", self.output_dir)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result.name, "file")
            self.assertTrue(result.exists())
            self.assertEqual(result.read_bytes(), b"chunk")

    def test_download_package_already_downloaded(self) -> None:
        existing = self.output_dir / '"existing.txt"'
        existing.write_bytes(b"existing")

        def fake_get(url: str, stream: bool, allow_redirects: bool, timeout: int) -> FakeResponse:
            headers = {"content-disposition": 'attachment; filename="existing.txt"'}
            return FakeResponse(headers, [b"new data"])

        with patch("requests.get", side_effect=fake_get):
            result = files.download_package("http://example.com/existing.txt", self.output_dir)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result.read_bytes(), b"existing")

    def test_download_package_empty_chunk(self) -> None:
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.iter_content.return_value = [b"", b"data"]
            mock_response.headers = {"content-disposition": 'attachment; filename="testfile.txt"'}
            mock_get.return_value = mock_response

            result = files.download_package("http://example.com/file", self.output_dir)
            self.assertIsNotNone(result)
            if result is not None:
                self.assertEqual(result.name, '"testfile.txt"')
                self.assertTrue(result.exists())
                self.assertEqual(result.read_bytes(), b"data")


if __name__ == "__main__":
    unittest.main()
