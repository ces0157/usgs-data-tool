#!/usr/bin/env python3
"""
USGS Data Tool CLI - Download and process USGS geospatial datasets.
"""
import argparse
import os
import json
import sys

from data_helpers.fetch_files import fetch_data_list
from data_helpers.download import download_data
from exceptions import (
    USGSDataToolError,
    ConfigNotFoundError,
    InvalidConfigError,
    ConnectionFailedError,
    APITimeoutError
)


def main():
    """Main entry point for the USGS Data Tool CLI."""
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
        help="Area of interest defined by minimum and maximum lat and long to make bounding box AOI"
    )

    parser.add_argument(
        "--type",
        type=str,
        choices=["dem", "lidar", "both"],
        help="Type of data to pull from USGS"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory of data"
    )

    parser.add_argument(
        "--dem-spec",
        type=str,
        choices=["regular", "seamless"],
        default="regular",
        help="Type of DEM data to pull, seamless data is rare limited availability in the country. Default: regular"
    )

    parser.add_argument(
        "--dem-output",
        type=str,
        choices=["tif", "png", "r16"],
        default="tif",
        help="File type to save the Digital Elevation Maps (Note changing to png or raw will reduce precision). Default: tif"
    )

    parser.add_argument(
        "--png-precision",
        type=int,
        choices=[8, 16],
        default=16,
        help="If PNG is selected, change the precision type. Default: 16"
    )

    parser.add_argument(
        "--dem-merge",
        type=str,
        choices=["no-merge", "merge-keep", "merge-delete"],
        default="merge-keep",
        help="For each project that gets downloaded merge or don't merge the GeoTIFF files into a single file. "
             "merge-keep keeps all original .tif/PNG/.r16 files and any metadata that get's generated. "
             "merge-delete removes all original files and only keeps the merged output. Default: merge-keep"
    )

    parser.add_argument(
        "--dem-merge-method",
        type=str,
        choices=["project", "all", "both"],
        default="all",
        help="Merge DEM Files across projects or only merge DEM files within projects. "
             "Note: FILES FROM different years may overlap or have differing structures. Default: all"
    )

    parser.add_argument(
        '--dem-filter-type',
        type=str,
        choices=["none", "merge", "all"],
        default="none",
        help='For each GeoTiff that gets downloaded crop/filter down the Tiff to only the AOI being used. '
             '"none" will not filter any of the DEM files, "merge" will only filter the merged files. '
             '"all" will filter any file merged or downloaded. Default: none'
    )

    parser.add_argument(
        "--dem-resolution",
        type=str,
        choices=["none", "auto", "1009", "2017", "4033", "8129"],
        default="auto",
        help="Scale the merged raw and or png files resolution to be compatible with UE terrain import. "
             "Only scales merged files since single files can be represented in Unreal Engine. Default: auto"
    )

    parser.add_argument(
        "--merge-lidar",
        type=str,
        choices=["no-merge", "merge-keep", "merge-delete"],
        default="merge-keep",
        help="For each project that gets downloaded merge or don't merge the .laz/.las files into a single pointcloud. "
             "merge-keep keeps all original las/laz files. merge-delete removes all original files and only keeps "
             "the merged output. Default: merge-keep"
    )

    parser.add_argument(
        "--lidar-filter",
        type=str,
        choices=["no-filter", "filter"],
        default="filter",
        help="After Lidar is merged, filter to the boundary that was specified. ONLY MERGED IS CURRENTLY SUPPORTED"
    )

    parser.add_argument(
        "--lidar-reproject",
        choices=["none", "auto"],
        default="none",
        help="If the --both tag is selected for the output type then we can reproject "
             "the lidar into the same coordinate system as the digital elevation maps. "
             "Note: THIS is only supported if both and dem-merge are selected"
    )

    args = check_arguments(parser, config_defaults, remaining_argv, pre_args)

    # Normalize output directory path
    output_dir = args.output_dir.rstrip("/")

    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        print(f"Error: Could not create output directory '{output_dir}': {e}")
        sys.exit(1)

    # Load the USGS data configuration
    usgs_data = load_usgs_config()

    # Fetch dataset information from USGS API
    bbox = tuple(args.aoi)
    try:
        if args.type == "dem":
            download_info = fetch_data_list(bbox, args.type, usgs_data, args.dem_spec)
        elif args.type == "lidar":
            download_info = fetch_data_list(bbox, args.type, usgs_data)
        else:  # both
            download1 = fetch_data_list(bbox, "dem", usgs_data, args.dem_spec)
            download2 = fetch_data_list(bbox, "lidar", usgs_data)
            download_info = download1 + download2
    except ConnectionFailedError as e:
        print(f"Error: Failed to connect to USGS API: {e}")
        sys.exit(1)
    except APITimeoutError as e:
        print(f"Error: USGS API request timed out: {e}")
        sys.exit(1)
    except USGSDataToolError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Found {len(download_info)} files within the region of interest")

    if len(download_info) == 0:
        print("No datasets found for the specified area of interest.")
        return

    # Download and process the data
    try:
        download_data(args, download_info, output_dir)
        print("Download complete!")
    except USGSDataToolError as e:
        print(f"Error during download: {e}")
        sys.exit(1)


def load_config(config_path: str) -> dict:
    """
    Load configuration file and return a dict.

    Args:
        config_path: Path to the JSON configuration file.

    Returns:
        Dictionary containing configuration values.

    Raises:
        SystemExit: If config file cannot be loaded.
    """
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration file: {e}")
        sys.exit(1)
    except IOError as e:
        print(f"Error: Could not read configuration file: {e}")
        sys.exit(1)


def load_usgs_config() -> dict:
    """
    Load the USGS data configuration file.

    Returns:
        Dictionary containing USGS dataset definitions.

    Raises:
        SystemExit: If config file cannot be loaded.
    """
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    usgs_file = os.path.join(curr_dir, "usgs_data.json")

    if not os.path.exists(usgs_file):
        print(f"Error: USGS configuration file not found: {usgs_file}")
        sys.exit(1)

    try:
        with open(usgs_file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in USGS configuration file: {e}")
        sys.exit(1)
    except IOError as e:
        print(f"Error: Could not read USGS configuration file: {e}")
        sys.exit(1)


def check_arguments(parser, config_defaults: dict, remaining_argv: list, pre_args) -> argparse.Namespace:
    """
    Validate and process command line arguments.

    Args:
        parser: ArgumentParser instance.
        config_defaults: Default values from config file.
        remaining_argv: Remaining command line arguments.
        pre_args: Pre-parsed arguments (for config file).

    Returns:
        Parsed and validated arguments namespace.
    """
    parser.set_defaults(**config_defaults)

    # Parse again with config defaults applied
    args = parser.parse_args(remaining_argv)

    # Enforce required fields only if config not provided
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

    # Also check if config is missing any required keys
    elif pre_args.config:
        for key in ["aoi", "type", "output_dir"]:
            if key not in config_defaults and getattr(args, key) is None:
                parser.error(
                    f"'{key}' must be defined in the config file or passed on the command line."
                )

    return args


if __name__ == "__main__":
    main()
