import requests
import os
import json

BASE_URL = "https://tnmaccess.nationalmap.gov/api/v1/products"

def fetch_lidar_data(bbox: tuple, type:str, usgs_data:dict) -> list[dict]:
    """
    Query The National Map (TNM) API for given lidar dataset

    Args:
        bbox (tuple): (minLon, minLat, maxLon, maxLat) in WGS84 (lon/lat).
        type (str): (lidar, dem) datatype
        usgs_Data (Dict): json configuration holding names and format tpes 
        

    Returns:
        list of dicts containing dataset info and download URLs.
    """
    
    dataset_name = usgs_data[type]["usgs_name"]
    dataset_format = usgs_data[type]["usgs_data_format"]

    print(dataset_name)
    print(dataset_format)

    return fetch_data(dataset_name, dataset_format, bbox)


def fetch_dem_data(bbox: tuple, type: str, spec: str, usgs_data:dict) -> list[dict]:
    """
    Query The National Map (TNM) API for given DEM dataset

    Args:
        bbox: (minLon, minLat, maxLon, maxLat) in WGS84 (lon/lat).
        type: (lidar, dem) datatype
        spec: this type has dataset may have different types (seamsless versus regular).
        Refer to USGS documenation
        usgs_Data: json configuration holding names and format tpes 
        

    Returns:
        list of dicts containing dataset info and download URLs.
    """
    dataset_name = usgs_data[type][spec]["usgs_name"]
    dataset_format = usgs_data[type][spec]["usgs_data_format"]

    print(dataset_name)
    print(dataset_format)

    return fetch_data(dataset_name, dataset_format, bbox)


def fetch_data(dataset_name: str, dataset_format: str, bbox: dict) -> list[dict]:
    """
    Query The National Map (TNM) API for given name, format, and bounding box

    Args:
        dataset_name: name of the datset to be downloaded (i.e is it a Lidar, DEM, etc.)
        dataset_format: format of the dataset to be downloaded
        usgs_Data: json configuration holding names and format tpes 
        

    Returns:
        list of dicts containing dataset info and download URLs.
    """
    params = {
        "datasets": dataset_name,
        "bbox": ",".join(map(str, bbox)),
        "prodFormats": dataset_format  # DEMs usually available as GeoTIFF
    }

    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return []

    data = response.json()

    results = []

    for item in data.get("items", []):
        results.append({
            "title": item.get("title"),
            "publicationDate": item.get("publicationDate"),
            "format": item.get("prodFormats"),
            "url": item.get("downloadURL")
        })

    return results
