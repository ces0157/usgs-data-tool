import json
import re
import subprocess
import os
from pathlib import Path

import pdal
from pyproj import CRS

from exceptions import (
    InvalidLASFileError,
    PDALPipelineError,
    MissingMetadataError,
    EPSGDetectionError,
    LiDARError,
    CRSTransformationError
)
from utils import CoordinateTransformer, append_to_dict_list


def safe_execute_pipeline(pipeline_dict: dict, operation_name: str = "pipeline"):
    """
    Execute PDAL pipeline with comprehensive error handling.

    Args:
        pipeline_dict: Dictionary containing the pipeline definition.
        operation_name: Name of the operation for error messages.

    Returns:
        Tuple of (pipeline object, point count).

    Raises:
        PDALPipelineError: If pipeline execution fails.
    """
    try:
        pipeline_json = json.dumps(pipeline_dict)
        pipeline = pdal.Pipeline(pipeline_json)
        count = pipeline.execute()
        return pipeline, count
    except RuntimeError as e:
        error_msg = str(e)
        if "Could not open" in error_msg:
            raise InvalidLASFileError(f"Invalid LAS/LAZ file: {e}")
        raise PDALPipelineError(f"PDAL {operation_name} failed: {e}")
    except json.JSONDecodeError as e:
        raise PDALPipelineError(f"Invalid pipeline configuration: {e}")


def detect_epsg_from_las(path: str) -> str:
    """
    Detect EPSG code from a LAS/LAZ file.

    Args:
        path: Path to the LAS/LAZ file.

    Returns:
        EPSG code string (e.g., "EPSG:26917") or None if not detected.

    Raises:
        InvalidLASFileError: If file cannot be opened or read.
        MissingMetadataError: If no SRS metadata is found.
    """
    if not os.path.exists(path):
        raise InvalidLASFileError(f"LAS file not found: {path}")

    print(f"Detecting EPSG from: {path}")

    pipeline_dict = {"pipeline": [{"type": "readers.las", "filename": path}]}

    try:
        pipeline, _ = safe_execute_pipeline(pipeline_dict, "EPSG detection")
    except PDALPipelineError as e:
        raise InvalidLASFileError(f"Could not read LAS file {path}: {e}")

    try:
        srs = pipeline.metadata["metadata"]["readers.las"]["srs"]
    except (KeyError, TypeError) as e:
        raise MissingMetadataError(f"No SRS metadata in LAS file {path}")

    print(f"SRS metadata: {srs}")
    wkt = srs.get("wkt") or srs.get("horizontal")

    if not wkt:
        return None

    # Try robust EPSG detection via pyproj
    try:
        crs = CRS.from_wkt(wkt)
        epsg = crs.to_epsg()
        if epsg is not None:
            return f"EPSG:{epsg}"
    except Exception:
        pass

    # Fallback: regex for the last AUTHORITY["EPSG","####"]
    matches = re.findall(r'AUTHORITY\s*\[\s*"EPSG"\s*,\s*"(\d+)"\s*\]', wkt)
    if matches:
        return f"EPSG:{matches[-1]}"

    return None


def merge_lidar(files: dict, keep_files: bool) -> dict:
    """
    Merge LiDAR point cloud files and save to a new file.

    Args:
        files: Dictionary where keys are folders and values are lists of filenames.
        keep_files: Whether to keep the original files afterwards.

    Returns:
        Dictionary mapping folders to merged file paths.

    Raises:
        PDALPipelineError: If merge operation fails.
    """
    merged_files = {}

    for key in files:
        print(f"Merging LAZ files in {key}")
        output_file = os.path.join(key, "merged.laz")

        laz_files = files[key]
        if not laz_files:
            print(f"Warning: No files to merge in {key}, skipping...")
            continue

        readers = [{"type": "readers.las", "filename": f} for f in laz_files]

        pipeline_dict = {
            "pipeline": readers + [
                {
                    "type": "writers.las",
                    "filename": output_file,
                    "compression": "laszip"
                }
            ]
        }

        try:
            _, count = safe_execute_pipeline(pipeline_dict, f"merge in {key}")
            merged_files[key] = output_file
            print(f"Merged {len(laz_files)} files into {output_file}")
            print(f"Total points written: {count}")
        except PDALPipelineError as e:
            print(f"Error merging files in {key}: {e}")
            continue

        if not keep_files:
            print("Removing original files")
            for filename in os.listdir(key):
                file_path = os.path.join(key, filename)
                if os.path.isfile(file_path) and file_path != output_file:
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        print(f"Warning: Could not remove {file_path}: {e}")

    return merged_files


def reproject_lidar(files: dict, out_srs: str) -> dict:
    """
    Reproject LiDAR files to a target coordinate reference system.

    Args:
        files: Dictionary where keys are folders and values are lists of filenames.
        out_srs: Target CRS (e.g., "EPSG:26917").

    Returns:
        Dictionary mapping folders to lists of reprojected file paths.

    Raises:
        EPSGDetectionError: If source EPSG cannot be detected.
        PDALPipelineError: If reprojection fails.
    """
    new_files = {}

    for key in files:
        folder = files[key]

        # Legacy files typically do not contain a valid CRS
        if folder and "legacy" in folder[0].lower():
            print(f"Skipping legacy folder: {key}")
            continue

        for i, input_file in enumerate(folder):
            try:
                in_srs = detect_epsg_from_las(input_file)
            except (InvalidLASFileError, MissingMetadataError) as e:
                print(f"Warning: Could not detect EPSG for {input_file}: {e}")
                continue

            if not in_srs:
                print(f"Warning: No EPSG code detected for {input_file}, skipping...")
                continue

            filename = os.path.join(key, f"reprojected{i}.laz")
            print(f"Reprojecting {input_file} to {filename}")

            pipeline_def = {
                "pipeline": [
                    input_file,
                    {
                        "type": "filters.reprojection",
                        "in_srs": in_srs,
                        "out_srs": out_srs
                    },
                    filename
                ]
            }

            append_to_dict_list(new_files, key, filename)

            try:
                _, count = safe_execute_pipeline(pipeline_def, f"reproject {input_file}")
                print(f"Pipeline executed successfully. Points processed: {count}")
            except PDALPipelineError as e:
                print(f"Warning: Reprojection failed for {input_file}: {e}")
                # Remove from new_files list since it failed
                new_files[key].pop()

    return new_files


def filter_lidar(input_clouds: dict, output_cloud_name: str, bounds: tuple) -> None:
    """
    Filter/crop LiDAR point clouds to specified bounds.

    Args:
        input_clouds: Dictionary mapping folders to input cloud paths.
        output_cloud_name: Name for the output cloud file.
        bounds: Bounding box as (minLon, minLat, maxLon, maxLat) in WGS84.

    Raises:
        LiDARError: If filtering fails.
    """
    # Transform bounds from WGS84 to target CRS
    # TODO: Make target CRS configurable instead of hardcoded
    try:
        minE, minN, maxE, maxN = CoordinateTransformer.transform_bbox(
            bounds, "EPSG:4326", "EPSG:26917"
        )
    except CRSTransformationError as e:
        raise LiDARError(f"Failed to transform bounds: {e}")

    print(f"Transformed bounds: {minE}, {minN}, {maxE}, {maxN}")

    for key in input_clouds:
        input_cloud = input_clouds[key]
        output_cloud = os.path.join(key, output_cloud_name)

        pipeline = {
            "pipeline": [
                input_cloud,
                {
                    "type": "filters.crop",
                    "bounds": f"([{minE},{maxE}],[{minN},{maxN}])"
                },
                output_cloud
            ]
        }

        pipeline_file = os.path.join(key, "crop.json")

        # Save pipeline to file
        try:
            with open(pipeline_file, "w") as f:
                json.dump(pipeline, f, indent=4)
        except IOError as e:
            print(f"Warning: Could not write pipeline file {pipeline_file}: {e}")
            continue

        # Run PDAL via subprocess
        try:
            result = subprocess.run(
                ["pdal", "pipeline", pipeline_file],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"Filtered {input_cloud} -> {output_cloud}")
        except subprocess.CalledProcessError as e:
            print(f"Warning: PDAL filter failed for {input_cloud}: {e.stderr}")
        except FileNotFoundError:
            raise LiDARError("PDAL command not found. Ensure PDAL is installed and in PATH.")
