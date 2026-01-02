"""Shared utilities for USGS Data Tool."""

import os
from typing import Dict, List, Any, Tuple
from pyproj import Transformer
from pyproj.exceptions import CRSError

from exceptions import CRSTransformationError


def append_to_dict_list(d: Dict[str, List], key: str, value: Any) -> None:
    """
    Append value to a list in dictionary, creating list if key doesn't exist.

    Args:
        d: Dictionary with list values.
        key: Key to append value to.
        value: Value to append.

    Example:
        >>> d = {}
        >>> append_to_dict_list(d, "folder1", "file1.tif")
        >>> append_to_dict_list(d, "folder1", "file2.tif")
        >>> d
        {'folder1': ['file1.tif', 'file2.tif']}
    """
    if key not in d:
        d[key] = []
    d[key].append(value)


def should_keep_file(filename: str, file_type: str, keep_merged: bool = True) -> bool:
    """
    Determine if a file should be kept based on filtering criteria.

    Args:
        filename: Name of the file to check.
        file_type: Target file type to keep (tif, png, r16).
        keep_merged: Whether to keep merged files.

    Returns:
        True if file should be kept, False otherwise.
    """
    filename_lower = filename.lower()

    # Always remove XML files
    if "xml" in filename_lower:
        return False

    # If keeping merged files, check for merged prefix
    if keep_merged:
        if "merged" in filename_lower and file_type in filename_lower:
            return True
        return False

    return file_type in filename_lower


def get_files_to_remove(directory: str, file_type: str, keep_merged: bool = True) -> List[str]:
    """
    Get list of files to remove from directory based on filter criteria.

    Args:
        directory: Directory to check.
        file_type: File type to keep (tif, png, r16).
        keep_merged: Whether to keep merged files.

    Returns:
        List of absolute paths to files that should be removed.
    """
    to_remove = []

    if not os.path.exists(directory):
        return to_remove

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            if not should_keep_file(filename, file_type, keep_merged):
                to_remove.append(filepath)

    return to_remove


def safe_remove_files(file_paths: List[str]) -> int:
    """
    Safely remove a list of files, handling errors gracefully.

    Args:
        file_paths: List of file paths to remove.

    Returns:
        Number of files successfully removed.
    """
    removed_count = 0
    for filepath in file_paths:
        try:
            os.remove(filepath)
            removed_count += 1
        except OSError as e:
            print(f"Warning: Could not remove {filepath}: {e}")

    return removed_count


class CoordinateTransformer:
    """Utility for transforming coordinates between CRS with caching."""

    _cache: Dict[Tuple[str, str], Transformer] = {}

    @classmethod
    def get_transformer(cls, from_crs: str, to_crs: str) -> Transformer:
        """
        Get cached transformer for CRS pair.

        Args:
            from_crs: Source CRS (e.g., "EPSG:4326").
            to_crs: Target CRS (e.g., "EPSG:26917").

        Returns:
            Transformer object for the CRS pair.

        Raises:
            CRSTransformationError: If transformer cannot be created.
        """
        key = (from_crs, to_crs)
        if key not in cls._cache:
            try:
                cls._cache[key] = Transformer.from_crs(from_crs, to_crs, always_xy=True)
            except CRSError as e:
                raise CRSTransformationError(f"Failed to create transformer from {from_crs} to {to_crs}: {e}")
        return cls._cache[key]

    @classmethod
    def transform_bbox(
        cls,
        bbox: Tuple[float, float, float, float],
        from_crs: str,
        to_crs: str
    ) -> Tuple[float, float, float, float]:
        """
        Transform bounding box coordinates.

        Args:
            bbox: (minX, minY, maxX, maxY) in source CRS.
            from_crs: Source CRS (e.g., "EPSG:4326").
            to_crs: Target CRS (e.g., "EPSG:26917").

        Returns:
            Transformed (minX, minY, maxX, maxY) tuple.

        Raises:
            CRSTransformationError: If transformation fails.
        """
        try:
            transformer = cls.get_transformer(from_crs, to_crs)
            minX, minY = transformer.transform(bbox[0], bbox[1])
            maxX, maxY = transformer.transform(bbox[2], bbox[3])
            return (minX, minY, maxX, maxY)
        except Exception as e:
            raise CRSTransformationError(f"Coordinate transformation failed: {e}")

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the transformer cache."""
        cls._cache.clear()
