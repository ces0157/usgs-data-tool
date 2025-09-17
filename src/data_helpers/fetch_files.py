import requests
import os
import json

BASE_URL = "https://tnmaccess.nationalmap.gov/api/v1/products"


def fetch_data_list(bbox: tuple, type: str, usgs_data:dict, spec:str = "regular") -> list[dict]:
    """
    Extract dataset type and spec and pass to the dataset types and function

    Args:
        bbox: (minLon, minLat, maxLon, maxLat) in WGS84 (lon/lat).
        type: (lidar, dem) datatype
        usgs_Data: json configuration holding names, specs, and format types
        specs: specialization of datast we are dealing with 
        
    Returns:
        list of dicts containing dataset info and download URLs.
    """
    
    
    dataset_name = usgs_data[type][spec]["usgs_name"]
    dataset_format = usgs_data[type][spec]["usgs_data_format"]
    
    return fetch_datasets(dataset_name, dataset_format, bbox)



def fetch_datasets(dataset_name: str, dataset_format: str, bbox: tuple) -> list[dict]:
    """
    Query The National Map (TNM) API for given name, format, and bounding box

    Args:
        dataset_name: name of the datset to be downloaded (i.e is it a Lidar, DEM, etc.)
        dataset_format: format of the dataset to be downloaded
        bbox: (minLon, minLat, maxLon, maxLat) in WGS84 (lon/lat).
        

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
