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


#TODO: Whole testing refactor to use pytest paramterize
#merge files within the project direcotires
def test_merge_dem_tiff_keep_files_true_project(sample_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    merge_dem(sample_files, keep_files=True, file_type="tif", merge_method="project")

    after_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    for folder in sample_files:
        if(before_counts[folder] != 1):
            assert after_counts[folder] == before_counts[folder] + 1
            assert "merged.tif" in os.listdir(folder)
        else:
            assert after_counts[folder] == 1
            assert "merged.tif" not in os.listdir(folder)

#delte all files within the project directory except merged (or single files)
def test_merge_dem_tiff_keep_files_false_project(sample_files):
        before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}
        
        merge_dem(sample_files, keep_files=False, file_type="tif", merge_method="project")

        after_counts = {folder: len(os.listdir(folder)) for folder in sample_files}
        
        for folder in sample_files:
            assert after_counts[folder] == 1
            if(before_counts[folder] != 1):
                assert "merged.tif" in os.listdir(folder)
            else:
                assert "merged.tif" not in os.listdir(folder)


#merge all files into a single tiff in the top level dem directory 
def test_merge_dem_tiff_keep_files_true_all(sample_files):
    
    #get the top level directory
    for key in sample_files:
        dem_dir = key.rsplit("/", 1)[0]
        break

    before_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    before_counts_dem = len(os.listdir(dem_dir))
    
    merge_dem(sample_files, keep_files=True, file_type="tif", merge_method="all")

    after_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    after_counts_dem = len(os.listdir(dem_dir))
    
    #nothing was merged in the project directory
    for folder in sample_files:
        if(before_counts_project[folder] != 1):
            assert after_counts_project[folder] == before_counts_project[folder]
        else:
            assert after_counts_project[folder] == 1
        assert "merged.tif" not in os.listdir(folder)

    
    #merged in the top-level directory
    assert "merged.tif" in os.listdir(dem_dir)
    assert after_counts_dem == before_counts_dem + 1

#remove all files or subfolders that are not in the top level dem directory
def test_merge_dem_tiff_keep_files_false_all(sample_files):
    #get the top level directory
    for key in sample_files:
        dem_dir = key.rsplit("/", 1)[0]
        break

    merge_dem(sample_files, keep_files=False, file_type="tif", merge_method="all")

    after_counts_dem = len(os.listdir(dem_dir))
    
    #merged in the top-level directory
    assert "merged.tif" in os.listdir(dem_dir)
    assert after_counts_dem == 1


#merge projects and top level
def test_merge_dem_tiff_keep_files_true_both(sample_files):
    #get the top level directory
    for key in sample_files:
        dem_dir = key.rsplit("/", 1)[0]
        break

    before_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    before_counts_dem = len(os.listdir(dem_dir))
    
    merge_dem(sample_files, keep_files=True, file_type="tif", merge_method="both")

    after_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    after_counts_dem = len(os.listdir(dem_dir))
    
    #nothing was merged in the project directory
    for folder in sample_files:
        if(before_counts_project[folder] != 1):
            assert after_counts_project[folder] == before_counts_project[folder] + 1
            assert "merged.tif" in os.listdir(folder)   
        else:
            assert after_counts_project[folder] == 1
            assert "merged.tif" not in os.listdir(folder)

    
    #merged in the top-level directory
    assert "merged.tif" in os.listdir(dem_dir)
    assert after_counts_dem == before_counts_dem + 1

#merge projects but remove everything that is not merged
def test_merge_dem_tiff_keep_files_false_both(sample_files):
    for key in sample_files:
        dem_dir = key.rsplit("/", 1)[0]
        break

    before_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    before_counts_dem = len(os.listdir(dem_dir))
    
    merge_dem(sample_files, keep_files=False, file_type="tif", merge_method="both")

    after_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    after_counts_dem = len(os.listdir(dem_dir))
        
    for folder in sample_files:
        assert after_counts_project[folder] == 1
        if(before_counts_project[folder] != 1):
            assert "merged.tif" in os.listdir(folder)
        else:
            assert "merged.tif" not in os.listdir(folder)

    assert "merged.tif" in os.listdir(dem_dir)
    assert after_counts_dem == before_counts_dem + 1
    

#merge only png in the project directory
def test_merge_dem_png_keep_files_true_project(sample_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    merge_dem(sample_files, keep_files=True, file_type="png", merge_method="project")

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
            assert "merged.png" not in os.listdir(folder)

#delete all files exelcuding png in the project directory
def test_merge_dem_png_keep_files_false_project(sample_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}
    merge_dem(sample_files, keep_files=False, file_type="png", merge_method="project")

    after_counts = {folder: len(os.listdir(folder)) for folder in sample_files}
    for folder in sample_files:
        assert after_counts[folder] == 1
        if(before_counts[folder] != 1):
            assert "merged.png" in os.listdir(folder)
        else:
            assert "merged.png" not in os.listdir(folder)


#keep all files in the top level directory
def test_merge_dem_png_keep_files_true_all(sample_files):
    
    #get the top level directory
    for key in sample_files:
        dem_dir = key.rsplit("/", 1)[0]
        break

    before_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    before_counts_dem = len(os.listdir(dem_dir))
    
    merge_dem(sample_files, keep_files=True, file_type="png", merge_method="all")

    after_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    after_counts_dem = len(os.listdir(dem_dir))
    
    #nothing was merged in the project directory
    for folder in sample_files:
        if(before_counts_project[folder] != 1):
            assert after_counts_project[folder] == before_counts_project[folder]
        else:
            assert after_counts_project[folder] == 1
        assert "merged.tif" not in os.listdir(folder)
    
    assert "merged.tif" in os.listdir(dem_dir)
    assert "merged.png" in os.listdir(dem_dir)
    
    #merged tif, merged png, and xml file should be located here
    assert after_counts_dem == before_counts_dem + 3

#remove all files except merged files in the top level directory
def test_merge_dem_png_keep_files_false_all(sample_files):
    #get the top level directory
    for key in sample_files:
        dem_dir = key.rsplit("/", 1)[0]
        break

    merge_dem(sample_files, keep_files=False, file_type="png", merge_method="all")

    after_counts_dem = len(os.listdir(dem_dir))
    
    #merged in the top-level directory
    assert "merged.png" in os.listdir(dem_dir)
    assert "merged.tif" not in os.listdir(dem_dir)
    assert after_counts_dem == 1


def test_merge_dem_png_keep_files_true_both(sample_files):
    #get the top level directory
    for key in sample_files:
        dem_dir = key.rsplit("/", 1)[0]
        break

    before_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    before_counts_dem = len(os.listdir(dem_dir))
    
    merge_dem(sample_files, keep_files=True, file_type="png", merge_method="both")

    after_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    after_counts_dem = len(os.listdir(dem_dir))
    
    #nothing was merged in the project directory
    for folder in sample_files:
        print(folder)
        if(before_counts_project[folder] != 1):
            assert after_counts_project[folder] == before_counts_project[folder] + 3
            assert "merged.png" in os.listdir(folder)
            assert "merged.tif" in os.listdir(folder)   
        else:
            assert after_counts_project[folder] == 1
            assert "merged.png" not in os.listdir(folder)
            assert "merged.tif" not in os.listdir(folder)

    
    #merged in the top-level directory
    assert "merged.tif" in os.listdir(dem_dir)
    assert "merged.png" in os.listdir(dem_dir)
    assert after_counts_dem == before_counts_dem + 3


def test_merge_dem_png_keep_files_false_both(sample_files):
    for key in sample_files:
        dem_dir = key.rsplit("/", 1)[0]
        break

    before_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    before_counts_dem = len(os.listdir(dem_dir))
    
    merge_dem(sample_files, keep_files=False, file_type="png", merge_method="both")

    after_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    after_counts_dem = len(os.listdir(dem_dir))
        
    for folder in sample_files:
        assert after_counts_project[folder] == 1
        if(before_counts_project[folder] != 1):
            assert "merged.png" in os.listdir(folder)
        else:
            assert "merged.tif" not in os.listdir(folder)

    assert "merged.png" in os.listdir(dem_dir)
    assert after_counts_dem == before_counts_dem + 1



def test_merge_dem_raw_keep_files_true_project(sample_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    merge_dem(sample_files, keep_files=True, file_type="r16", merge_method="project")

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


def test_merge_dem_raw_keep_files_false_project(sample_files):
    before_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    merge_dem(sample_files, keep_files=False, file_type="r16", merge_method="project")

    after_counts = {folder: len(os.listdir(folder)) for folder in sample_files}

    for folder in sample_files:
        assert after_counts[folder] == 1
        if(before_counts[folder] != 1):
            assert "merged.r16" in os.listdir(folder)
        else:
            assert "merged.r16" not in os.listdir(folder)


def test_merge_dem_raw_keep_files_true_all(sample_files):
    
    #get the top level directory
    for key in sample_files:
        dem_dir = key.rsplit("/", 1)[0]
        break

    before_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    before_counts_dem = len(os.listdir(dem_dir))
    
    merge_dem(sample_files, keep_files=True, file_type="r16", merge_method="all")

    after_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    after_counts_dem = len(os.listdir(dem_dir))
    
    #nothing was merged in the project directory
    for folder in sample_files:
        if(before_counts_project[folder] != 1):
            assert after_counts_project[folder] == before_counts_project[folder]
        else:
            assert after_counts_project[folder] == 1
        assert "merged.tif" not in os.listdir(folder)
    
    assert "merged.tif" in os.listdir(dem_dir)
    assert "merged.r16" in os.listdir(dem_dir)
    
    #merged tif, merged png, xml, and hdr file should be located here
    assert after_counts_dem == before_counts_dem + 4


def test_merge_dem_raw_keep_files_false_all(sample_files):
    #get the top level directory
    for key in sample_files:
        dem_dir = key.rsplit("/", 1)[0]
        break

    merge_dem(sample_files, keep_files=False, file_type="r16", merge_method="all")

    after_counts_dem = len(os.listdir(dem_dir))
    
    #merged in the top-level directory
    assert "merged.r16" in os.listdir(dem_dir)
    assert "merged.tif" not in os.listdir(dem_dir)
    assert after_counts_dem == 1


def test_merge_dem_raw_keep_files_true_both(sample_files):
    #get the top level directory
    for key in sample_files:
        dem_dir = key.rsplit("/", 1)[0]
        break

    before_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    before_counts_dem = len(os.listdir(dem_dir))
    
    merge_dem(sample_files, keep_files=True, file_type="r16", merge_method="both")

    after_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    after_counts_dem = len(os.listdir(dem_dir))
    
    #nothing was merged in the project directory
    for folder in sample_files:
        print(folder)
        if(before_counts_project[folder] != 1):
            assert after_counts_project[folder] == before_counts_project[folder] + 4
            assert "merged.r16" in os.listdir(folder)
            assert "merged.tif" in os.listdir(folder)   
        else:
            assert after_counts_project[folder] == 1
            assert "merged.r16" not in os.listdir(folder)
            assert "merged.tif" not in os.listdir(folder)

    
    #merged in the top-level directory
    assert "merged.tif" in os.listdir(dem_dir)
    assert "merged.r16" in os.listdir(dem_dir)
    assert after_counts_dem == before_counts_dem + 4


def test_merge_dem_png_keep_files_false_both(sample_files):
    for key in sample_files:
        dem_dir = key.rsplit("/", 1)[0]
        break

    before_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    before_counts_dem = len(os.listdir(dem_dir))
    
    merge_dem(sample_files, keep_files=False, file_type="r16", merge_method="both")

    after_counts_project = {folder: len(os.listdir(folder)) for folder in sample_files}
    after_counts_dem = len(os.listdir(dem_dir))
        
    for folder in sample_files:
        assert after_counts_project[folder] == 1
        if(before_counts_project[folder] != 1):
            assert "merged.r16" in os.listdir(folder)
        else:
            assert "merged.tif" not in os.listdir(folder)

    assert "merged.r16" in os.listdir(dem_dir)
    assert after_counts_dem == before_counts_dem + 1


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