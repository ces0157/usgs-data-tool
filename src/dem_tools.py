from osgeo import gdal
import numpy as np
from PIL import Image
import os
import glob



def convert_tiff(input_dir: str, file: str, new_file_type: str):
    """
    Convert GeoTIFF files into either a RAW or PNG 

    Args:
        input_dir: directory we are saving too
        file: file to be replaced
        new_file_type: new file type to be saved (png or raw)
        
    """
    filename = os.path.basename(file)
    filename = filename.replace(".tif", "")

    src_ds = gdal.Open(file)

    band = src_ds.GetRasterBand(1)
    min_val, max_val = band.ComputeRasterMinMax(True)

    if new_file_type == "png":
        output_png = input_dir + "/" + filename + ".png"
        #conver to png
        gdal.Translate(
            output_png,
            src_ds,
            format="PNG",        # Equivalent to -of PNG
            outputType=gdal.GDT_Byte,  # Equivalent to -ot Byte
            scaleParams=[[min_val, max_val, 0, 255]]       # Equivalent to -scale (auto-scale min/max to 0–255)
        )
    
    elif new_file_type == "raw":
        output_raw = input_dir + "/" + filename + ".raw"
        gdal.Translate(
            output_raw,
            src_ds,
            format="ENVI",             # RAW-like format with .hdr file
            outputType=gdal.GDT_UInt16,
            scaleParams=[]             # Auto-scale min->0, max->65535
        )

    
    os.remove(file)

   