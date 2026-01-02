import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
import os
import json

from exceptions import (
    ConnectionFailedError,
    APITimeoutError,
    InvalidResponseError,
    MissingConfigKeyError
)

BASE_URL = "https://tnmaccess.nationalmap.gov/api/v1/products"

# Request timeout in seconds
REQUEST_TIMEOUT = 30


def fetch_data_list(bbox: tuple, type: str, usgs_data: dict, spec: str = "regular") -> list[dict]:
    """
    Extract dataset type and spec and pass to the dataset types and function

    Args:
        bbox: (minLon, minLat, maxLon, maxLat) in WGS84 (lon/lat).
        type: (lidar, dem) datatype
        usgs_data: json configuration holding names, specs, and format types
        spec: specialization of dataset we are dealing with

    Returns:
        list of dicts containing dataset info and download URLs.

    Raises:
        MissingConfigKeyError: If required keys are missing from usgs_data config.
    """
    try:
        dataset_name = usgs_data[type][spec]["usgs_name"]
        dataset_format = usgs_data[type][spec]["usgs_data_format"]
    except KeyError as e:
        raise MissingConfigKeyError(
            f"Missing required key in usgs_data config: {e}. "
            f"Expected structure: usgs_data['{type}']['{spec}']['usgs_name' | 'usgs_data_format']"
        )

    return fetch_datasets(dataset_name, dataset_format, bbox)


def fetch_datasets(dataset_name: str, dataset_format: str, bbox: tuple) -> list[dict]:
    """
    Query The National Map (TNM) API for given name, format, and bounding box

    Args:
        dataset_name: name of the dataset to be downloaded (i.e is it a Lidar, DEM, etc.)
        dataset_format: format of the dataset to be downloaded
        bbox: (minLon, minLat, maxLon, maxLat) in WGS84 (lon/lat).

    Returns:
        list of dicts containing dataset info and download URLs.

    Raises:
        ConnectionFailedError: If connection to USGS API fails.
        APITimeoutError: If request times out.
        InvalidResponseError: If response is not valid JSON.
    """
    params = {
        "datasets": dataset_name,
        "bbox": ",".join(map(str, bbox)),
        "prodFormats": dataset_format
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except ConnectionError as e:
        raise ConnectionFailedError(f"Failed to connect to USGS API: {e}")
    except Timeout as e:
        raise APITimeoutError(f"Request to USGS API timed out after {REQUEST_TIMEOUT}s: {e}")
    except RequestException as e:
        raise ConnectionFailedError(f"Request to USGS API failed: {e}")

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        raise InvalidResponseError(f"Invalid JSON response from USGS API: {e}")

    results = []
    for item in data.get("items", []):
        results.append({
            "title": item.get("title"),
            "publicationDate": item.get("publicationDate"),
            "format": item.get("prodFormats"),
            "url": item.get("downloadURL")
        })

    return results
