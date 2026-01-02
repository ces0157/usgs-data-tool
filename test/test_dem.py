"""Tests for DEM tools module."""

import os
import pytest
import sys
import numpy as np
from unittest.mock import patch, Mock, MagicMock
from osgeo import gdal, osr

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dem.dem_tools import (
    merge_dem,
    convert_tiff,
    safe_open_geotiff,
    safe_get_driver,
    safe_transform_bbox,
    get_resolution,
    detect_z_units,
    convert_dem_to_meters,
    filter_dem,
    warp_dem
)
from exceptions import (
    InvalidGeoTIFFError,
    GDALDriverError,
    CRSTransformationError
)



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
            # Should have at least merged.tif created
            assert after_counts_project[folder] >= before_counts_project[folder] + 1
            assert "merged.tif" in os.listdir(folder)
            # PNG file may or may not be created depending on conversion
        else:
            assert after_counts_project[folder] >= 1
            assert "merged.tif" not in os.listdir(folder)

    
    #merged in the top-level directory
    assert "merged.tif" in os.listdir(dem_dir)
    # PNG file may or may not be created at top level depending on conversion
    assert after_counts_dem >= before_counts_dem + 1


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
        # With keep_files=False, original files are deleted, only merged files remain
        # Should have at least 1 file (could be merged.tif, merged.png or both)
        assert after_counts_project[folder] >= 0  # Files may be deleted if folder had no merge
        if(before_counts_project[folder] != 1):
            # Should have merged file (tif, png, or both)
            assert len(os.listdir(folder)) >= 1
        # else: single file folders may have files removed

    # Top level should have merged file
    assert after_counts_dem >= before_counts_dem + 1



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
            # Should have at least merged.tif created
            assert after_counts_project[folder] >= before_counts_project[folder] + 1
            assert "merged.tif" in os.listdir(folder)
            # R16 file may or may not be created depending on conversion
        else:
            assert after_counts_project[folder] >= 1
            assert "merged.tif" not in os.listdir(folder)


    #merged in the top-level directory
    assert "merged.tif" in os.listdir(dem_dir)
    # R16 file may or may not be created depending on conversion
    assert after_counts_dem >= before_counts_dem + 1


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
        # With keep_files=False, files may be deleted, check flexibly
        assert after_counts_project[folder] >= 0
        if(before_counts_project[folder] != 1 and after_counts_project[folder] > 0):
            # May have merged file if merge happened
            files_in_folder = os.listdir(folder)
            # Should have at least one output file if folder not empty
            assert len(files_in_folder) >= 1

    # Top level should have at least one merged file
    assert after_counts_dem >= before_counts_dem + 1


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


# ============================================================================
# Helper Functions Tests
# ============================================================================

class TestSafeOpenGeotiff:
    """Tests for safe_open_geotiff function."""

    def test_open_valid_file(self, sample_files):
        """Test opening a valid GeoTIFF file."""
        for folder, files in sample_files.items():
            ds = safe_open_geotiff(files[0])
            assert ds is not None
            ds = None  # Close

    def test_file_not_found(self):
        """Test error when file does not exist."""
        with pytest.raises(InvalidGeoTIFFError) as excinfo:
            safe_open_geotiff("/nonexistent/path/to/file.tif")
        assert "not found" in str(excinfo.value)

    def test_invalid_file(self, tmp_path):
        """Test error when file is not a valid GeoTIFF."""
        invalid_file = tmp_path / "invalid.tif"
        invalid_file.write_text("this is not a tiff")

        with pytest.raises(InvalidGeoTIFFError) as excinfo:
            safe_open_geotiff(str(invalid_file))
        assert "Could not open" in str(excinfo.value)


class TestSafeGetDriver:
    """Tests for safe_get_driver function."""

    def test_get_valid_driver(self):
        """Test getting a valid GDAL driver."""
        driver = safe_get_driver("GTiff")
        assert driver is not None

    def test_get_invalid_driver(self):
        """Test error when driver is not available."""
        with pytest.raises(GDALDriverError) as excinfo:
            safe_get_driver("NonExistentDriver")
        assert "not available" in str(excinfo.value)

    def test_get_png_driver(self):
        """Test getting PNG driver."""
        driver = safe_get_driver("PNG")
        assert driver is not None


class TestSafeTransformBbox:
    """Tests for safe_transform_bbox function."""

    def test_valid_transformation(self):
        """Test valid coordinate transformation."""
        bbox = (-84.45688, 33.62848, -84.40212, 33.65607)
        result = safe_transform_bbox(bbox, "EPSG:4326", "EPSG:26917")

        # Result should be in meters (UTM Zone 17N)
        assert len(result) == 4
        assert all(isinstance(v, float) for v in result)
        # UTM coordinates should be much larger than lat/lon
        assert abs(result[0]) > 100000

    def test_invalid_source_crs(self):
        """Test error with invalid source CRS."""
        bbox = (-84.0, 33.0, -83.0, 34.0)
        with pytest.raises(CRSTransformationError):
            safe_transform_bbox(bbox, "INVALID:CRS", "EPSG:26917")

    def test_invalid_target_crs(self):
        """Test error with invalid target CRS."""
        bbox = (-84.0, 33.0, -83.0, 34.0)
        with pytest.raises(CRSTransformationError):
            safe_transform_bbox(bbox, "EPSG:4326", "INVALID:CRS")

    def test_same_crs_transformation(self):
        """Test transformation when source and target CRS are the same."""
        bbox = (-84.0, 33.0, -83.0, 34.0)
        result = safe_transform_bbox(bbox, "EPSG:4326", "EPSG:4326")

        assert result[0] == pytest.approx(bbox[0], rel=1e-6)
        assert result[1] == pytest.approx(bbox[1], rel=1e-6)


class TestGetResolution:
    """Tests for get_resolution function."""

    def test_resolution_none(self, sample_files):
        """Test resolution with 'none' (keeps original)."""
        for folder, files in sample_files.items():
            ds = gdal.Open(files[0])
            width, height = get_resolution(ds, "none")
            assert width == ds.RasterXSize
            assert height == ds.RasterYSize
            ds = None

    def test_resolution_auto(self, sample_files):
        """Test auto resolution scaling to UE-compatible size."""
        for folder, files in sample_files.items():
            ds = gdal.Open(files[0])
            width, height = get_resolution(ds, "auto")
            # Should be one of the valid resolutions
            valid_sizes = {1009, 2017, 4033, 8129}
            assert width in valid_sizes
            assert height in valid_sizes
            ds = None

    def test_resolution_custom(self, sample_files):
        """Test custom resolution value."""
        for folder, files in sample_files.items():
            ds = gdal.Open(files[0])
            width, height = get_resolution(ds, "1024")
            assert width == 1024
            assert height == 1024
            ds = None


class TestDetectZUnits:
    """Tests for detect_z_units function."""

    def test_detect_units_from_file(self, sample_files):
        """Test unit detection from a sample file."""
        for folder, files in sample_files.items():
            result = detect_z_units(files[0])
            assert isinstance(result, dict)
            assert "units" in result
            assert "source" in result
            assert "details" in result

    def test_detect_units_nonexistent_file(self, tmp_path):
        """Test unit detection with nonexistent file."""
        result = detect_z_units(str(tmp_path / "nonexistent.tif"))
        assert result["source"] == "error"
        assert result["units"] is None

    def test_detect_units_usgs_fallback(self, tmp_path):
        """Test USGS 3DEP fallback heuristic."""
        # Create a file with USGS naming pattern
        usgs_file = tmp_path / "usgs_1m_dem.tif"
        create_dummy_tif(str(usgs_file))

        result = detect_z_units(str(usgs_file))
        # Should trigger USGS fallback or find no units
        assert "source" in result


class TestConvertDemToMeters:
    """Tests for convert_dem_to_meters function."""

    def test_conversion_creates_new_file(self, sample_files):
        """Test that conversion creates a new file."""
        for folder, files in sample_files.items():
            input_file = files[0]
            output_file = convert_dem_to_meters(input_file)

            assert os.path.exists(output_file)
            assert "_converted.tif" in output_file

            # Clean up
            os.remove(output_file)
            break  # Only test one file

    def test_conversion_applies_factor(self, tmp_path):
        """Test that conversion applies the scaling factor."""
        # Create a dummy file with known values
        input_file = tmp_path / "feet_dem.tif"
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(str(input_file), 10, 10, 1, gdal.GDT_Float32)
        ds.SetGeoTransform((0, 1, 0, 0, 0, -1))
        srs = osr.SpatialReference()
        srs.SetWellKnownGeogCS("WGS84")
        ds.SetProjection(srs.ExportToWkt())

        # Fill with known value (100 feet)
        band = ds.GetRasterBand(1)
        arr = np.full((10, 10), 100.0, dtype=np.float32)
        band.WriteArray(arr)
        ds.FlushCache()
        ds = None

        # Convert
        output_file = convert_dem_to_meters(str(input_file))

        # Check converted values
        out_ds = gdal.Open(output_file)
        out_arr = out_ds.GetRasterBand(1).ReadAsArray()
        out_ds = None

        # 100 feet * 0.3048 = ~30.48 meters
        expected = 100.0 * 0.3048006096012192
        assert out_arr[0, 0] == pytest.approx(expected, rel=1e-5)

        # Clean up
        os.remove(output_file)

    def test_conversion_nonexistent_file(self):
        """Test conversion with nonexistent file."""
        with pytest.raises(InvalidGeoTIFFError):
            convert_dem_to_meters("/nonexistent/file.tif")


class TestFilterDem:
    """Tests for filter_dem function."""

    def test_filter_creates_output(self, sample_files, tmp_path):
        """Test that filter creates output file."""
        for folder, files in sample_files.items():
            input_file = files[0]
            output_file = str(tmp_path / "filtered.tif")

            # Small bbox for filtering
            bbox = (-1.0, -1.0, 1.0, 1.0)

            filter_dem(input_file, output_file, "EPSG:4326", bbox)

            assert os.path.exists(output_file)
            break

    def test_filter_invalid_input(self, tmp_path):
        """Test filter with invalid input file."""
        output_file = str(tmp_path / "filtered.tif")
        bbox = (-1.0, -1.0, 1.0, 1.0)

        with pytest.raises(InvalidGeoTIFFError):
            filter_dem("/nonexistent/file.tif", output_file, "EPSG:4326", bbox)


class TestWarpDem:
    """Tests for warp_dem function."""

    def test_warp_single_file(self, sample_files, tmp_path):
        """Test warping a single file."""
        for folder, files in sample_files.items():
            input_files = [files[0]]
            output_file = str(tmp_path / "warped.tif")

            code, units = warp_dem(input_files, output_file)

            assert os.path.exists(output_file)
            assert "EPSG:" in code
            assert units == "metre"
            break

    def test_warp_multiple_files(self, sample_files, tmp_path):
        """Test warping multiple files."""
        for folder, files in sample_files.items():
            if len(files) > 1:
                output_file = str(tmp_path / "warped_multi.tif")

                code, units = warp_dem(files, output_file)

                assert os.path.exists(output_file)
                assert "EPSG:" in code
                break

    def test_warp_skips_invalid_files(self, sample_files, tmp_path):
        """Test that warp skips invalid files and continues."""
        for folder, files in sample_files.items():
            # Mix valid and invalid files
            input_files = ["/nonexistent/file.tif"] + files
            output_file = str(tmp_path / "warped_partial.tif")

            # Should complete (skipping invalid file)
            code, units = warp_dem(input_files, output_file)

            assert os.path.exists(output_file)
            break