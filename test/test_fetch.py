import os
import pytest
import sys
from unittest.mock import patch, call
from data_helpers.fetch_files import fetch_datasets, fetch_data_list  # replace 'your_module' with actual module name
import json
import pdal
import pathlib
import numpy as np


def test_fetch_datasets_regular_dem_length():
    """
    Test the data returned in specifc bounding box matches
    expected USGS output
    """
    
    dataset_name = "Digital Elevation Model (DEM) 1 meter"
    dataset_format = "GeoTIFF"

    bbox = (-84.45688, 33.62848, -84.40212, 33.65607)

    data = fetch_datasets(dataset_name, dataset_format, bbox)
    assert len(data) == 4


def test_fetch_datasets_seamless_dem_length():
    """
    Test the data returned in specifc bounding box matches
    expected USGS output
    """

    dataset_name = "Seamless 1-meter DEM (Limited Availability)"
    dataset_format = "GeoTIFF"

    bbox = (-84.45688, 33.62848, -84.40212, 33.65607)

    data = fetch_datasets(dataset_name, dataset_format, bbox)
    assert len(data) == 0


def test_fetch_datasets_lidar_length():
    """
    Test the data returned in specifc bounding box matches
    expected USGS output
    """
    
    dataset_name = "Lidar Point Cloud (LPC)"
    dataset_format = "LAS,LAZ"

    bbox = (-84.45688, 33.62848, -84.40212, 33.65607)

    data = fetch_datasets(dataset_name, dataset_format, bbox)
    assert len(data) == 50


def test_fetch_data_list_dem_regular():
    dataset_spec = "regular"
    dataset_type = "dem"
    dataset_name = "Digital Elevation Model (DEM) 1 meter"
    dataset_format = "GeoTIFF"
    
    usgs_data = {dataset_type: {dataset_spec: 
                {"usgs_name": dataset_name, "usgs_data_format": dataset_format}}}

    bbox = (-84.45688, 33.62848, -84.40212, 33.65607)

    data = fetch_data_list(bbox, dataset_type, usgs_data, dataset_spec)
    assert len(data) == 4
    

def test_fetch_data_list_dem_seamless():
    dataset_spec = "seamless"
    dataset_type = "dem"
    dataset_name = "Seamless 1-meter DEM (Limited Availability)"
    dataset_format = "GeoTIFF"
    
    usgs_data = {dataset_type: {dataset_spec: 
                {"usgs_name": dataset_name, "usgs_data_format": dataset_format}}}

    bbox = (-84.45688, 33.62848, -84.40212, 33.65607)

    data = fetch_data_list(bbox, dataset_type, usgs_data, dataset_spec)
    assert len(data) == 0


def test_fetch_data_list_lidar():
    dataset_spec = "regular"
    dataset_type = "dem"
    dataset_name = "Lidar Point Cloud (LPC)"
    dataset_format = "LAS,LAZ"
    
    usgs_data = {dataset_type: {dataset_spec: 
                {"usgs_name": dataset_name, "usgs_data_format": dataset_format}}}

    bbox = (-84.45688, 33.62848, -84.40212, 33.65607)

    data = fetch_data_list(bbox, dataset_type, usgs_data, dataset_spec)
    assert len(data) == 50
    


