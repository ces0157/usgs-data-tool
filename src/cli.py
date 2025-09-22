#!/usr/bin/env python3
import argparse
import os
import json
# from data_helpers.fetch_files import fetch_lidar_data, fetch_dem_data
from data_helpers.fetch_files import fetch_data_list
from data_helpers.download import download_data


def main():
    parser = argparse.ArgumentParser(
        description="Download USGS data based on specified area of interest"
    )

    parser.add_argument(
        "--aoi",
        type=float,
        nargs=4,
        metavar=("minLon", "minLat", "maxLon", "maxLat"),
        help="Area of interest defined by minimum and maximum lat and long to make boudning box aoi",
        required=True
    )

    parser.add_argument(
        "--type",
        type=str,
        choices=["dem", "lidar"],
        help="Type of data to pull from USGS",
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory of data",
        required=True
    )

    parser.add_argument(
        "--dem-spec",
        type=str,
        choices = ["regular", "seamless"],
        default = "regular",
        help="Type of DEM data to pull, seamless data is rare limited availability in the country"
    )

    parser.add_argument(
        "--dem-output",
        type=str,
        choices = ["tif", "png", "r16"],
        default = "tif",
        help="File type to save the Digital Elevation Maps (Note changing to png or raw will reduce precision)"
    )

    parser.add_argument(
        "--png-precision",
        type =int,
        choices =[8, 16],
        default = 16,
        help = "If PNG is selected, change the precision type."
    )

    parser.add_argument(
        "--dem-merge",
        type = str,
        choices = ["no-merge", "merge-keep", "merge-delete"],
        default = "merge-keep",
        help = "For each project that gets downloaded merge or don't merge the GeoTIFF files into a single file"
        "merge-keep keeps all original .tif/PNG/.r16 files and any metadata that get's generated. merge-delete removes all original files and only keeps the merged output"
    )

    parser.add_argument(
        "--dem-merge-method",
        type = str,
        choices = ["project", "all", "both"],
        default = "all",
        help="Merge DEM Files accross projects or only merge DEM files within projects. Note: FILES FROM differet years may overlap or have differing structures"
    )

    # parser.add_argument(
    #     '--dem-filter', 
    #     action='store_true', 
    #     help='For each GeoTiff that gets downloaded ' \
    #     'crop/filter down the Tiff to only the AOI being used. Some datasets may intersect with the AOI' \
    #         'but are not a part of it')

    # parser.add_argument(
    #     "--dem-scale",
    #     type=str,
    #     choices = ["none", "auto", "1009", "2017", "4033", "8129", "8129"],
    #     default="auto",
    #     help="Scale the raw and or png files resolution to be combatible with UE terrain import. Only scales if dem-output is changed to png or raw"
    # )

    parser.add_argument(
        "--merge-lidar",
        type =str,
        choices = ["no-merge", "merge-keep", "merge-delete"],
        default = "merge-keep",
        help = "For each project that gets downloaded merge or don't merge the .laz/.las files into a single pointcloud."
        "merge-keep keeps all original las/laz files. merge-delete removes all original files and only keeps the merged output "
    )



    args = parser.parse_args()

    
    #used to help ensure easy string additions later on in the code
    if args.output_dir[-1] == "/":
        output_dir = args.output_dir[:-1]
    else:
        output_dir = args.output_dir
    
    os.makedirs(output_dir, exist_ok=True)

    #load the usgs data information to allow for downloads
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    usgs_file = os.path.join(curr_dir, "usgs_data.json")
    
    
    with open(usgs_file, "r") as f:
        usgs_data = json.load(f)


    bbox = tuple(args.aoi)
    if args.type == "dem":
        download_info = fetch_data_list(bbox, args.type, usgs_data, args.dem_spec)
    else:
        download_info = fetch_data_list(bbox, args.type, usgs_data)

    print(f"Found {len(download_info)} files within the region of interest")

    if(len(download_info) != 0):
        download_data(args, download_info, output_dir)
    









if __name__ == "__main__":
    main()