from osgeo import gdal
import numpy as np
from PIL import Image
import os
import glob
import shutil
import subprocess
import shutil
import math



VALID_RESOLUTIONS = {1009, 2017, 4033, 8129}  # UE-supported sizes (power of 2 + 1)

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
    
    vertical_range = (max_val - min_val)
    print(f"Vertical range of {file}: {str(vertical_range)}")
        
    
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
                    
                    warp_dem(files[key], output_warped)
                    filter_dem(output_warped, output_filtered, bbox)
                    os.remove(output_warped)
                    if file_type != "tif":
                        output_file = key + "/heightmap1_filtered." + file_type
                        convert_tiff(output_filtered, file_type, output_file, precision)
                
                continue
            
            #create an output GTIFF
            #TODO: TEST filter for just project
            #this is done so we wait to rescale unitl after all files have been merged. We want to combine all at native resoltuion before crooping
            #and rescaling
            if merge_method != "both":
                merge(key, files[key], file_type, precision, filter, bbox, scale_resolution)
            
            #no resizing,cropping, or conversion will occur unitl after everything is combined.
            else:
                merge(key, files[key], "tif", precision)

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
            
            #merge all project files together (i.e merged.tif from project1, project2, etc.)
            merge(output_dir, merged_files, file_type, precision, filter, bbox, scale_resolution)
            
            #now that we combined all merged files, ensure the merged files in each project are rescaled to target aoi and converted
            #this should only happen if a merged file exists (aka when there are more htan two files to a project)
            if len(files[key]) != 1:
                for file in merged_files:
                    project_output_dir = file.rsplit("/", 1)[0]
                    translate_and_replace(project_output_dir, file, file_type, precision, filter, bbox, scale_resolution)
                

     
    elif merge_method == "all":
        all_files = []
        for key in files:
            all_files = all_files + files[key]
            #get the output directory for digital elevation maps 
            output_dir = key.rsplit("/", 1)[0]
        
        merge(output_dir, all_files, file_type, precision, filter, bbox, scale_resolution)    
   
    #remove all files that are not merged files
    if not keep_files:
        remove_files(files, file_type, merge_method)


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
    #convert to lat long and merge
    warp_dem(files, output_file_tif)

    translate_and_replace(output_dir, output_file_tif, file_type, precision, filter, bbox, scale_resolution)


def warp_dem(input_files, out_file: str):
    """"
    Converts to Lat/lon and merge if nesseccary
    
    Args:
    input_files: an array of files to be merged/changed
    out_file: name of the file to be changed
    """
    
    gdal.Warp(
        destNameOrDestDS=out_file,
        srcDSOrSrcDSTab=input_files,
        format="GTiff",
        dstSRS="EPSG:4326",
        resampleAlg="cubic"
    )
    



def filter_dem(input_tif: str, out_file: str, bbox = None, scale_resolution="none"):
    """
    Crop down the DEM file to the target location
    
    ARGS
    input_tif: the tiff we are modifying/changing/saving
    out_file: the name we should use
    bbox: the area of interest to filter too
    scale_resolution should we rescale this file
    """
    
    src_ds = gdal.Open(input_tif)
    width, height = get_resoltuion(src_ds, scale_resolution)

    gdal.Translate(
        out_file,
        input_tif,
        projWin=(bbox[0], bbox[3], bbox[2], bbox[1]), # minX, maxY, maxX, minY
        width=width,
        height=height,
        resampleAlg="cubic"
    )
   


def translate_and_replace(output_dir:str, input_tif:str , file_type:str, precision=None, filter = False, bbox=None, scale_resolution="none"):
    """
    Translates, converts, and replaces files if need be
    
    output_dir: where we are saving too
    input_tif: the tiff we are modifying/saving
    file_type: how to save the merged output (tif, png, raw)
    precision: the precision that we save too 
    filter: crop the DEM to specified area
    bbox: the area of interest to filter too
    """
    #TODO: REFACTOR reduant code between filtered_dem and this
    tmp_file = output_dir + "/temp.tif"
    src_ds = gdal.Open(input_tif)
    width, height = get_resoltuion(src_ds, scale_resolution)
    
    if filter:
        output_filtered = output_dir + "/merged_filtered.tif"
        filter_dem(input_tif, output_filtered, bbox, scale_resolution)

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
        convert_tiff(input_tif, file_type, output_file, precision)
        if filter:
            output_file = output_dir + "/" + "merged_filtered." + file_type
            convert_tiff(output_dir + "/merged_filtered.tif", file_type, output_file, precision) 
     


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
                    if "merged" not in folder_contents[i] or file_type not in folder_contents[i] or "xml" in folder_contents[i]:
                        #print(key + "/" + folder_contents[i])
                        os.remove(key + "/" + folder_contents[i])
            dem_dir = key.rsplit("/", 1)[0]
        
        #remove top level directory contents
        if merge_method == "both":
            folder_contents = [f for f in os.listdir(dem_dir) if os.path.isfile(os.path.join(dem_dir, f))]
            for i in range(0, len(folder_contents)):              
                if "merged" not in folder_contents[i] or file_type not in folder_contents[i] or "xml" in folder_contents[i]:
                    os.remove(dem_dir + "/" + folder_contents[i])

    elif merge_method == "all":
        for key in files:
            if os.path.exists(key):
                shutil.rmtree(key)
            dem_dir = key.rsplit("/", 1)[0]
        
        #remove top level direcot
        folder_contents = os.listdir(dem_dir)
        for i in range(0, len(folder_contents)):              
            if "merged" not in folder_contents[i] or file_type not in folder_contents[i] or "xml" in folder_contents[i]:
                os.remove(dem_dir + "/" + folder_contents[i])

    
#TODO MAKE resolution unit tests 
def get_resoltuion(src_ds, resolution: str):
    """
    Check the resolution of GeoTIFF file and change if required

    Args:
        src_ds: GeoTiff file
        resolution: the type resoltuion we need to change too (if required)
        
    """
    if resolution != "auto" and resolution != "none":
        print(f"Chaning Resoltuion to {resolution} x {resolution}")
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


    

   