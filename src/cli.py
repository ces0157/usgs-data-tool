import argparse
import os


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
        choices=["dem", "lidar", "both"],
        help="Type of data to pull from USGS",
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory of data",
        required=True
    )

    args = parser.parse_args()








if __name__ == "__main__":
    main()