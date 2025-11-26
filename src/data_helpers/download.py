import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm
from lidar.lidar_tools import merge_lidar
from dem.dem_tools import convert_tiff, merge_dem, filter_dem, warp_dem


def _load_existing_projects(output_dir: str, data_type: str) -> dict:
    """
    Collect already-downloaded source files so they can be reused and merged.
    """
    projects = {}
    type_dir = os.path.join(output_dir, data_type)

    if not os.path.isdir(type_dir):
        return projects

    for project_name in os.listdir(type_dir):
        project_dir = os.path.join(type_dir, project_name)
        if not os.path.isdir(project_dir):
            continue

        for entry in os.listdir(project_dir):
            full_path = os.path.join(project_dir, entry)
            if not os.path.isfile(full_path):
                continue

            # Only keep original source files, skip merged/filtered outputs
            lower = entry.lower()
            if data_type == "dem":
                if not lower.endswith(".tif") or "merged" in lower or "filtered" in lower or "warped" in lower:
                    continue
            elif data_type == "lidar":
                if not (lower.endswith(".las") or lower.endswith(".laz")):
                    continue
            else:
                continue

            if project_dir not in projects:
                projects[project_dir] = []
            projects[project_dir].append(full_path)

    return projects


def download_data(args, download_information: dict, output_dir:str):
    """
    Download, save and merge (depending on datatypes) the file

    Args:
        args: command line arguments from the cli
        
        usgs_Data : json configuration holding names and format tpes 

    Returns:
        list of dicts containing dataset info and download URLs.
    """
    # dictonary containing project_dirs and associated files, start with any existing data to reuse
    project_dirs = _load_existing_projects(output_dir, args.type)

    # Shared session with retries for all downloads
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    print(f"Downloading {len(download_information)} {args.type} datasets")
    for i in tqdm(range(0, len(download_information))):
        #get the name of the project we are downloading from

        
        url = download_information[i]["url"]

        #create project name from the download url
        project_name = url.split("Projects/")[1].split("/")[0]
        project_dir = output_dir + "/" + args.type + "/" + project_name

        os.makedirs(project_dir, exist_ok=True)

        filename = os.path.join(project_dir, url.split("/")[-1])
        print(f"Saving: {filename}")

        if project_dir not in project_dirs:
            project_dirs[project_dir] = []

        # Always include the path in the merge list, but avoid duplicates
        if filename not in project_dirs[project_dir]:
            project_dirs[project_dir].append(filename)

        # Skip downloading if the file is already present so we can reuse cached data
        if os.path.exists(filename):
            print(f"Found existing file, skipping download: {filename}")
        else:
            #TODO: REMOVE verify is False and set up handeling
            r = session.get(url, stream=True, timeout=20, verify=True)
            r.raise_for_status()   # raise if HTTP error (404, 500, etc.)

            with open(filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        if args.type == "dem" and (args.dem_output != "tif"):
            print("Converting file ...")
            output_filename = project_dir + "/" + "heightmap" + str(len(project_dirs[project_dir])) + "." + args.dem_output
            convert_tiff(filename, args.dem_output, output_filename, args.png_precision)

        if args.type == "dem" and args.dem_filter_type == "all":
            output_filterd = project_dir + "/" + "heightmap" + str(len(project_dirs[project_dir])) + "_filtered.tif"
            output_warped = project_dir + "/warped.tif"
            warp_dem([filename], output_warped)
            filter_dem(output_warped, output_filterd, args.aoi, args.dem_resolution)
            os.remove(output_warped)
            if args.dem_output != "tif":
                print("Converting filtered file ...")
                output_filename = project_dir + "/" + "heightmap" + str(len(project_dirs[project_dir])) + "_filtered." + args.dem_output
                convert_tiff(output_filterd, args.dem_output, output_filename, args.png_precision)

    
    
    #merging files related to DEM files
    if args.type == "dem" and (args.dem_merge == "merge-keep" or args.dem_merge == "merge-delete"):
        filter = False
        if args.dem_filter_type == "merge" or args.dem_filter_type == "all":
            filter = True
        
        if args.dem_merge == "merge-keep":
            merge_dem(project_dirs, True, args.dem_output, args.dem_merge_method, args.png_precision, filter, args.aoi, args.dem_resolution)
        else:
            merge_dem(project_dirs, False, args.dem_output, args.dem_merge_method, args.png_precision, filter, args.aoi, args.dem_resolution)

        
        
    #merging files related to lidar
    if args.type == "lidar" and (args.merge_lidar == "merge-keep" or args.merge_lidar == "merge-delete"):
        if args.merge_lidar == "merge-keep":
            merge_lidar(project_dirs, True)
        else:
            merge_lidar(project_dirs, False)




        


