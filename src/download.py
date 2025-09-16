import os
import requests
from tqdm import tqdm
from lidar_tools import merge_lidar
from dem_tools import convert_tiff

def download_data(args, download_information: dict, output_dir:str):
    """
    Download, save and merge (depending on datatypes) the file

    Args:
        args: command line arguments from the cli
        
        usgs_Data : json configuration holding names and format tpes 

    Returns:
        list of dicts containing dataset info and download URLs.
    """
    project_dirs = set()
    print(f"Downloading {len(download_information)} {args.type} datasets")
    for i in tqdm(range(0, len(download_information))):
        #get the name of the project we are downloading from
        url = download_information[i]["url"]

        project_name = url.split("Projects/")[1].split("/")[0]
        project_dir = output_dir + "/" + args.type + "/" + project_name

        project_dirs.add(project_dir)
        os.makedirs(project_dir, exist_ok=True)

        filename = os.path.join(project_dir, url.split("/")[-1])
        
        #TODO: REMOVE verify is False and set up handeling
        r = requests.get(url, stream=True, timeout=20, verify=False)
        r.raise_for_status()   # raise if HTTP error (404, 500, etc.)

        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        if args.type == "dem" and (args.dem_output != "tiff"):
            print("Converting file ...")
            convert_tiff(project_dir, filename, args.dem_output, i, args.png_precision)

    
    if args.type == "lidar" and (args.merge_lidar == "merge-keep" or args.merge_lidar == "merge-delete"):
        if args.merge_lidar == "merge-keep":
            merge_lidar(project_dirs, True)
        else:
            merge_lidar(project_dirs, False)

    


        



