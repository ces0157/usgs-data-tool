import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm
from lidar.lidar_tools import merge_lidar, reproject_lidar#, filter_lidar, detect_crs
from dem.dem_tools import convert_tiff, merge_dem, filter_dem, warp_dem

def download_data(args, download_information: dict, output_dir:str):
    """
    Download, save and merge (depending on datatypes) the file

    Args:
        args: command line arguments from the cli
        
        usgs_Data : json configuration holding names and format tpes 

    Returns:
        list of dicts containing dataset info and download URLs.
    """
    #dictonary containing project_dirs and associated files
    dem_project_dirs = {}
    lidar_project_dirs = {}
    
    #filtered_project_dirs = {}
    print(f"Downloading {len(download_information)} {args.type} datasets")
    for i in tqdm(range(0, len(download_information))):
        
        title = download_information[i]['title']
        if "Lidar" in title and "1M" not in title:
            data_type = "lidar"
        else:
            data_type = "dem"
        
        
        #get the name of the project we are downloading from
        
        session = requests.Session()
        retries = Retry(
            total=3,                 # Retry up to 3 times
            backoff_factor=1,        # Wait 1s, then 2s, then 4s between retries
            status_forcelist=[500, 502, 503, 504],  # Retry on these HTTP codes
            allowed_methods=["GET", "POST"],        # Retry on these methods
        )
        
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        
        url = download_information[i]["url"]

        #create project name from the download url
        project_name = url.split("Projects/")[1].split("/")[0]

        
        project_dir = output_dir + "/" + data_type + "/" + project_name

        os.makedirs(project_dir, exist_ok=True)

        filename = os.path.join(project_dir, url.split("/")[-1])
        print(f"Saving: {filename}")

        if data_type == "lidar":
            if project_dir in lidar_project_dirs:
                lidar_project_dirs[project_dir].append(filename)
            else:
                lidar_project_dirs[project_dir] = [filename]
        
        else:
            if project_dir in dem_project_dirs:
                dem_project_dirs[project_dir].append(filename)
            else:
                dem_project_dirs[project_dir] = [filename]

        
        #TODO: REMOVE verify is False and set up handeling
        r = session.get(url, stream=True, timeout=20, verify=True)
        r.raise_for_status()   # raise if HTTP error (404, 500, etc.)

        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        #we will filter the pointcloud now because filtering merged
        #will be do costly
        # if (args.type == "lidar" or args.type=="both") and args.lidar_filter == "filter":
        #     filter_output = project_dir + f"/filtered{i}.las"
        #     filter_lidar(filename, filter_output, args.aoi)
            
        #     crs_test = detect_crs(filename)

        #     if project_dir in filtered_project_dirs:
        #         filtered_project_dirs[project_dir].append(filter_output)
        #     else:
        #         filtered_project_dirs[project_dir] = [filter_output]




        if data_type == "dem" and (args.dem_output != "tif"):
            print("Converting file ...")
            output_filename = project_dir + "/" + "heightmap" + str(len(dem_project_dirs[project_dir])) + "." + args.dem_output
            convert_tiff(filename, args.dem_output, output_filename, args.png_precision)

        if data_type == "dem" and args.dem_filter_type == "all":
            output_filterd = project_dir + "/" + "heightmap" + str(len(dem_project_dirs[project_dir])) + "_filtered.tif"
            output_warped = project_dir + "/warped.tif"
            warp_dem([filename], output_warped)
            filter_dem(output_warped, output_filterd, args.aoi, args.dem_resolution)
            os.remove(output_warped)
            if args.dem_output != "tif":
                print("Converting filtered file ...")
                output_filename = project_dir + "/" + "heightmap" + str(len(dem_project_dirs[project_dir])) + "_filtered." + args.dem_output
                convert_tiff(output_filterd, args.dem_output, output_filename, args.png_precision)

    
    
    #merging files related to DEM files
    if (args.type == "dem" or args.type == "both") and (args.dem_merge == "merge-keep" or args.dem_merge == "merge-delete"):
        filter = False
        if args.dem_filter_type == "merge" or args.dem_filter_type == "all":
            print("filtering files")
            filter = True
        
        if args.dem_merge == "merge-keep":
            code = merge_dem(dem_project_dirs, True, args.dem_output, args.dem_merge_method, args.png_precision, filter, args.aoi, args.dem_resolution)
        else:
            code = merge_dem(dem_project_dirs, False, args.dem_output, args.dem_merge_method, args.png_precision, filter, args.aoi, args.dem_resolution)

        
    if (args.type == "lidar" or args.type == "both") and args.lidar_reproject == "auto":
        print(f"code to reproject lidar {code}")
        lidar_project_dirs = reproject_lidar(lidar_project_dirs, code)


    if (args.type == "lidar" or args.type == "both") and (args.merge_lidar == "merge-keep" or args.merge_lidar == "merge-delete"):
        if args.merge_lidar == "merge-keep":
            merge_lidar(lidar_project_dirs, True)
        else:
            merge_lidar(lidar_project_dirs, False)




    #merging files related to lidar
    # if (args.type == "lidar" or args.type == "both") and (args.merge_lidar == "merge-keep" or args.merge_lidar == "merge-delete"):
        
        
    #     project_files = lidar_project_dirs
    #     if args.lidar_filter == "filter":
    #         project_files = filtered_project_dirs
            
    #     if args.merge_lidar == "merge-keep":
    #         merge_lidar(project_files, True)
    #     else:
    #         merge_lidar(project_files, False)

        



        



