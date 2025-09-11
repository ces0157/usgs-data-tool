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

    
    # Read GEO-TIFF
    ds = gdal.Open(file)
    band = ds.GetRasterBand(1)
    array = band.ReadAsArray().astype(np.float32)

    #Normalize TO 0-65535
    min_val = np.nanmin(array)
    max_val = np.nanmax(array)

    # Avoid divide-by-zero
    if max_val == min_val:
        norm_array = np.zeros_like(array, dtype=np.uint16)
    else:
        norm_array = ((array - min_val) / (max_val - min_val) * 65535).astype(np.uint16)

    if new_file_type == "raw":
        output_raw = input_dir + "/" + filename + ".raw"
        with open(output_raw, "wb") as f:
            norm_array.byteswap(False).tofile(f)

    elif new_file_type == "png":
        output_png = input_dir + "/" + filename + ".png"
        img = Image.fromarray(norm_array, mode="I;16")
        img.save(output_png)
    
    #remove the original tiff file
    os.remove(file)
