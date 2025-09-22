from osgeo import gdal
import numpy as np
from PIL import Image
import os
import glob
import shutil
import subprocess

#TODO add this back in
#VALID_RESOLUTIONS = {1009, 2017, 4033, 8129}  # UE-supported sizes (power of 2 + 1)

def convert_tiff(input_dir: str, file: str, new_file_type: str, output_file: str, precision=None):
    """
    Convert GeoTIFF files into either a RAW (r16) or PNG 

    Args:
        input_dir: directory we are saving too
        file: file to be replaced
        new_file_type: new file type to be saved (png or raw)
        output_filename: name of the new filename to save
        precision: precision in which to save a png file. RAW files will always default to 16
    """
    
    #filename = "heightmap" + str(index)

    src_ds = gdal.Open(file)

    band = src_ds.GetRasterBand(1)
    min_val, max_val = band.ComputeRasterMinMax(True)


    #src_ds = check_resolution(src_ds, resolution)
        
    
    if new_file_type == "png":
        
        if precision == 16:
            output_precision = gdal.GDT_UInt16
            max_normalization = 65535
        else:
            output_precision = gdal.GDT_Byte
            max_normalization = 255

        #output_png = input_dir + "/" + output_filename + ".png"
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


def merge_dem(files: dict, keep_files: bool, file_type: str, precision=None):
    """
    Merge DEM files together into a single GeoTIFF file

    Args:
    files: dictonary where the keys are folders and the filenames are the value
    keep_files: Weather to keep the original files afterwards
    file_type: how to save the merged output (tif, png, raw)
    """
    for key in files:
        print(files[key])
        if len(files[key]) == 1:
            print("Only 1 file recongized ... no merging required")
            continue
        
        #create an output GTIFF
        output_file_tif = key + "/" + "merged.tif"
        gdal.Warp(
            destNameOrDestDS=output_file_tif,
            srcDSOrSrcDSTab=files[key],
            format="GTiff"
        )

        #convert the output to png or raw16
        if file_type != "tiff":
            output_file = key + "/" + "merged." + file_type 
            convert_tiff(key, output_file_tif, file_type, output_file, precision)
        
        #remove all files that are not merged files
        if not keep_files:
            folder_contents = os.listdir(key)
            print(folder_contents)
            for i in range(0, len(folder_contents)):
                print(folder_contents[i])
                    
                #delete everything except merge files and if there was only one file to begin with
                #then delete nothing
                if folder_contents[i] != "merged." + file_type:
                    print(key + "/" + folder_contents[i])
                    os.remove(key + "/" + folder_contents[i])
                


    
    
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

   