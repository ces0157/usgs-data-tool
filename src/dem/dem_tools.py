from osgeo import gdal, osr
import numpy as np
from PIL import Image
import os
import glob
import shutil
import math
from pyproj import Transformer
from pyproj.exceptions import CRSError
import sys
from pathlib import Path

from exceptions import (
    InvalidGeoTIFFError,
    GDALDriverError,
    CRSTransformationError,
    MergeError,
    DEMError
)
from utils import get_files_to_remove, safe_remove_files

VALID_RESOLUTIONS = {1009, 2017, 4033, 8129}  # UE-supported sizes (power of 2 + 1)
US_SURVEY_FOOT_TO_M = 0.3048006096012192
INTL_FOOT_TO_M = 0.3048


def safe_open_geotiff(path: str, mode=gdal.GA_ReadOnly):
    """
    Safely open a GeoTIFF file with error handling.

    Args:
        path: Path to the GeoTIFF file.
        mode: GDAL access mode (default: read-only).

    Returns:
        GDAL Dataset object.

    Raises:
        InvalidGeoTIFFError: If file cannot be opened.
    """
    if not os.path.exists(path):
        raise InvalidGeoTIFFError(f"GeoTIFF file not found: {path}")

    ds = gdal.Open(path, mode)
    if ds is None:
        raise InvalidGeoTIFFError(f"Could not open GeoTIFF file: {path}")
    return ds


def safe_get_driver(driver_name: str):
    """
    Get GDAL driver with error handling.

    Args:
        driver_name: Name of the GDAL driver.

    Returns:
        GDAL Driver object.

    Raises:
        GDALDriverError: If driver is not available.
    """
    driver = gdal.GetDriverByName(driver_name)
    if driver is None:
        raise GDALDriverError(f"GDAL driver not available: {driver_name}")
    return driver


def safe_transform_bbox(bbox: tuple, from_crs: str, to_crs: str) -> tuple:
    """
    Transform bounding box coordinates with error handling.

    Args:
        bbox: (minLon, minLat, maxLon, maxLat) tuple.
        from_crs: Source CRS (e.g., "EPSG:4326").
        to_crs: Target CRS (e.g., "EPSG:26917").

    Returns:
        Transformed (minX, minY, maxX, maxY) tuple.

    Raises:
        CRSTransformationError: If transformation fails.
    """
    try:
        transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
        minX, minY = transformer.transform(bbox[0], bbox[1])
        maxX, maxY = transformer.transform(bbox[2], bbox[3])
        return (minX, minY, maxX, maxY)
    except CRSError as e:
        raise CRSTransformationError(f"Failed to transform coordinates from {from_crs} to {to_crs}: {e}")
    except Exception as e:
        raise CRSTransformationError(f"Coordinate transformation failed: {e}")

def convert_tiff(file: str, new_file_type: str, output_file: str, precision=None, scale_resolution="none"):
    """
    Convert GeoTIFF files into either a RAW (r16) or PNG.

    Args:
        file: File to be converted.
        new_file_type: New file type to be saved (png or r16).
        output_file: Name of the new filename to save.
        precision: Precision for PNG file (8 or 16). RAW files always use 16.
        scale_resolution: Resolution scaling option.

    Raises:
        InvalidGeoTIFFError: If input file cannot be opened.
        DEMError: If conversion fails.
    """
    src_ds = safe_open_geotiff(file)

    band = src_ds.GetRasterBand(1)
    min_val, max_val = band.ComputeRasterMinMax(True)
    
    vertical_range = (max_val - min_val)
    #print(f"Vertical range of {file}: {str(vertical_range)}")

    #print(f"precision:  {precision}")


    width, height = get_resolution(src_ds, scale_resolution)
    #print(width, height)
        
    
    if new_file_type == "png":
        
        if precision == 16:
            output_precision = gdal.GDT_UInt16
            max_normalization = 65535
        else:
            output_precision = gdal.GDT_Byte
            max_normalization = 255

        #convert to png
        gdal.Translate(
            output_file,
            src_ds,
            format="PNG",        # Equivalent to -of PNG
            outputType=output_precision,  # Equivalent to -ot Byte
            resampleAlg="cubic",
            scaleParams=[[min_val, max_val, 0, max_normalization]],
        )
    
    elif new_file_type == "r16":
        #Valid resolutions that we can import into unreal engine
        #output_raw = input_dir + "/" + output_filename + ".r16"
        gdal.Translate(
            output_file,
            src_ds,
            format="ENVI",             # RAW-like format with .hdr file
            outputType=gdal.GDT_UInt16,
            resampleAlg="cubic",
            scaleParams=[[min_val, max_val, 0, 65535]],
        )

#TODO REFACTOR REDUDANT CALLS
def merge_dem(files: dict, keep_files: bool, file_type: str, merge_method: str, precision=None, filter = False, bbox=None, scale_resolution='none'):
    """
    Merge DEM files together into a single GeoTIFF file

    Args:
    files: dictonary where the keys are folders and the filenames are the value
    keep_files: Weather to keep the original files afterwards
    merge_method: do we merge files in just projects, across projects, or both (options)
    file_type: how to save the merged output (tif, png, raw)
    """

    if merge_method == "project" or merge_method == "both":
        for key in files:
            if len(files[key]) == 1:
                print("Only 1 file recongized ... no merging required")
                if filter:
                    output_filtered = key + "/heightmap1_filtered.tif"
                    output_warped = key + "/heightmap1_warped.tif"
                    
                    code, units = warp_dem(files[key], output_warped)
                    filter_dem(output_warped, output_filtered, code, bbox, scale_resolution)
                    os.remove(output_warped)
                    if file_type != "tif":
                        output_file = key + "/heightmap1_filtered." + file_type
                        convert_tiff(output_filtered, file_type, output_file, precision, scale_resolution)

                    print_unreal_units(output_filtered)
                
                continue
            
            #create an output GTIFF
            #TODO: TEST filter for just project
            #this is done so we wait to rescale unitl after all files have been merged. We want to combine all at native resoltuion before crooping
            #and rescaling
            if merge_method != "both":
                code = merge(key, files[key], file_type, precision, filter, bbox, scale_resolution)
            
            #no resizing,cropping, or conversion will occur until after everything is combined.
            else:
                code = merge(key, files[key], "tif", precision)

        #we just need to merge the merged tiff files into a singular file
        #TODO: TEST the case for both
        if merge_method == "both":
            merged_files = []
            for key in files:
                #check that more than one file exists
                if len(files[key]) != 1:
                    merged_files.append(key + "/merged.tif")
                else:
                    merged_files.append(files[key][0])
                
                #get the output directory for digital elevation maps 
                output_dir = key.rsplit("/", 1)[0]
            
            #print(merged_files)
            #merge all project files together (i.e merged.tif from project1, project2, etc.)
            code = merge(output_dir, merged_files, file_type, precision, filter, bbox, scale_resolution)
            
            #now that we combined all merged files, ensure the merged files in each project are rescaled to target aoi and converted
            #this should only happen if a merged file exists (aka when there are more htan two files to a project)
            if len(files[key]) != 1:
                for file in merged_files:
                    print(f"Starting rescaling of {file} ")
                    print(code)
                    project_output_dir = file.rsplit("/", 1)[0]
                    translate_and_replace(project_output_dir, file, file_type, code, "metre",precision, filter, bbox, scale_resolution)
                

     
    elif merge_method == "all":
        all_files = []
        for key in files:
            all_files = all_files + files[key]
            #get the output directory for digital elevation maps 
            output_dir = key.rsplit("/", 1)[0]
        
        code = merge(output_dir, all_files, file_type, precision, filter, bbox, scale_resolution)    
   
    #remove all files that are not merged files
    if not keep_files:
        remove_files(files, file_type, merge_method)

    return code




def merge(output_dir: str, files, file_type: str, precision=None, filter = False, bbox=None, scale_resolution="none"):
    """
   

    Does the actual merging and conversion if nesseccary

    Args:
    output_dir: where we are saving too
    files: all the files that we are going to merge/convert to lat long
    file_type: how to save the merged output (tif, png, raw)
    precision: the precision that we save too 
    filter: crop the DEM to specified area
    bbox: the area of interest to filter too
    scale_resoltuion: how we should go about scaling.
    """
    #TODO FIX RESOLUTION PROBLEMS
    
    #creates the merged file
    output_file_tif = output_dir + "/merged.tif"
    
    print(f"merging files in {output_dir}")
    #merges all the files together
    code, units = warp_dem(files, output_file_tif)

    translate_and_replace(output_dir, output_file_tif, file_type, code, units, precision, filter, bbox, scale_resolution)

    return code

def warp_dem(input_files, out_file: str):
    """
    Merge and warp DEM files to a common CRS.

    Args:
        input_files: An array of files to be merged/changed.
        out_file: Name of the output file.

    Returns:
        Tuple of (EPSG code string, units string).

    Raises:
        InvalidGeoTIFFError: If input files cannot be opened.
        MergeError: If merge operation fails.
    """
    codes = set()
    merged_files = []
    for i in range(len(input_files)):
        try:
            ds = safe_open_geotiff(input_files[i])
        except InvalidGeoTIFFError as e:
            print(f"Warning: Skipping file {input_files[i]}: {e}")
            continue

        srs = ds.GetSpatialRef()  # returns osr.SpatialReference or None

        if srs is None:
            print("No CRS found.")
        else:
            srs.AutoIdentifyEPSG()
            code = srs.GetAuthorityCode(None)
            name = srs.GetAuthorityName(None)

            codes.add(code)
        
        z_units = detect_z_units(input_files[i])

        ##WE MADE NEED TO TAKE INTO ACCOUNT OTHER CONVERISON
        if z_units['units'] == "US survey foot":
            print(f"note this dataset elevation is in {z_units['units']}, converting elevation to metre to standarizde merging ...") 
            converted = convert_dem_to_meters(input_files[i])
            merged_files.append(converted)
        else:
            merged_files.append(input_files[i])
        

    
    if(len(codes) == 1):
        codes = list(codes)
        #units = list(units)
        print(f"All files being merged are part of the same UTM zone: {codes[0]} and z merging will happen automatically ...")

    #TODO:Add a projection technique to deal with this problem
    else:
        print("Not all files about to be merged are part of the same UTM and some distortion could occur if combined. Do you wish to continue?: ")
        user_response = input("Do you want to proceed? (yes/no): ")
        if user_response.lower() == "yes":
            print("Proceeding as requested.")
        elif user_response.lower() == "no":
            print("Operation cancelled.")
            sys.exit("Stopping merge")

    print(merged_files)
    gdal.Warp(
        destNameOrDestDS=out_file,
        srcDSOrSrcDSTab=merged_files,
        format="GTiff",
        resampleAlg="cubic"
    )

    #TODO FIX this return since we don't need it anymore
    return f"EPSG:{codes[0]}", "metre"    






def filter_dem(input_tif: str, out_file: str, code: str, bbox=None, scale_resolution="none"):
    """
    Crop down the DEM file to the target location.

    Args:
        input_tif: The tiff we are modifying/changing/saving.
        out_file: The name we should use.
        code: The EPSG code we are using for the project.
        bbox: The area of interest to filter to.
        scale_resolution: Should we rescale this file.

    Raises:
        InvalidGeoTIFFError: If input file cannot be opened.
        CRSTransformationError: If coordinate transformation fails.
    """
    src_ds = safe_open_geotiff(input_tif)
    width, height = get_resolution(src_ds, scale_resolution)

    minX, minY, maxX, maxY = safe_transform_bbox(bbox, "EPSG:4326", code)
   
   
    gdal.Translate(
        out_file,
        input_tif,
        projWin=(minX, maxY, maxX, minY), # minX, maxY, maxX, minY
        width=width,
        height=height,
        resampleAlg="cubic"
    )

    
   


def translate_and_replace(output_dir:str, input_tif:str , file_type:str, code: str, units="metre", precision=None, filter = False, bbox=None, scale_resolution="none"):
    """
    Translates, converts, and replaces files if need be
    
    output_dir: where we are saving too
    input_tif: the tiff we are modifying/saving
    file_type: how to save the merged output (tif, png, raw)
    precision: the precision that we save too 
    filter: crop the DEM to specified area
    bbox: the area of interest (in lat long) to filter too
    code: the authority code the dataset(s) are in
    """
    #TODO: REFACTOR reduant code between filtered_dem and this
    tmp_file = output_dir + "/temp.tif"
    src_ds = gdal.Open(input_tif)
    width, height = get_resolution(src_ds, scale_resolution)
    
    if filter:
        output_filtered = output_dir + "/merged_filtered.tif"
        filter_dem(input_tif, output_filtered, code, bbox, scale_resolution)

    gdal.Translate(
        tmp_file,
        input_tif,
        width=width,
        height=height,
        resampleAlg="cubic"
    )

    os.replace(tmp_file, input_tif)

    if file_type != "tif":
        output_file = output_dir + "/" + "merged." + file_type 
        convert_tiff(input_tif, file_type, output_file, precision, scale_resolution)
        if filter:
            output_file = output_dir + "/" + "merged_filtered." + file_type
            convert_tiff(output_dir + "/merged_filtered.tif", file_type, output_file, precision, scale_resolution)


    print_unreal_units(input_tif, units)
    if filter:
        print_unreal_units(output_dir + "/merged_filtered.tif", units)

     


#TODO REFACTOR REDUDANT CODE
def remove_files(files: dict, file_type: str, merge_method: str) -> None:
    """
    Remove unnecessary files after merging.

    Args:
        files: Dictionary where keys are folders and values are lists of filenames.
        file_type: File type to keep (tif, png, r16).
        merge_method: Merge strategy (project, all, or both).
    """
    dem_dir = None

    if merge_method == "project" or merge_method == "both":
        for key in files:
            if len(files[key]) != 1:
                # Remove files that don't match the merged file pattern
                files_to_remove = get_files_to_remove(key, file_type, keep_merged=True)
                safe_remove_files(files_to_remove)
            dem_dir = key.rsplit("/", 1)[0]

        # Remove top level directory contents for "both" method
        if merge_method == "both" and dem_dir:
            files_to_remove = get_files_to_remove(dem_dir, file_type, keep_merged=True)
            safe_remove_files(files_to_remove)

    elif merge_method == "all":
        for key in files:
            if os.path.exists(key):
                try:
                    shutil.rmtree(key)
                except OSError as e:
                    print(f"Warning: Could not remove directory {key}: {e}")
            dem_dir = key.rsplit("/", 1)[0]

        # Remove top level directory contents
        if dem_dir:
            files_to_remove = get_files_to_remove(dem_dir, file_type, keep_merged=True)
            safe_remove_files(files_to_remove)

    
#TODO MAKE resolution unit tests 
def get_resolution(src_ds, resolution: str):
    """
    Check the resolution of GeoTIFF file and change if required

    Args:
        src_ds: GeoTiff file
        resolution: the type resoltuion we need to change too (if required)
        
    """
    if resolution != "auto" and resolution != "none":
        print(f"Changing Resoltuion to {resolution} x {resolution}")
        return int(resolution), int(resolution)
        
    
    else:
        width = src_ds.RasterXSize
        height = src_ds.RasterYSize

        if resolution == "none":
            print(f"Keeping resoltuion the same: {width} x {height}")
            return width, height

        resolution_value = None
        min_resolution = math.inf
        for number in VALID_RESOLUTIONS:
            resolution = math.sqrt((number - width) ** 2 + (number - height) **2)
            if resolution < min_resolution:
                resolution_value = number
                min_resolution = resolution
        
        print(f"Auto scaling resolution to {resolution_value} x {resolution_value}")
        return int(resolution_value), int(resolution_value)



#not all digital elevation maps share the same z units so we are checking
#what the value is
def detect_z_units(path):
    ds = gdal.Open(path)
    if ds is None:
        return {"units": None, "source": "error", "details": "Could not open dataset"}

    # --- 1) Band-level unit metadata (most common when present)
    band = ds.GetRasterBand(1)
    unit = band.GetUnitType()  # returns "" if not set
    if unit:
        return {"units": unit, "source": "band", "details": "Band Unit Type metadata present"}

    # --- 2) Vertical CRS inside the SRS (VERT_CS / VERTCRS)
    wkt = ds.GetProjectionRef()
    if wkt:
        srs = osr.SpatialReference()
        srs.ImportFromWkt(wkt)

        # If it's a compound CRS, vertical part may be accessible
        if srs.IsCompound():
            vert = srs.GetVerticalCS()
            if vert:
                # unit name + conversion factor
                unit_name = vert.GetAttrValue("UNIT", 0)
                return {"units": unit_name, "source": "vertical_crs", "details": "Found VerticalCS in CRS"}

        # WKT2 vertical CRS sometimes not flagged as compound;
        # brute search for VERTCRS/VERT_CS and UNIT inside it.
        if "VERTCRS" in wkt or "VERT_CS" in wkt:
            # naive parse: look for UNIT right after vertical node
            # (good enough for most WKT)
            try:
                vert_srs = osr.SpatialReference()
                vert_srs.ImportFromWkt(wkt)
                unit_name = vert_srs.GetAttrValue("VERTCRS|CS|AXIS|UNIT", 0) \
                            or vert_srs.GetAttrValue("VERT_CS|UNIT", 0)
                if unit_name:
                    return {"units": unit_name, "source": "vertical_crs", "details": "Vertical CRS unit found in WKT"}
            except Exception:
                pass

    # --- 3) Fallback for known USGS 3DEP 1m DEM tiles
    # Heuristic: filename pattern + USGS 1M tile context
    name = (ds.GetDescription() or path).lower()
    if "usgs_1m" in name or "3dep" in name:
        # USGS standard elevation products in CONUS are meters/NAVD88
        print("Please note that we did not find explicit z units within these files, we will assume meters are being used, but take note if elevations are not matching expectation")
        return {
            "units": "metre",
            "source": "usgs_3dep_fallback",
            "details": "USGS 3DEP/1m DEM products use meters (NAVD88 in CONUS)"
        }

    return {"units": None, "source": "unknown", "details": "No unit metadata or vertical CRS found"}



def print_unreal_units(input_file, units="metre"):
    """
    Print Unreal Engine scale units for a DEM file.

    Args:
        input_file: Path to the GeoTIFF file.
        units: Units of the elevation data.
    """
    try:
        ds = safe_open_geotiff(input_file)
    except InvalidGeoTIFFError as e:
        print(f"Warning: Could not calculate UE units for {input_file}: {e}")
        return

    gt = ds.GetGeoTransform()


    pixel_width  = gt[1]
    pixel_height = abs(gt[5])

    x_scale = pixel_width * 100
    y_scale = pixel_height * 100


    band = ds.GetRasterBand(1)
    min_val, max_val = band.ComputeRasterMinMax(True)
    
    vertical_range = (max_val - min_val)
    z_scale = (vertical_range * 100) / 512

    print(f"UE x scale in cm: {x_scale} for {input_file}")
    print(f"UE y scale in cm: {y_scale} for {input_file}")
    print(f"UE z scale in cm: {z_scale} for {input_file}")



def convert_dem_to_meters(in_path, factor=US_SURVEY_FOOT_TO_M):
    """
    Convert DEM elevation values from feet to meters.

    Args:
        in_path: Path to input GeoTIFF file.
        factor: Conversion factor (default: US survey foot to meters).

    Returns:
        Path to the converted output file.

    Raises:
        InvalidGeoTIFFError: If input file cannot be opened.
        GDALDriverError: If GTiff driver is not available.
        DEMError: If conversion fails.
    """
    p = Path(in_path)
    name_no_ext = p.stem
    directory = Path(in_path).parent

    out_path = str(directory) + "/" + str(name_no_ext) + "_converted.tif"

    src = safe_open_geotiff(in_path)

    band = src.GetRasterBand(1)
    nodata = band.GetNoDataValue()

    # Read as float64 for safe scaling
    arr = band.ReadAsArray().astype(np.float64)

    # Apply scaling, preserving NoData
    if nodata is not None:
        mask = (arr == nodata)
        arr *= factor
        arr[mask] = nodata
    else:
        arr *= factor

    # Create output with same size/projection/geotransform
    driver = safe_get_driver("GTiff")
    # copy common creation options; tweak as needed
    options = [
        "TILED=YES",
        "COMPRESS=LZW",
        "PREDICTOR=3",
        "BIGTIFF=IF_SAFER"
    ]

    dst = driver.Create(
        out_path,
        src.RasterXSize,
        src.RasterYSize,
        1,
        gdal.GDT_Float32,
        options=options
    )

    dst.SetGeoTransform(src.GetGeoTransform())
    dst.SetProjection(src.GetProjection())

    out_band = dst.GetRasterBand(1)
    out_band.WriteArray(arr.astype(np.float32))

    if nodata is not None:
        out_band.SetNoDataValue(nodata)

    # Set vertical units metadata so gdalinfo shows Unit Type: metre
    out_band.SetUnitType("metre")

    out_band.FlushCache()
    dst.FlushCache()
    dst = None
    src = None

    print(f"Converted to meters -> {out_path}")
    return out_path







    

   