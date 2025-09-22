from osgeo import gdal
import numpy as np
from PIL import Image
import os
import glob
import shutil
import subprocess
import shutil


#TODO add this back in
#VALID_RESOLUTIONS = {1009, 2017, 4033, 8129}  # UE-supported sizes (power of 2 + 1)

def convert_tiff(file: str, new_file_type: str, output_file: str, precision=None):
    """
    Convert GeoTIFF files into either a RAW (r16) or PNG 

    Args:
        file: file to be replaced
        new_file_type: new file type to be saved (png or raw)
        output_filename: name of the new filename to save
        precision: precision in which to save a png file. RAW files will always default to 16
    """

    src_ds = gdal.Open(file)

    band = src_ds.GetRasterBand(1)
    min_val, max_val = band.ComputeRasterMinMax(True)
        
    
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
            scaleParams=[[min_val, max_val, 0, 65535]],
        )

def merge_dem(files: dict, keep_files: bool, file_type: str, merge_method: str, precision=None, filter = False, bbox=None):
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
                continue
            
            #create an output GTIFF
            #TODO: TEST filter for just project
            merge(key, files[key], file_type, precision)

        #we just need to merge the merged tiff files into a singular file
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
            #TODO: TEST filter for both
            merge(output_dir, merged_files, file_type, precision)
     
    elif merge_method == "all":
        all_files = []
        for key in files:
            all_files = all_files + files[key]
            #get the output directory for digital elevation maps 
            output_dir = key.rsplit("/", 1)[0]
        
        merge(output_dir, all_files, file_type, precision, filter, bbox)    
   
    #remove all files that are not merged files
    if not keep_files:
        remove_files(files, file_type, merge_method)


def merge(output_dir: str, files, file_type: str, precision=None, filter = False, bbox=None):
    """
    Args:

    Does the actual merging and conversion if nesseccary

    output_dir: where we are saving too
    files: all the files that we are going to merge
    file_type: how to save the merged output (tif, png, raw)
    precision: the precision that we save too 
    filter: crop the DEM to specified area
    bbox: the area of interest to filter too
    """

    output_file_tif = output_dir + "/merged.tif"
    gdal.Warp(
        destNameOrDestDS=output_file_tif,
        srcDSOrSrcDSTab=files,
        format="GTiff",
        dstSRS="EPSG:4326"
    )

    if filter:
        tmp_file = output_dir + "/filtered.tif"
        gdal.Translate(
            tmp_file,
            output_file_tif,
            projWin=(bbox[0], bbox[3], bbox[2], bbox[1]) # minX, maxY, maxX, minY
        )

        os.replace(tmp_file, output_file_tif)

    if file_type != "tif":
        output_file = output_dir + "/" + "merged." + file_type 
        convert_tiff(output_file_tif, file_type, output_file, precision)



#TODO REFACTOR REDUDANT CODE
def remove_files(files: str, file_type:str, merge_method: str):
    """
    Remove unesseccary files
    Args:
    files: dictonary where the keys are folders and the filenames are the value
    file_type: how to save the merged output (tif, png, raw)
    merge_method: do we merge files in just projects, across projects, or both (options)
    """
    if merge_method == "project" or merge_method == "both":
        for key in files:
            if len(files[key]) != 1:
                folder_contents = os.listdir(key)
                for i in range(0, len(folder_contents)):              
                    if folder_contents[i] != "merged." + file_type:
                        #print(key + "/" + folder_contents[i])
                        os.remove(key + "/" + folder_contents[i])
            dem_dir = key.rsplit("/", 1)[0]
        
        #remove top level directory contents
        if merge_method == "both":
            print(dem_dir)
            folder_contents = [f for f in os.listdir(dem_dir) if os.path.isfile(os.path.join(dem_dir, f))]
            print(folder_contents)
            for i in range(0, len(folder_contents)):              
                if folder_contents[i] != "merged." + file_type:
                    os.remove(dem_dir + "/" + folder_contents[i])

    elif merge_method == "all":
        for key in files:
            if os.path.exists(key):
                shutil.rmtree(key)
            dem_dir = key.rsplit("/", 1)[0]
        
        #remove top level direcot
        folder_contents = os.listdir(dem_dir)
        for i in range(0, len(folder_contents)):              
            if folder_contents[i] != "merged." + file_type:
                os.remove(dem_dir + "/" + folder_contents[i])

    
    
#TODO add resolution check back in
# def check_resolution(src_ds, resolution: str):
#     """
#     Check the resolution of GeoTIFF file and change if required

#     Args:
#         src_ds: GeoTiff file
#         resolution: the type resoltuion we need to change too (if required)
        
#     """
#     width = src_ds.RasterXSize
#     height = src_ds.RasterYSize

#     print(f"Current GeoTIFF resolution ... {width} x {height}")
#     if width == height and width in VALID_RESOLUTIONS:
#         print("✅ Resolution already matches a valid Unreal Engine landscape resolution!")
        
#     elif resolution != "none":
#         if resolution == "auto":
#             print("⚠️ Not a valid UE landscape size, auto resampling")
#             print(f"Nearest valid sizes: {min(VALID_RESOLUTIONS, key=lambda x: abs(x-width))} or {min(VALID_RESOLUTIONS, key=lambda x: abs(x-height))}")
#             new_resolution = min(VALID_RESOLUTIONS, key=lambda x: abs(x-width))
#         else:
#             print(f"⚠️ Not a valid UE landscape size, using custom resolution {resolution}")
#             new_resolution = int(resolution)

#         src_ds = gdal.Warp("", src_ds, width=new_resolution, height=new_resolution,format='VRT')
    
#     else:
#         print("Skipping Resolution resampling  ...")

#     return src_ds

   