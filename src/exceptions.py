"""Custom exceptions for USGS Data Tool."""


class USGSDataToolError(Exception):
    """Base exception for all USGS Data Tool errors."""
    pass


# ============================================================================
# Network Errors
# ============================================================================

class NetworkError(USGSDataToolError):
    """Base class for network-related errors."""
    pass


class ConnectionFailedError(NetworkError):
    """Failed to establish connection to USGS API."""
    pass


class APITimeoutError(NetworkError):
    """Request timed out."""
    pass


class InvalidResponseError(NetworkError):
    """Invalid or malformed response from API."""
    pass


# ============================================================================
# Download Errors
# ============================================================================

class DownloadError(USGSDataToolError):
    """Base class for download-related errors."""
    pass


class DownloadInterruptedError(DownloadError):
    """Download was interrupted before completion."""
    pass


class DiskSpaceError(DownloadError):
    """Insufficient disk space for download."""
    pass


class FileWriteError(DownloadError):
    """Failed to write downloaded file."""
    pass


class MalformedURLError(DownloadError):
    """Invalid or malformed download URL."""
    pass


# ============================================================================
# GeoTIFF/DEM Errors
# ============================================================================

class DEMError(USGSDataToolError):
    """Base class for DEM processing errors."""
    pass


class InvalidGeoTIFFError(DEMError):
    """Invalid or corrupted GeoTIFF file."""
    pass


class GDALDriverError(DEMError):
    """Missing or unavailable GDAL driver."""
    pass


class CRSTransformationError(DEMError):
    """Failed to transform coordinate reference system."""
    pass


class ResolutionError(DEMError):
    """Invalid resolution specified."""
    pass


class MergeError(DEMError):
    """Failed to merge DEM files."""
    pass


# ============================================================================
# LiDAR Errors
# ============================================================================

class LiDARError(USGSDataToolError):
    """Base class for LiDAR processing errors."""
    pass


class InvalidLASFileError(LiDARError):
    """Invalid or corrupted LAS/LAZ file."""
    pass


class PDALPipelineError(LiDARError):
    """PDAL pipeline execution failed."""
    pass


class MissingMetadataError(LiDARError):
    """Required metadata missing from LiDAR file."""
    pass


class EPSGDetectionError(LiDARError):
    """Failed to detect EPSG code from LiDAR file."""
    pass


# ============================================================================
# Configuration Errors
# ============================================================================

class ConfigError(USGSDataToolError):
    """Base class for configuration errors."""
    pass


class ConfigNotFoundError(ConfigError):
    """Configuration file not found."""
    pass


class InvalidConfigError(ConfigError):
    """Configuration file is invalid or malformed."""
    pass


class MissingConfigKeyError(ConfigError):
    """Required key missing from configuration."""
    pass
