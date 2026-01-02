import os
import sys
import json
import pytest
from unittest.mock import patch, Mock
import requests

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_helpers.fetch_files import fetch_datasets, fetch_data_list
from exceptions import (
    ConnectionFailedError,
    APITimeoutError,
    InvalidResponseError,
    MissingConfigKeyError
)


def test_fetch_datasets_regular_dem_length():
    """
    Test the data returned in specifc bounding box matches
    expected USGS output
    """
    
    dataset_name = "Digital Elevation Model (DEM) 1 meter"
    dataset_format = "GeoTIFF"

    bbox = (-84.45688, 33.62848, -84.40212, 33.65607)

    data = fetch_datasets(dataset_name, dataset_format, bbox)
    assert len(data) == 4


def test_fetch_datasets_seamless_dem_length():
    """
    Test the data returned in specifc bounding box matches
    expected USGS output
    """

    dataset_name = "Seamless 1-meter DEM (Limited Availability)"
    dataset_format = "GeoTIFF"

    bbox = (-84.45688, 33.62848, -84.40212, 33.65607)

    data = fetch_datasets(dataset_name, dataset_format, bbox)
    assert len(data) == 0


def test_fetch_datasets_lidar_length():
    """
    Test the data returned in specifc bounding box matches
    expected USGS output
    """
    
    dataset_name = "Lidar Point Cloud (LPC)"
    dataset_format = "LAS,LAZ"

    bbox = (-84.45688, 33.62848, -84.40212, 33.65607)

    data = fetch_datasets(dataset_name, dataset_format, bbox)
    assert len(data) == 50


def test_fetch_data_list_dem_regular():
    dataset_spec = "regular"
    dataset_type = "dem"
    dataset_name = "Digital Elevation Model (DEM) 1 meter"
    dataset_format = "GeoTIFF"
    
    usgs_data = {dataset_type: {dataset_spec: 
                {"usgs_name": dataset_name, "usgs_data_format": dataset_format}}}

    bbox = (-84.45688, 33.62848, -84.40212, 33.65607)

    data = fetch_data_list(bbox, dataset_type, usgs_data, dataset_spec)
    assert len(data) == 4
    

def test_fetch_data_list_dem_seamless():
    dataset_spec = "seamless"
    dataset_type = "dem"
    dataset_name = "Seamless 1-meter DEM (Limited Availability)"
    dataset_format = "GeoTIFF"
    
    usgs_data = {dataset_type: {dataset_spec: 
                {"usgs_name": dataset_name, "usgs_data_format": dataset_format}}}

    bbox = (-84.45688, 33.62848, -84.40212, 33.65607)

    data = fetch_data_list(bbox, dataset_type, usgs_data, dataset_spec)
    assert len(data) == 0


def test_fetch_data_list_lidar():
    dataset_spec = "regular"
    dataset_type = "dem"
    dataset_name = "Lidar Point Cloud (LPC)"
    dataset_format = "LAS,LAZ"

    usgs_data = {dataset_type: {dataset_spec:
                {"usgs_name": dataset_name, "usgs_data_format": dataset_format}}}

    bbox = (-84.45688, 33.62848, -84.40212, 33.65607)

    data = fetch_data_list(bbox, dataset_type, usgs_data, dataset_spec)
    assert len(data) == 50


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestFetchDatasetsErrorHandling:
    """Tests for error handling in fetch_datasets function."""

    @patch('data_helpers.fetch_files.requests.get')
    def test_connection_error(self, mock_get):
        """Test handling of connection errors."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(ConnectionFailedError):
            fetch_datasets("test", "GeoTIFF", (-84, 33, -83, 34))

    @patch('data_helpers.fetch_files.requests.get')
    def test_timeout_error(self, mock_get):
        """Test handling of timeout errors."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(APITimeoutError):
            fetch_datasets("test", "GeoTIFF", (-84, 33, -83, 34))

    @patch('data_helpers.fetch_files.requests.get')
    def test_invalid_json_response(self, mock_get):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response

        with pytest.raises(InvalidResponseError):
            fetch_datasets("test", "GeoTIFF", (-84, 33, -83, 34))

    @patch('data_helpers.fetch_files.requests.get')
    def test_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(ConnectionFailedError):
            fetch_datasets("test", "GeoTIFF", (-84, 33, -83, 34))

    @patch('data_helpers.fetch_files.requests.get')
    def test_empty_items_response(self, mock_get):
        """Test handling of empty items in response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        result = fetch_datasets("test", "GeoTIFF", (-84, 33, -83, 34))
        assert result == []


class TestFetchDataListErrorHandling:
    """Tests for error handling in fetch_data_list function."""

    def test_missing_type_key(self, sample_usgs_data):
        """Test handling of missing type key in config."""
        with pytest.raises(MissingConfigKeyError):
            fetch_data_list((-84, 33, -83, 34), "invalid_type", sample_usgs_data)

    def test_missing_spec_key(self, sample_usgs_data):
        """Test handling of missing spec key in config."""
        with pytest.raises(MissingConfigKeyError):
            fetch_data_list((-84, 33, -83, 34), "dem", sample_usgs_data, "invalid_spec")

    def test_missing_usgs_name_key(self):
        """Test handling of missing usgs_name key."""
        usgs_data = {"dem": {"regular": {"usgs_data_format": "GeoTIFF"}}}
        with pytest.raises(MissingConfigKeyError):
            fetch_data_list((-84, 33, -83, 34), "dem", usgs_data, "regular")

    def test_missing_usgs_data_format_key(self):
        """Test handling of missing usgs_data_format key."""
        usgs_data = {"dem": {"regular": {"usgs_name": "DEM"}}}
        with pytest.raises(MissingConfigKeyError):
            fetch_data_list((-84, 33, -83, 34), "dem", usgs_data, "regular")

