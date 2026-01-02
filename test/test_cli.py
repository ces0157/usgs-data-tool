"""Tests for CLI module."""

import os
import sys
import json
import pytest
from unittest.mock import patch, Mock, MagicMock, mock_open
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cli import (
    load_config,
    load_usgs_config,
    check_arguments,
    main
)
from exceptions import (
    ConfigNotFoundError,
    InvalidConfigError,
    ConnectionFailedError,
    APITimeoutError,
    USGSDataToolError
)


# ============================================================================
# Tests for load_config function
# ============================================================================

class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, temp_dir):
        """Test loading a valid JSON configuration file."""
        config_path = os.path.join(temp_dir, "config.json")
        config_data = {
            "aoi": [-84.5, 33.6, -84.4, 33.7],
            "type": "dem",
            "output_dir": "/tmp/output"
        }

        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        result = load_config(config_path)
        assert result == config_data

    def test_load_config_file_not_found(self):
        """Test loading non-existent config file."""
        with pytest.raises(SystemExit) as excinfo:
            load_config("/nonexistent/config.json")
        assert excinfo.value.code == 1

    def test_load_config_invalid_json(self, temp_dir):
        """Test loading config file with invalid JSON."""
        config_path = os.path.join(temp_dir, "invalid.json")
        with open(config_path, 'w') as f:
            f.write("{ invalid json content")

        with pytest.raises(SystemExit) as excinfo:
            load_config(config_path)
        assert excinfo.value.code == 1

    @patch('builtins.open', side_effect=IOError("Cannot read file"))
    @patch('os.path.exists', return_value=True)
    def test_load_config_io_error(self, mock_exists, mock_file):
        """Test handling of IOError when reading config."""
        with pytest.raises(SystemExit) as excinfo:
            load_config("/some/path/config.json")
        assert excinfo.value.code == 1


# ============================================================================
# Tests for load_usgs_config function
# ============================================================================

class TestLoadUsgsConfig:
    """Tests for load_usgs_config function."""

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_valid_usgs_config(self, mock_file, mock_exists):
        """Test loading valid USGS config file."""
        mock_exists.return_value = True
        usgs_data = {
            "dem": {
                "regular": {
                    "usgs_name": "Digital Elevation Model (DEM) 1 meter",
                    "usgs_data_format": "GeoTIFF"
                }
            }
        }
        mock_file.return_value.read.return_value = json.dumps(usgs_data)

        # Mock json.load to return our data
        with patch('json.load', return_value=usgs_data):
            result = load_usgs_config()
            assert "dem" in result

    @patch('os.path.exists', return_value=False)
    def test_load_usgs_config_file_not_found(self, mock_exists):
        """Test when USGS config file is not found."""
        with pytest.raises(SystemExit) as excinfo:
            load_usgs_config()
        assert excinfo.value.code == 1

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data="{ invalid json")
    def test_load_usgs_config_invalid_json(self, mock_file, mock_exists):
        """Test loading USGS config with invalid JSON."""
        with pytest.raises(SystemExit) as excinfo:
            load_usgs_config()
        assert excinfo.value.code == 1

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', side_effect=IOError("Cannot read"))
    def test_load_usgs_config_io_error(self, mock_file, mock_exists):
        """Test handling of IOError when reading USGS config."""
        with pytest.raises(SystemExit) as excinfo:
            load_usgs_config()
        assert excinfo.value.code == 1


# ============================================================================
# Tests for check_arguments function
# ============================================================================

class TestCheckArguments:
    """Tests for check_arguments function."""

    def test_valid_arguments_no_config(self):
        """Test argument checking with valid command line args and no config."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--aoi', type=float, nargs=4)
        parser.add_argument('--type', type=str)
        parser.add_argument('--output-dir', type=str)

        config_defaults = {}
        remaining_argv = ['--aoi', '-84.5', '33.6', '-84.4', '33.7',
                          '--type', 'dem', '--output-dir', '/tmp/output']
        pre_args = Mock(config=None)

        result = check_arguments(parser, config_defaults, remaining_argv, pre_args)

        assert result.aoi == [-84.5, 33.6, -84.4, 33.7]
        assert result.type == 'dem'
        assert result.output_dir == '/tmp/output'

    def test_valid_arguments_with_config(self):
        """Test argument checking with config file defaults."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--aoi', type=float, nargs=4)
        parser.add_argument('--type', type=str)
        parser.add_argument('--output-dir', type=str)

        config_defaults = {
            'aoi': [-84.5, 33.6, -84.4, 33.7],
            'type': 'lidar',
            'output_dir': '/config/output'
        }
        remaining_argv = []
        pre_args = Mock(config='/path/to/config.json')

        result = check_arguments(parser, config_defaults, remaining_argv, pre_args)

        assert result.aoi == [-84.5, 33.6, -84.4, 33.7]
        assert result.type == 'lidar'
        assert result.output_dir == '/config/output'

    def test_missing_required_args_no_config(self):
        """Test error when required arguments are missing without config."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--aoi', type=float, nargs=4)
        parser.add_argument('--type', type=str)
        parser.add_argument('--output-dir', type=str)

        config_defaults = {}
        remaining_argv = []  # Missing all required args
        pre_args = Mock(config=None)

        with pytest.raises(SystemExit):
            check_arguments(parser, config_defaults, remaining_argv, pre_args)

    def test_missing_required_key_in_config(self):
        """Test error when config is missing a required key."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--aoi', type=float, nargs=4)
        parser.add_argument('--type', type=str)
        parser.add_argument('--output-dir', type=str)

        config_defaults = {
            'type': 'dem',
            'output_dir': '/config/output'
            # Missing 'aoi'
        }
        remaining_argv = []
        pre_args = Mock(config='/path/to/config.json')

        with pytest.raises(SystemExit):
            check_arguments(parser, config_defaults, remaining_argv, pre_args)

    def test_command_line_overrides_config(self):
        """Test that command line arguments override config defaults."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--aoi', type=float, nargs=4)
        parser.add_argument('--type', type=str)
        parser.add_argument('--output-dir', type=str)

        config_defaults = {
            'aoi': [-84.5, 33.6, -84.4, 33.7],
            'type': 'dem',
            'output_dir': '/config/output'
        }
        remaining_argv = ['--type', 'lidar']  # Override type from config
        pre_args = Mock(config='/path/to/config.json')

        result = check_arguments(parser, config_defaults, remaining_argv, pre_args)

        assert result.type == 'lidar'  # Should use command line value
        assert result.output_dir == '/config/output'  # Should use config value


# ============================================================================
# Integration Tests for main function
# ============================================================================

class TestMainFunction:
    """Integration tests for main CLI function."""

    @patch('cli.download_data')
    @patch('cli.fetch_data_list')
    @patch('cli.load_usgs_config')
    @patch('os.makedirs')
    @patch('sys.argv', ['cli.py', '--aoi', '-84.5', '33.6', '-84.4', '33.7',
                         '--type', 'dem', '--output-dir', '/tmp/test'])
    def test_main_successful_dem_download(self, mock_makedirs, mock_usgs_config,
                                          mock_fetch, mock_download):
        """Test successful DEM download workflow."""
        mock_usgs_config.return_value = {"dem": {"regular": {}}}
        mock_fetch.return_value = [
            {"title": "Test DEM", "url": "https://example.com/test.tif"}
        ]

        main()

        # Verify API calls
        mock_fetch.assert_called_once()
        mock_download.assert_called_once()

    @patch('cli.download_data')
    @patch('cli.fetch_data_list')
    @patch('cli.load_usgs_config')
    @patch('os.makedirs')
    @patch('sys.argv', ['cli.py', '--aoi', '-84.5', '33.6', '-84.4', '33.7',
                         '--type', 'lidar', '--output-dir', '/tmp/test'])
    def test_main_successful_lidar_download(self, mock_makedirs, mock_usgs_config,
                                            mock_fetch, mock_download):
        """Test successful LiDAR download workflow."""
        mock_usgs_config.return_value = {"lidar": {"regular": {}}}
        mock_fetch.return_value = [
            {"title": "Test LiDAR", "url": "https://example.com/test.laz"}
        ]

        main()

        mock_fetch.assert_called_once()
        mock_download.assert_called_once()

    @patch('cli.download_data')
    @patch('cli.fetch_data_list')
    @patch('cli.load_usgs_config')
    @patch('os.makedirs')
    @patch('sys.argv', ['cli.py', '--aoi', '-84.5', '33.6', '-84.4', '33.7',
                         '--type', 'both', '--output-dir', '/tmp/test'])
    def test_main_both_types(self, mock_makedirs, mock_usgs_config,
                             mock_fetch, mock_download):
        """Test downloading both DEM and LiDAR data."""
        mock_usgs_config.return_value = {
            "dem": {"regular": {}},
            "lidar": {"regular": {}}
        }
        mock_fetch.side_effect = [
            [{"title": "Test DEM", "url": "https://example.com/test.tif"}],
            [{"title": "Test LiDAR", "url": "https://example.com/test.laz"}]
        ]

        main()

        # Should call fetch twice - once for DEM, once for LiDAR
        assert mock_fetch.call_count == 2
        mock_download.assert_called_once()

    @patch('cli.fetch_data_list')
    @patch('cli.load_usgs_config')
    @patch('os.makedirs')
    @patch('sys.argv', ['cli.py', '--aoi', '-84.5', '33.6', '-84.4', '33.7',
                         '--type', 'dem', '--output-dir', '/tmp/test'])
    def test_main_connection_error(self, mock_makedirs, mock_usgs_config,
                                   mock_fetch, capsys):
        """Test handling of connection errors."""
        mock_usgs_config.return_value = {"dem": {"regular": {}}}
        mock_fetch.side_effect = ConnectionFailedError("Connection failed")

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Failed to connect to USGS API" in captured.out

    @patch('cli.fetch_data_list')
    @patch('cli.load_usgs_config')
    @patch('os.makedirs')
    @patch('sys.argv', ['cli.py', '--aoi', '-84.5', '33.6', '-84.4', '33.7',
                         '--type', 'dem', '--output-dir', '/tmp/test'])
    def test_main_timeout_error(self, mock_makedirs, mock_usgs_config,
                                mock_fetch, capsys):
        """Test handling of API timeout errors."""
        mock_usgs_config.return_value = {"dem": {"regular": {}}}
        mock_fetch.side_effect = APITimeoutError("Request timed out")

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "timed out" in captured.out

    @patch('cli.fetch_data_list')
    @patch('cli.load_usgs_config')
    @patch('os.makedirs')
    @patch('sys.argv', ['cli.py', '--aoi', '-84.5', '33.6', '-84.4', '33.7',
                         '--type', 'dem', '--output-dir', '/tmp/test'])
    def test_main_no_datasets_found(self, mock_makedirs, mock_usgs_config,
                                    mock_fetch, capsys):
        """Test behavior when no datasets are found."""
        mock_usgs_config.return_value = {"dem": {"regular": {}}}
        mock_fetch.return_value = []  # Empty list

        main()

        captured = capsys.readouterr()
        assert "No datasets found" in captured.out

    @patch('cli.load_usgs_config')
    @patch('os.makedirs')
    @patch('sys.argv', ['cli.py', '--aoi', '-84.5', '33.6', '-84.4', '33.7',
                         '--type', 'dem', '--output-dir', '/tmp/test'])
    def test_main_output_dir_creation_error(self, mock_makedirs, mock_usgs_config, capsys):
        """Test handling of output directory creation errors."""
        mock_usgs_config.return_value = {"dem": {"regular": {}}}
        mock_makedirs.side_effect = OSError("Permission denied")

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Could not create output directory" in captured.out

    @patch('cli.download_data')
    @patch('cli.fetch_data_list')
    @patch('cli.load_usgs_config')
    @patch('os.makedirs')
    @patch('sys.argv', ['cli.py', '--aoi', '-84.5', '33.6', '-84.4', '33.7',
                         '--type', 'dem', '--output-dir', '/tmp/test'])
    def test_main_download_error(self, mock_makedirs, mock_usgs_config,
                                 mock_fetch, mock_download, capsys):
        """Test handling of errors during download."""
        mock_usgs_config.return_value = {"dem": {"regular": {}}}
        mock_fetch.return_value = [
            {"title": "Test DEM", "url": "https://example.com/test.tif"}
        ]
        mock_download.side_effect = USGSDataToolError("Download failed")

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error during download" in captured.out

    @patch('cli.download_data')
    @patch('cli.fetch_data_list')
    @patch('cli.load_usgs_config')
    @patch('cli.load_config')
    @patch('os.makedirs')
    @patch('sys.argv', ['cli.py', '--config', '/path/to/config.json'])
    def test_main_with_config_file(self, mock_makedirs, mock_load_config,
                                   mock_usgs_config, mock_fetch, mock_download):
        """Test main function using a config file."""
        mock_load_config.return_value = {
            'aoi': [-84.5, 33.6, -84.4, 33.7],
            'type': 'dem',
            'output_dir': '/tmp/config_test'
        }
        mock_usgs_config.return_value = {"dem": {"regular": {}}}
        mock_fetch.return_value = [
            {"title": "Test DEM", "url": "https://example.com/test.tif"}
        ]

        main()

        mock_load_config.assert_called_once_with('/path/to/config.json')
        mock_download.assert_called_once()
