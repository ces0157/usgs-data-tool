import os
import pytest
import sys
from unittest.mock import patch, call
from dem.dem_tools import merge_dem, convert_tiff  # replace 'your_module' with actual module name
from osgeo import gdal, osr



def create_dummy_tif(path, width=10, height=10):
    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(str(path), width, height, 1, gdal.GDT_Byte)
    
    # set geotransform (origin at 0,0 and pixel size 1x1)
    dataset.SetGeoTransform((0, 1, 0, 0, 0, -1))

    # set spatial reference system (WGS84)
    srs = osr.SpatialReference()
    srs.SetWellKnownGeogCS("WGS84")
    dataset.SetProjection(srs.ExportToWkt())

    # fill band with dummy values
    band = dataset.GetRasterBand(1)
    band.Fill(100)  # constant gray value
    
    dataset.FlushCache()
    dataset = None  # closes the file

@pytest.fixture
def sample_files(tmp_path):
    folder1 = tmp_path / "folder1"
    folder1.mkdir()
    f1 = folder1 / "a.tif"
    f2 = folder1 / "b.tif"

    create_dummy_tif(f1)
    create_dummy_tif(f2)

    folder2 = tmp_path / "folder2"
    folder2.mkdir()
    f3 = folder2 / "c.tif"

    create_dummy_tif(f3)

    return {
        str(folder1): [str(f1), str(f2)],
        str(folder2): [str(f3)],
    }


def test_merge_dem_tiff_keep_files_true(sample_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    merge_dem(sample_files, keep_files=True, file_type="tif")

    after_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    for folder in sample_files:
        if(before_counts[folder] != 1):
            assert after_counts[folder] == before_counts[folder] + 1
            assert "merged.tif" in os.listdir(folder)
        else:
            assert after_counts[folder] == 1
            assert "merged.tif" not in os.listdir(folder)

def test_merge_dem_tiff_keep_files_false(sample_files):
        before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}
        merge_dem(sample_files, keep_files=False, file_type="tif")

        after_counts = {folder: len(os.listdir(folder)) for folder in sample_files}
        for folder in sample_files:
            assert after_counts[folder] == 1
            if(before_counts[folder] != 1):
                assert "merged.tif" in os.listdir(folder)
            else:
                assert "merged.tif" not in os.listdir(folder)


def test_merge_dem_png_keep_files_true(sample_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    merge_dem(sample_files, keep_files=True, file_type="png")

    after_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    for folder in sample_files:
        if(before_counts[folder] != 1):
            #file will contain (.png and xml) for every tiff and there will be a merged.tiff file
            assert after_counts[folder] == before_counts[folder] + 3
            assert "merged.tif" in os.listdir(folder)
            assert "merged.png" in os.listdir(folder)
        else:
            assert after_counts[folder] == 1
            assert "merged.tif" not in os.listdir(folder)
            assert "merged.r16" not in os.listdir(folder)


def test_merge_dem_png_keep_files_false(sample_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}
    merge_dem(sample_files, keep_files=False, file_type="png")

    after_counts = {folder: len(os.listdir(folder)) for folder in sample_files}
    for folder in sample_files:
        assert after_counts[folder] == 1
        if(before_counts[folder] != 1):
            assert "merged.png" in os.listdir(folder)
        else:
            assert "merged.png" not in os.listdir(folder)

def test_merge_dem_raw_keep_files_true(sample_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    merge_dem(sample_files, keep_files=True, file_type="r16")

    after_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    for folder in sample_files:
        if(before_counts[folder] != 1):
            #file will contain (.raw and hdr, and xml) for every tiff and there will be a merged.tiff file
            assert after_counts[folder] == before_counts[folder] + 4
            assert "merged.tif" in os.listdir(folder)
            assert "merged.r16" in os.listdir(folder)
        else:
            assert after_counts[folder] == 1
            assert "merged.tif" not in os.listdir(folder)
            assert "merged.r16" not in os.listdir(folder)

def test_merge_dem_raw_keep_files_false(sample_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    merge_dem(sample_files, keep_files=False, file_type="r16")

    after_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    for folder in sample_files:
        assert after_counts[folder] == 1
        if(before_counts[folder] != 1):
            assert "merged.r16" in os.listdir(folder)
        else:
            assert "merged.r16" not in os.listdir(folder)


@pytest.mark.parametrize("new_file_type,precision,expected_ext", [
    ("png", None, ".png"),
    ("png", 16, ".png"),
    ("r16", None, ".r16"),
])
def test_convert_tiff_creates_expected_amount(sample_files, new_file_type, precision, expected_ext):
    count = 0
    for folder, files in sample_files.items():
        for i, tif in enumerate(files, start=1):
            #print(folder)
            #print(tif)
            output_file = folder + "/test" + str(i) + "." + new_file_type
            convert_tiff(
                input_dir=folder,
                file=tif,
                new_file_type=new_file_type,
                output_file= output_file,
                precision=precision
            )
            count += 1

    # Assert: number of converted files equals number of inputs
    for folder, files in sample_files.items():
        converted = [f for f in os.listdir(folder) if f.endswith(expected_ext)]
        assert len(converted) == len(files)