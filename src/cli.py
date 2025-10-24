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

    # Optional config file argument
    parser.add_argument(
        "--config",
        type=str,
        help="Path to a JSON configuration file to use for defaults",
    )

    pre_args, remaining_argv = parser.parse_known_args()

    # Load defaults from config if present
    config_defaults = {}
    if pre_args.config:
        config_defaults = load_config(pre_args.config)

    parser = argparse.ArgumentParser(
        description="Download USGS data based on specified area of interest"
    )

    parser.add_argument(
        "--aoi",
        type=float,
        nargs=4,
        metavar=("minLon", "minLat", "maxLon", "maxLat"),
        help="Area of interest defined by minimum and maximum lat and long to make boudning box aoi"
        #required=True
    )

    parser.add_argument(
        "--type",
        type=str,
        choices=["dem", "lidar"],
        help="Type of data to pull from USGS"
        #required=True,
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory of data"
        #required=True
    )

    parser.add_argument(
        "--dem-spec",
        type=str,
        choices = ["regular", "seamless"],
        default = "regular",
        help="Type of DEM data to pull, seamless data is rare limited availability in the country. Default: regular"
    )

    parser.add_argument(
        "--dem-output",
        type=str,
        choices = ["tif", "png", "r16"],
        default = "tif",
        help="File type to save the Digital Elevation Maps (Note changing to png or raw will reduce precision). Default: tif"
    )

    parser.add_argument(
        "--png-precision",
        type =int,
        choices =[8, 16],
        default = 16,
        help = "If PNG is selected, change the precision type. Default: 16"
    )

    parser.add_argument(
        "--dem-merge",
        type = str,
        choices = ["no-merge", "merge-keep", "merge-delete"],
        default = "merge-keep",
        help = "For each project that gets downloaded merge or don't merge the GeoTIFF files into a single file." \
        " merge-keep keeps all original .tif/PNG/.r16 files and any metadata that get's generated. merge-delete removes all original files and only keeps the merged output." \
        " Default: merge-keep"
    )

    parser.add_argument(
        "--dem-merge-method",
        type = str,
        choices = ["project", "all", "both"],
        default = "all",
        help="Merge DEM Files accross projects or only merge DEM files within projects. Note: FILES FROM differet years may overlap or have differing structures." \
        " Default: all"
    )

    parser.add_argument(
        '--dem-filter-type', 
        type = str,
        choices = ["none", "merge", "all"],
        default="none", 
        help='For each GeoTiff that gets downloaded ' \
        'crop/filter down the Tiff to only the AOI being used. Some datasets may intersect with the AOI' \
            ' but are not a part of it. "none" will not filter any of the DEM files, "merge" will only filter the merged files' \
                ' If only one file is found in a project this will be rescaled and conveted. "any" will do this to any file merged or downloaded.' \
        " Default: all"
    )

    parser.add_argument(
        "--dem-resolution",
        type=str,
        choices = ["none", "auto", "1009", "2017", "4033", "8129"],
        default="auto",
        help="Scale the merged raw and or png files resolution to be combatible with UE terrain import. Only scales merged files" \
            " since single files can be represented in Unreal Engine."
            " Defualt: auto"
    )

    parser.add_argument(
        "--merge-lidar",
        type =str,
        choices = ["no-merge", "merge-keep", "merge-delete"],
        default = "merge-keep",
        help = "For each project that gets downloaded merge or don't merge the .laz/.las files into a single pointcloud." \
        "merge-keep keeps all original las/laz files. merge-delete removes all original files and only keeps the merged output. " \
        " Default: merge-keep"
    )

   
    args = check_arguments(parser, config_defaults, remaining_argv, pre_args)
    
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
    


def load_config(config_path):
    """Load configuration file and return a dict."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config file: {e}")
        sys.exit(1)


def check_arguments(parser, config_defaults, remaining_argv, pre_args):
    parser.set_defaults(**config_defaults)

    # Parse again with config defaults applied
    args = parser.parse_args(remaining_argv)

    # ---- Enforce required fields only if config not provided ----
    if not pre_args.config:
        missing = []
        if args.aoi is None:
            missing.append("--aoi")
        if args.type is None:
            missing.append("--type")
        if args.output_dir is None:
            missing.append("--output-dir")
        if missing:
            parser.error(f"The following arguments are required when no config is used: {', '.join(missing)}")

    # ---- Also check if config is missing any required keys ----
    elif pre_args.config:
        # Only warn, don't error — since CLI can override
        for key in ["aoi", "type", "output_dir"]:
            if key not in config_defaults and getattr(args, key) is None:
                parser.error(
                    f"'{key}' must be defined in the config file or passed on the command line."
                )
    
    return args


if __name__ == "__main__":
    main()