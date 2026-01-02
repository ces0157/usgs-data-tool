"""Tests for download module."""

import os
import sys
import pytest
from unittest.mock import patch, Mock, MagicMock
import requests

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_helpers.download import (
    validate_url,
    check_disk_space,
    extract_project_name,
    safe_download,
    create_session,
    download_data
)
from exceptions import (
    MalformedURLError,
    DiskSpaceError,
    ConnectionFailedError,
    DownloadInterruptedError,
    FileWriteError
)


class TestValidateUrl:
    """Tests for URL validation function."""

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        assert validate_url("https://example.com/file.tif") is True

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        assert validate_url("http://example.com/file.tif") is True

    def test_invalid_url_no_scheme(self):
        """Test URL without scheme."""
        assert validate_url("example.com/file.tif") is False

    def test_invalid_url_empty(self):
        """Test empty URL."""
        assert validate_url("") is False

    def test_invalid_url_none(self):
        """Test None URL."""
        assert validate_url(None) is False

    def test_invalid_url_ftp_scheme(self):
        """Test FTP scheme (not allowed)."""
        assert validate_url("ftp://example.com/file.tif") is False


class TestCheckDiskSpace:
    """Tests for disk space checking function."""

    def test_sufficient_space(self, temp_dir):
        """Test when sufficient space is available."""
        # Most systems have at least 1KB free
        assert check_disk_space(temp_dir, 1024) is True

    def test_insufficient_space(self, temp_dir):
        """Test when insufficient space is available."""
        # Request more space than any system could have
        assert check_disk_space(temp_dir, 10**20) is False

    def test_invalid_path(self):
        """Test with invalid path (should return True to proceed anyway)."""
        assert check_disk_space("/nonexistent/path/that/does/not/exist", 1024) is True


class TestExtractProjectName:
    """Tests for project name extraction from URL."""

    def test_valid_url(self):
        """Test extraction from valid USGS URL."""
        url = "https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/1m/Projects/GA_GwinnetCo_2017/TIFF/file.tif"
        assert extract_project_name(url) == "GA_GwinnetCo_2017"

    def test_invalid_url_no_projects(self):
        """Test URL without Projects segment."""
        url = "https://example.com/some/other/path/file.tif"
        with pytest.raises(MalformedURLError):
            extract_project_name(url)

    def test_empty_url(self):
        """Test empty URL."""
        with pytest.raises(MalformedURLError):
            extract_project_name("")

    def test_none_url(self):
        """Test None URL."""
        with pytest.raises(MalformedURLError):
            extract_project_name(None)


class TestSafeDownload:
    """Tests for safe download function."""

    def test_invalid_url_raises_error(self, temp_dir):
        """Test that invalid URL raises MalformedURLError."""
        session = Mock()
        filename = os.path.join(temp_dir, "test.tif")

        with pytest.raises(MalformedURLError):
            safe_download(session, "not-a-valid-url", filename)

    @patch('data_helpers.download.check_disk_space')
    def test_insufficient_disk_space(self, mock_disk_space, temp_dir):
        """Test handling of insufficient disk space."""
        mock_disk_space.return_value = False

        mock_response = Mock()
        mock_response.headers = {'content-length': '1000000000'}
        mock_response.raise_for_status = Mock()

        session = Mock()
        session.get.return_value = mock_response

        filename = os.path.join(temp_dir, "test.tif")

        with pytest.raises(DiskSpaceError):
            safe_download(session, "https://example.com/test.tif", filename)

    def test_connection_error(self, temp_dir):
        """Test handling of connection error during download."""
        session = Mock()
        session.get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        filename = os.path.join(temp_dir, "test.tif")

        with pytest.raises(ConnectionFailedError):
            safe_download(session, "https://example.com/test.tif", filename)

    def test_timeout_error(self, temp_dir):
        """Test handling of timeout during download."""
        session = Mock()
        session.get.side_effect = requests.exceptions.Timeout("Timeout")

        filename = os.path.join(temp_dir, "test.tif")

        with pytest.raises(ConnectionFailedError):
            safe_download(session, "https://example.com/test.tif", filename)

    @patch('data_helpers.download.check_disk_space')
    def test_successful_download(self, mock_disk_space, temp_dir):
        """Test successful file download."""
        mock_disk_space.return_value = True

        mock_response = Mock()
        mock_response.headers = {'content-length': '9'}
        mock_response.raise_for_status = Mock()
        mock_response.iter_content.return_value = [b'test data']

        session = Mock()
        session.get.return_value = mock_response

        filename = os.path.join(temp_dir, "test.tif")
        safe_download(session, "https://example.com/test.tif", filename)

        assert os.path.exists(filename)
        with open(filename, 'rb') as f:
            assert f.read() == b'test data'


class TestCreateSession:
    """Tests for session creation."""

    def test_session_has_retry_adapter(self):
        """Test that session is configured with retry adapter."""
        session = create_session()
        assert session is not None
        # Check that adapters are mounted
        assert 'https://' in session.adapters
        assert 'http://' in session.adapters


class TestDownloadData:
    """Tests for main download_data function."""

    @patch('data_helpers.download.merge_dem')
    @patch('data_helpers.download.safe_download')
    def test_download_creates_directories(self, mock_download, mock_merge, temp_dir, mock_args):
        """Test that download_data creates necessary directories."""
        mock_args.output_dir = temp_dir

        download_info = [{
            'title': 'USGS 1 Meter DEM',
            'url': 'https://example.com/Projects/TestProject/file.tif'
        }]

        download_data(mock_args, download_info, temp_dir)

        expected_dir = os.path.join(temp_dir, "dem", "TestProject")
        assert os.path.exists(expected_dir)

    @patch('data_helpers.download.safe_download')
    def test_lidar_detection(self, mock_download, temp_dir, mock_args):
        """Test correct detection of lidar data type."""
        mock_args.output_dir = temp_dir
        mock_args.type = "lidar"

        download_info = [{
            'title': 'Lidar Point Cloud',
            'url': 'https://example.com/Projects/LidarProject/file.laz'
        }]

        download_data(mock_args, download_info, temp_dir)

        expected_dir = os.path.join(temp_dir, "lidar", "LidarProject")
        assert os.path.exists(expected_dir)

    @patch('data_helpers.download.merge_dem')
    @patch('data_helpers.download.safe_download')
    def test_skips_item_without_url(self, mock_download, mock_merge, temp_dir, mock_args):
        """Test that items without URL are skipped."""
        mock_args.output_dir = temp_dir

        download_info = [
            {'title': 'No URL item', 'url': None},
            {'title': 'Valid item', 'url': 'https://example.com/Projects/TestProject/file.tif'}
        ]

        download_data(mock_args, download_info, temp_dir)

        # Should only call download once (for valid item)
        assert mock_download.call_count == 1

    @patch('data_helpers.download.merge_dem')
    @patch('data_helpers.download.safe_download')
    def test_continues_on_download_error(self, mock_download, mock_merge, temp_dir, mock_args):
        """Test that processing continues after download error."""
        from exceptions import DownloadError
        mock_args.output_dir = temp_dir

        # First call raises error, second succeeds
        mock_download.side_effect = [DownloadError("Failed"), None]

        download_info = [
            {'title': 'USGS 1 Meter DEM', 'url': 'https://example.com/Projects/Project1/file1.tif'},
            {'title': 'USGS 1 Meter DEM', 'url': 'https://example.com/Projects/Project2/file2.tif'}
        ]

        # Should not raise, should continue processing
        download_data(mock_args, download_info, temp_dir)

        assert mock_download.call_count == 2
