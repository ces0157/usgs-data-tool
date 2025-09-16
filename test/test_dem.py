import os
import pytest
import sys
from unittest.mock import patch, call
from dem.dem_tools import merge_dem  # replace 'your_module' with actual module name
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


def test_merge_dem_keep_files_true(sample_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    merge_dem(sample_files, keep_files=True)

    after_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    for folder in sample_files:
        if(before_counts[folder] != 1):
            assert after_counts[folder] == before_counts[folder] + 1
            assert "merged.tif" in os.listdir(folder)
        else:
            assert after_counts[folder] == 1
            assert "merged.tif" not in os.listdir(folder)

    


def test_merge_dem_keep_files_false(sample_files):
        before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}
        merge_dem(sample_files, keep_files=False)

        after_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

        for folder in sample_files:
            assert after_counts[folder] == 1
            if(before_counts[folder] != 1):
                assert "merged.tif" in os.listdir(folder)
            else:
                assert "merged.tif" not in os.listdir(folder)



        



# def test_merge_dem_keep_files_true():
#         current_dir = os.path.dirname(os.path.abspath(__file__))
#         dem_test_dir = current_dir + "/test_dem"
        
#         folders = [os.path.join(dem_test_dir, f) for f in os.listdir(dem_test_dir) if os.path.isdir(os.path.join(dem_test_dir, f))]
        
#         project_files = dict()
#         before_counts = dict()
#         for folder in folders:
#             files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
#             project_files[folder] = files
#             before_counts[folder] = len(files)
        
#         merge_dem(project_files, keep_files=True)

#         # merged.tif should be created in each folder
#         after_counts = dict()
#         for folder in folders:
#             new_files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
#             after_counts[folder] = len(new_files)

#         for folder in project_files:
#             if(before_counts[folder] != 1):
#                 assert after_counts[folder] == before_counts[folder] + 1
#                 assert "merged.tif" in os.listdir(folder)
#                 #remove file from testing
#                 os.remove(folder + "/merged.tif")
#             else:
#                 assert after_counts[folder] == 1
#                 assert "merged.tif" not in os.listdir(folder)



# def test_merge_dem_keep_files_false():
#     current_dir = os.path.dirname(os.path.abspath(__file__))
#     dem_test_dir = current_dir + "/test_dem"
        
#     folders = [os.path.join(dem_test_dir, f) for f in os.listdir(dem_test_dir) if os.path.isdir(os.path.join(dem_test_dir, f))]
        
#     project_files = dict()
#     before_counts = dict()
#     for folder in folders:
#         files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
#         project_files[folder] = files
#         before_counts[folder] = len(files)
        
#     merge_dem(project_files, keep_files=False)

#     # merged.tif should be created in each folder
#     after_counts = dict()
#     for folder in folders:
#         new_files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
#         after_counts[folder] = len(new_files)

    
#     for folder in project_files:
#         if(before_counts[folder] != 1):
#             assert after_counts[folder] != before_counts[folder]
#             assert "merged.tif" in os.listdir(folder)
#         else:
#             assert "merged.tif" not in os.listdir(folder)
#         assert after_counts[folder] == 1
        
        