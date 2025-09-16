import os
import pytest
import sys
from unittest.mock import patch, call
from lidar.lidar_tools import merge_lidar # replace 'your_module' with actual module name
import json
import pdal
import pathlib
import numpy as np


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
