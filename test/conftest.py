"""Shared test fixtures and utilities for USGS Data Tool tests."""

import pytest
import json
import tempfile
import shutil
import os
import sys
from pathlib import Path
from unittest.mock import Mock

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def sample_bbox():
    """Standard bounding box for testing (Atlanta area)."""
    return (-84.45688, 33.62848, -84.40212, 33.65607)


@pytest.fixture
def sample_usgs_data():
    """Sample USGS configuration data."""
    return {
        "lidar": {
            "regular": {
                "usgs_name": "Lidar Point Cloud (LPC)",
                "usgs_data_format": "LAS,LAZ"
            }
        },
        "dem": {
            "regular": {
                "usgs_name": "Digital Elevation Model (DEM) 1 meter",
                "usgs_data_format": "GeoTIFF"
            },
            "seamless": {
                "usgs_name": "Seamless 1-meter DEM (Limited Availability)",
                "usgs_data_format": "GeoTIFF"
            }
        }
    }


@pytest.fixture
def mock_args():
    """Create mock CLI arguments."""
    args = Mock()
    args.type = "dem"
    args.aoi = (-84.45688, 33.62848, -84.40212, 33.65607)
    args.output_dir = "/tmp/test_output"
    args.dem_output = "tif"
    args.dem_merge = "merge-keep"
    args.dem_merge_method = "all"
    args.dem_filter_type = "none"
    args.dem_resolution = "auto"
    args.dem_spec = "regular"
    args.png_precision = 16
    args.merge_lidar = "merge-keep"
    args.lidar_filter = "no-filter"
    args.lidar_reproject = "none"
    return args


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    dirpath = tempfile.mkdtemp()
    yield dirpath
    # Cleanup after test
    shutil.rmtree(dirpath, ignore_errors=True)


@pytest.fixture
def sample_download_info():
    """Sample download information returned by API."""
    return [
        {
            'title': 'USGS 1 Meter DEM',
            'publicationDate': '2023-01-01',
            'format': 'GeoTIFF',
            'url': 'https://example.com/Projects/TestProject/dem_file.tif'
        }
    ]


@pytest.fixture
def sample_lidar_download_info():
    """Sample LiDAR download information returned by API."""
    return [
        {
            'title': 'Lidar Point Cloud',
            'publicationDate': '2023-01-01',
            'format': 'LAZ',
            'url': 'https://example.com/Projects/LidarProject/lidar_file.laz'
        }
    ]


def create_dummy_tif(path, width=10, height=10, epsg=4326):
    """
    Create a dummy GeoTIFF file for testing.

    Args:
        path: Path to create the file.
        width: Raster width in pixels.
        height: Raster height in pixels.
        epsg: EPSG code for the CRS.

    Returns:
        Path to the created file.
    """
    try:
        from osgeo import gdal, osr
        import numpy as np

        driver = gdal.GetDriverByName("GTiff")
        dataset = driver.Create(str(path), width, height, 1, gdal.GDT_Float32)

        dataset.SetGeoTransform((0, 1, 0, 0, 0, -1))

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(epsg)
        dataset.SetProjection(srs.ExportToWkt())

        band = dataset.GetRasterBand(1)
        data = np.random.rand(height, width).astype(np.float32) * 100
        band.WriteArray(data)

        dataset.FlushCache()
        dataset = None
        return path
    except ImportError:
        pytest.skip("GDAL not available for creating test files")


@pytest.fixture
def sample_tif_file(temp_dir):
    """Create a sample GeoTIFF file in a temp directory."""
    tif_path = os.path.join(temp_dir, "test.tif")
    return create_dummy_tif(tif_path)


@pytest.fixture
def sample_tif_files(temp_dir):
    """Create multiple sample GeoTIFF files organized by project."""
    project_dir = os.path.join(temp_dir, "dem", "TestProject")
    os.makedirs(project_dir, exist_ok=True)

    files = {}
    files[project_dir] = []
    for i in range(3):
        tif_path = os.path.join(project_dir, f"test_{i}.tif")
        create_dummy_tif(tif_path)
        files[project_dir].append(tif_path)

    return files
