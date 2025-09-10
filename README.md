# usgs-data-tool
This USGS Data Tool is used to download national datasets through their API. Currently, only DEM (Digital Elevation Maps) and LiDAR dataset downloads are supported within this repository, but I am open to merge requests and colloboration to get further datasets and specifications in! More possibe options can be found on the USGS TNM API [documenation](https://tnmaccess.nationalmap.gov/api/v1/docs)

# Setup
To install this repository, just clone and run:
`./install.sh`

This will download and setup the usgs-download cli for you

# Usage
The usgs-downloader has three required arguments

1. `--aoi`: This is the **Area Of Interest** (i.e boudning box) to download the dataset. It requires minLon, minLat, maxLon, and a maxLat to create the boundary. These types of values can be obtained using websites like [this](https://prochitecture.com/blender-osm/extent/?blender_version=4.5&addon=blosm&addon_version=2.7.15)


2. `--type`: This is the dataset type to download, which is currently either lidar or dem files


3. `ouput-dir`: Directory to save files. Each file type will be broken into the datatype (lidar, dem, etc) and the USGS project it came from. For example, lidar would like:

```text
output_dir/
└── lidar/
    ├── project1/
    │   └── data1.laz
    └── project2/
        └── data2.laz
```

Provided below is an example of downloading DEM data:

```
usgs-download --aoi -84.45688 33.62848 -84.40212 33.65607 --type dem --output-dir test/
```

Use `usgs-download -h` for more options and usage

# Attribution
1. This repo was orginally inspired from this [repo](https://github.com/DHersh3094/USGS-LiDAR-CLI-Tool/tree/master), but I just wanted to make it more expandable and easy to use with the USGS TNM API :)
2. This repo was built as part of a pipeline for an [Autonoma](https://www.autonoma.ai/) project. Check out what we do, I think it is pretty cool :)

