import argparse
import os
import json
from fetch_files import fetch_lidar_data, fetch_dem_data


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



    #load the usgs data information to allow for downloads
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    usgs_file = os.path.join(curr_dir, "usgs_data.json")
    
    
    with open(usgs_file, "r") as f:
        usgs_data = json.load(f)


    bbox = tuple(args.aoi)
    if args.type == "lidar":
        download_link = fetch_lidar_data(bbox, args.type, usgs_data)
    elif args.type == "dem":
        download_link = fetch_dem_data(bbox, args.type, args.dem_spec, usgs_data)











if __name__ == "__main__":
    main()