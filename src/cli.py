#!/usr/bin/env python3
import argparse
import os
import json
from fetch_files import fetch_lidar_data, fetch_dem_data
from download import download_data


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

    args = parser.parse_args()
    
    #used to help ensure easy string additions later on in the code
    if args.output_dir[-1] == "/":
        output_dir = args.output_dir[:-1]
    else:
        output_dir = args.output_dir
    
    os.makedirs(output_dir, exist_ok=True)

    #load the usgs data information to allow for downloads
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    usgs_file = os.path.join(curr_dir, "usgs_data.json")
    
    
    with open(usgs_file, "r") as f:
        usgs_data = json.load(f)


    bbox = tuple(args.aoi)
    if args.type == "lidar":
        download_info = fetch_lidar_data(bbox, args.type, usgs_data)
    elif args.type == "dem":
        download_info = fetch_dem_data(bbox, args.type, args.dem_spec, usgs_data)

    print(f"Found {len(download_info)} within the region of interest")
    download_data(args.type, download_info, output_dir)









if __name__ == "__main__":
    main()