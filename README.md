# usgs-data-tool
This USGS Data Tool is used to download national datasets through their API. Currently, only DEM (Digital Elevation Maps) and LiDAR dataset downloads are supported within this repository, but I am open to merge requests and collaboration to get further datasets and specifications in! More possible options can be found on the USGS TNM API [documenation](https://tnmaccess.nationalmap.gov/api/v1/docs)

# Setup
The only prerequisite to installing is ensuring conda is installed (note that this has only been texted on linux).

To install this repository, just clone and run:
`./install.sh`

This will download and setup a virtual environment where the usgs-download cli tool is set up for you

# Usage
The usgs-downloader has three required arguments:

1. `--aoi`: This is the **Area Of Interest** (i.e bounding box) to download the dataset. It requires minLon, minLat, maxLon, and a maxLat to create the boundary. These types of values can be obtained using websites like [this](https://prochitecture.com/blender-osm/extent/?blender_version=4.5&addon=blosm&addon_version=2.7.15)


2. `--type`: This is the dataset type to download, which is currently either lidar or dem files


3. `ouput-dir`: Directory to save files. Each file type will be broken into the datatype (lidar, dem, etc) and the USGS project it came from. For example, lidar would like:

```text
output_dir/
└── lidar/
    ├── project1/
    │   └── data1.laz
    └── project2/
        └── data1.laz
```

Provided below is an example of downloading DEM data:

```
usgs-download --aoi -84.45688 33.62848 -84.40212 33.65607 --type dem --output-dir test/
```

Use `usgs-download -h` for more options and usage.


# API Configuration and Contributing
If you look at the file `src/usgs_data.json` you can see how I structured the API requests that get made for each dataset type. 

For example, suppose you wanted to contribute add a new request for the `NED` dataset, the json could look like this:

```
"ned" : {
    "1/3 arc": {
        "usgs_name": "National Elevation Dataset (NED) 1/3 arc-second"
        "usgs_data_format": "GeoTIFF"
    }
    "1/9 arc" : {
        "usgs_name": "National Elevation Dataset (NED) 1/9 arc-second"
        "usgs_data_format": "GeoTIFF"
    }
}
```

The `usgs_name` is the real name that get's called from the API and the `usgs_data_format` is the format accepted for this dataset. See `src/data_helpers/fetch_files.py` for how this is properly used. Adding more to the json will require some modifications to the cli commands and how files are fetched. I plan on making `src/data_helpers/fetch_files.py` more generalizable in the future.

# Attribution
1. This repo was originally inspired from this [repo](https://github.com/DHersh3094/USGS-LiDAR-CLI-Tool/tree/master), but I just wanted to make it more expandable and easy to use with the USGS TNM API :)
2. This repo was built as part of a pipeline for an [Autonoma](https://www.autonoma.ai/) project. Check out what we do, I think it is pretty cool :)

