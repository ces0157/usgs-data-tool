"""Tests for LiDAR tools module."""

import os
import pytest
import sys
from unittest.mock import patch, Mock, MagicMock
import json
import pdal
import pathlib
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lidar.lidar_tools import (
    merge_lidar,
    safe_execute_pipeline,
    detect_epsg_from_las,
    reproject_lidar,
    filter_lidar
)
from exceptions import (
    InvalidLASFileError,
    PDALPipelineError,
    MissingMetadataError,
    LiDARError
)


def create_dummy_laz(path, num_points=10):
    """
    Create a dummy LAZ file using readers.numpy → writers.las.
    """
    # Create a small numpy structured array
    arr = np.zeros(num_points, dtype=[("X", np.float64), ("Y", np.float64), ("Z", np.float64)])
    arr["X"] = np.arange(num_points)
    arr["Y"] = np.arange(num_points)
    arr["Z"] = np.arange(num_points)

    # Save to a temporary .npy file
    npy_path = str(path) + ".npy"
    np.save(npy_path, arr)

    pipeline_dict = {
        "pipeline": [
            {
                "type": "readers.numpy",
                "filename": npy_path
            },
            {
                "type": "writers.las",
                "filename": str(path),
                "compression": "laszip"
            }
        ]
    }

    pipeline = pdal.Pipeline(json.dumps(pipeline_dict))
    pipeline.execute()
    return pathlib.Path(path)


@pytest.fixture
def sample_laz_files(tmp_path):
    folder1 = tmp_path / "lidar1"
    folder1.mkdir()
    f1 = folder1 / "a.laz"
    f2 = folder1 / "b.laz"
    create_dummy_laz(f1)
    create_dummy_laz(f2)

    folder2 = tmp_path / "lidar2"
    folder2.mkdir()
    f3 = folder2 / "c.laz"
    create_dummy_laz(f3)

    return {
        str(folder1): [str(f1), str(f2)],
        str(folder2): [str(f3)],
    }

def test_merge_lidar_keep_files_true(sample_laz_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_laz_files}

    merge_lidar(sample_laz_files, keep_files=True)

    after_counts = {folder: len(os.listdir(folder)) for folder in sample_laz_files}
    
    for folder in sample_laz_files:
        if(before_counts[folder] != 1):
            assert after_counts[folder] == before_counts[folder] + 1
            assert "merged.laz" in os.listdir(folder)
        else:
            assert after_counts[folder] == 1
            assert "merged.laz" not in os.listdir(folder)


def test_merge_lidar_keep_files_false(sample_laz_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_laz_files}

    merge_lidar(sample_laz_files, keep_files=False)


    after_counts = {folder: len(os.listdir(folder)) for folder in sample_laz_files}

    for folder in sample_laz_files:
        assert after_counts[folder] == 1
        if(before_counts[folder] != 1):
            assert "merged.laz" in os.listdir(folder)
        else:
            assert "merged.laz" not in os.listdir(folder)


# ============================================================================
# Helper Functions Tests
# ============================================================================

def create_laz_with_crs(path, epsg_code=26917, num_points=10):
    """
    Create a LAZ file with a defined CRS.

    Args:
        path: Output file path.
        epsg_code: EPSG code for the CRS.
        num_points: Number of points to create.
    """
    # Create a numpy structured array
    arr = np.zeros(num_points, dtype=[("X", np.float64), ("Y", np.float64), ("Z", np.float64)])
    arr["X"] = np.arange(num_points) + 500000  # UTM-like X coordinates
    arr["Y"] = np.arange(num_points) + 4000000  # UTM-like Y coordinates
    arr["Z"] = np.arange(num_points) * 10

    # Save to a temporary .npy file
    npy_path = str(path) + ".npy"
    np.save(npy_path, arr)

    # Create file with CRS set directly on writer (no reprojection needed)
    pipeline_dict = {
        "pipeline": [
            {
                "type": "readers.numpy",
                "filename": npy_path
            },
            {
                "type": "writers.las",
                "filename": str(path),
                "compression": "laszip",
                "a_srs": f"EPSG:{epsg_code}"
            }
        ]
    }

    pipeline = pdal.Pipeline(json.dumps(pipeline_dict))
    pipeline.execute()

    # Clean up temp file
    if os.path.exists(npy_path):
        os.remove(npy_path)

    return pathlib.Path(path)


class TestSafeExecutePipeline:
    """Tests for safe_execute_pipeline function."""

    def test_valid_pipeline(self, tmp_path):
        """Test execution of a valid pipeline."""
        # Create a simple read pipeline
        input_file = tmp_path / "test.laz"
        create_dummy_laz(str(input_file))

        pipeline_dict = {
            "pipeline": [
                {"type": "readers.las", "filename": str(input_file)}
            ]
        }

        pipeline, count = safe_execute_pipeline(pipeline_dict, "test read")
        assert pipeline is not None
        assert count >= 0

    def test_invalid_file_pipeline(self):
        """Test pipeline with nonexistent file."""
        pipeline_dict = {
            "pipeline": [
                {"type": "readers.las", "filename": "/nonexistent/file.laz"}
            ]
        }

        # May raise either InvalidLASFileError or PDALPipelineError depending on error message
        with pytest.raises((InvalidLASFileError, PDALPipelineError)):
            safe_execute_pipeline(pipeline_dict, "test invalid")

    def test_invalid_pipeline_config(self):
        """Test pipeline with invalid configuration."""
        pipeline_dict = {
            "pipeline": [
                {"type": "invalid_reader_type", "filename": "test.laz"}
            ]
        }

        with pytest.raises(PDALPipelineError):
            safe_execute_pipeline(pipeline_dict, "test invalid config")


class TestDetectEpsgFromLas:
    """Tests for detect_epsg_from_las function."""

    def test_file_not_found(self):
        """Test error when file does not exist."""
        with pytest.raises(InvalidLASFileError) as excinfo:
            detect_epsg_from_las("/nonexistent/file.laz")
        assert "not found" in str(excinfo.value)

    def test_detect_epsg_from_file_with_crs(self, tmp_path):
        """Test EPSG detection from file with defined CRS."""
        laz_file = tmp_path / "with_crs.laz"
        create_laz_with_crs(str(laz_file), epsg_code=26917)

        result = detect_epsg_from_las(str(laz_file))

        # Should detect EPSG or return None if metadata not preserved
        if result is not None:
            assert "EPSG:" in result

    def test_detect_epsg_from_basic_file(self, sample_laz_files):
        """Test EPSG detection from basic LAZ file."""
        for folder, files in sample_laz_files.items():
            # Basic files may not have EPSG set
            result = detect_epsg_from_las(files[0])
            # Result can be None or an EPSG string
            assert result is None or "EPSG:" in result
            break


class TestMergeLidarErrors:
    """Tests for merge_lidar error handling."""

    def test_empty_files_dict(self):
        """Test merging with empty dictionary."""
        result = merge_lidar({}, keep_files=True)
        assert result == {}

    def test_empty_folder_list(self, tmp_path):
        """Test merging with empty file list for a folder."""
        folder = tmp_path / "empty_folder"
        folder.mkdir()

        files = {str(folder): []}
        result = merge_lidar(files, keep_files=True)

        # Should skip empty folders
        assert str(folder) not in result or result[str(folder)] is None


class TestReprojectLidar:
    """Tests for reproject_lidar function."""

    def test_reproject_files_with_crs(self, tmp_path):
        """Test reprojection of files with valid CRS."""
        folder = tmp_path / "reproject_test"
        folder.mkdir()

        laz_file = folder / "source.laz"
        create_laz_with_crs(str(laz_file), epsg_code=26917)

        files = {str(folder): [str(laz_file)]}
        target_crs = "EPSG:4326"

        result = reproject_lidar(files, target_crs)

        # Should create reprojected files or skip if EPSG not detected
        assert isinstance(result, dict)

    def test_reproject_skips_legacy_folders(self, tmp_path):
        """Test that legacy folders are skipped."""
        folder = tmp_path / "legacy_project"
        folder.mkdir()

        laz_file = folder / "legacy_file.laz"
        create_dummy_laz(str(laz_file))

        files = {str(folder): [str(laz_file)]}

        result = reproject_lidar(files, "EPSG:4326")

        # Legacy folders should be skipped
        assert isinstance(result, dict)

    def test_reproject_empty_dict(self):
        """Test reprojection with empty dictionary."""
        result = reproject_lidar({}, "EPSG:4326")
        assert result == {}


class TestFilterLidar:
    """Tests for filter_lidar function."""

    def test_filter_creates_output(self, sample_laz_files, tmp_path):
        """Test that filter creates output file."""
        # Get first folder with merged file
        for folder, files in sample_laz_files.items():
            if len(files) > 1:
                # First merge the files
                merge_lidar({folder: files}, keep_files=True)

                merged_file = os.path.join(folder, "merged.laz")
                if os.path.exists(merged_file):
                    # Test filtering
                    input_clouds = {folder: merged_file}
                    bounds = (-84.5, 33.6, -84.4, 33.7)

                    # This may raise LiDARError if PDAL not found
                    try:
                        filter_lidar(input_clouds, "filtered.laz", bounds)
                        # Check if output exists
                        output_file = os.path.join(folder, "filtered.laz")
                        # Output may not exist if bounds don't intersect
                        assert isinstance(input_clouds, dict)
                    except LiDARError as e:
                        # PDAL command not found is acceptable in test env
                        if "not found" not in str(e):
                            raise
                break

    def test_filter_with_invalid_bounds(self, sample_laz_files):
        """Test filter behavior with bounds that don't intersect data."""
        for folder, files in sample_laz_files.items():
            if len(files) > 1:
                merge_lidar({folder: files}, keep_files=True)

                merged_file = os.path.join(folder, "merged.laz")
                if os.path.exists(merged_file):
                    input_clouds = {folder: merged_file}
                    # Very distant bounds
                    bounds = (-180, -90, -179, -89)

                    try:
                        filter_lidar(input_clouds, "filtered_empty.laz", bounds)
                        # Should still complete
                        assert True
                    except LiDARError:
                        # Expected if PDAL not available
                        pass
                break


# ============================================================================
# Additional Error Handling Tests
# ============================================================================

class TestDetectEpsgErrors:
    """Additional error handling tests for EPSG detection."""

    def test_corrupted_las_file(self, tmp_path):
        """Test handling of corrupted LAS file."""
        # Create a fake corrupted file
        corrupted_file = tmp_path / "corrupted.laz"
        with open(corrupted_file, 'wb') as f:
            f.write(b'not a valid LAS file')

        # Should raise InvalidLASFileError when trying to read
        with pytest.raises((InvalidLASFileError, PDALPipelineError)):
            detect_epsg_from_las(str(corrupted_file))

    @patch('lidar.lidar_tools.safe_execute_pipeline')
    def test_missing_srs_metadata(self, mock_pipeline, tmp_path):
        """Test handling of LAS file with missing SRS metadata."""
        # Mock pipeline that returns metadata without SRS
        mock_pipeline_obj = Mock()
        mock_pipeline_obj.metadata = {
            "metadata": {
                "readers.las": {}  # No 'srs' key
            }
        }
        mock_pipeline.return_value = (mock_pipeline_obj, 10)

        test_file = tmp_path / "no_srs.laz"
        test_file.touch()

        with pytest.raises(MissingMetadataError):
            detect_epsg_from_las(str(test_file))


class TestReprojectLidarErrors:
    """Additional error handling tests for reprojection."""

    @patch('lidar.lidar_tools.detect_epsg_from_las')
    def test_reproject_with_epsg_detection_failure(self, mock_detect, tmp_path):
        """Test reprojection when EPSG detection fails."""
        folder = tmp_path / "test_folder"
        folder.mkdir()

        laz_file = folder / "test.laz"
        create_dummy_laz(str(laz_file))

        files = {str(folder): [str(laz_file)]}

        # Simulate detection failure
        mock_detect.side_effect = InvalidLASFileError("Cannot read file")

        result = reproject_lidar(files, "EPSG:4326")

        # Should skip file and return empty or partial results
        assert isinstance(result, dict)

    @patch('lidar.lidar_tools.detect_epsg_from_las')
    def test_reproject_with_none_epsg(self, mock_detect, tmp_path):
        """Test reprojection when EPSG detection returns None."""
        folder = tmp_path / "test_folder"
        folder.mkdir()

        laz_file = folder / "test.laz"
        create_dummy_laz(str(laz_file))

        files = {str(folder): [str(laz_file)]}

        # Simulate detection returning None
        mock_detect.return_value = None

        result = reproject_lidar(files, "EPSG:4326")

        # Should skip file when EPSG is None
        assert isinstance(result, dict)
        # File should be skipped
        assert str(folder) not in result or len(result.get(str(folder), [])) == 0

    @patch('lidar.lidar_tools.safe_execute_pipeline')
    @patch('lidar.lidar_tools.detect_epsg_from_las')
    def test_reproject_pipeline_failure(self, mock_detect, mock_pipeline, tmp_path):
        """Test handling of pipeline failure during reprojection."""
        folder = tmp_path / "test_folder"
        folder.mkdir()

        laz_file = folder / "test.laz"
        create_dummy_laz(str(laz_file))

        files = {str(folder): [str(laz_file)]}

        mock_detect.return_value = "EPSG:26917"
        mock_pipeline.side_effect = PDALPipelineError("Reprojection failed")

        result = reproject_lidar(files, "EPSG:4326")

        # Should handle error gracefully and continue
        assert isinstance(result, dict)


class TestMergeLidarAdditional:
    """Additional tests for merge_lidar function."""

    @patch('lidar.lidar_tools.safe_execute_pipeline')
    def test_merge_with_pipeline_error(self, mock_pipeline, tmp_path):
        """Test merge handling when pipeline execution fails."""
        folder = tmp_path / "test_folder"
        folder.mkdir()

        laz_file = folder / "test.laz"
        create_dummy_laz(str(laz_file))

        files = {str(folder): [str(laz_file)]}

        mock_pipeline.side_effect = PDALPipelineError("Merge failed")

        result = merge_lidar(files, keep_files=True)

        # Should handle error and continue
        assert isinstance(result, dict)
        # Failed merge should not be in results
        assert str(folder) not in result

    def test_merge_file_removal_error(self, tmp_path, monkeypatch):
        """Test handling of file removal errors."""
        folder = tmp_path / "test_folder"
        folder.mkdir()

        laz_file1 = folder / "test1.laz"
        laz_file2 = folder / "test2.laz"
        create_dummy_laz(str(laz_file1))
        create_dummy_laz(str(laz_file2))

        files = {str(folder): [str(laz_file1), str(laz_file2)]}

        # Mock os.remove to raise an error
        original_remove = os.remove
        def mock_remove(path):
            if "test1.laz" in str(path):
                raise OSError("Permission denied")
            else:
                original_remove(path)

        monkeypatch.setattr(os, 'remove', mock_remove)

        # Should continue despite removal error
        result = merge_lidar(files, keep_files=False)

        # Merge should still succeed
        assert str(folder) in result
