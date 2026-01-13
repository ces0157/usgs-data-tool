import os
import shutil
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, Timeout, RequestException
from urllib3.util.retry import Retry
from urllib.parse import urlparse
from tqdm import tqdm

from lidar.lidar_tools import merge_lidar, reproject_lidar, filter_lidar
from dem.dem_tools import convert_tiff, merge_dem, filter_dem, warp_dem
from utils import append_to_dict_list
from exceptions import (
    DownloadError,
    DownloadInterruptedError,
    DiskSpaceError,
    FileWriteError,
    MalformedURLError,
    ConnectionFailedError
)

# Download settings
DOWNLOAD_TIMEOUT = 60  # seconds
CHUNK_SIZE = 8192
DISK_SPACE_BUFFER = 1.1  # 10% buffer for disk space check


def _load_existing_projects(output_dir: str, data_type: str) -> dict:
    """
    Collect already-downloaded source files so they can be reused and merged.

    Args:
        output_dir: Base output directory.
        data_type: Type of data ("dem" or "lidar").

    Returns:
        Dictionary mapping project directories to lists of file paths.
    """
    projects = {}
    type_dir = os.path.join(output_dir, data_type)

    if not os.path.isdir(type_dir):
        return projects

    for project_name in os.listdir(type_dir):
        project_dir = os.path.join(type_dir, project_name)
        if not os.path.isdir(project_dir):
            continue

        for entry in os.listdir(project_dir):
            full_path = os.path.join(project_dir, entry)
            if not os.path.isfile(full_path):
                continue

            # Only keep original source files, skip merged/filtered outputs
            lower = entry.lower()
            if data_type == "dem":
                if not lower.endswith(".tif") or "merged" in lower or "filtered" in lower or "warped" in lower:
                    continue
            elif data_type == "lidar":
                if not (lower.endswith(".las") or lower.endswith(".laz")):
                    continue
            else:
                continue

            if project_dir not in projects:
                projects[project_dir] = []
            projects[project_dir].append(full_path)

    return projects


def validate_url(url: str) -> bool:
    """
    Validate that a URL has proper structure.

    Args:
        url: URL string to validate.

    Returns:
        True if URL is valid, False otherwise.
    """
    if not url:
        return False
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


def check_disk_space(path: str, required_bytes: int) -> bool:
    """
    Check if sufficient disk space is available.

    Args:
        path: Path to check disk space for.
        required_bytes: Number of bytes required.

    Returns:
        True if sufficient space available, False otherwise.
    """
    try:
        total, used, free = shutil.disk_usage(path)
        return free > required_bytes
    except OSError:
        # If we can't check, proceed anyway
        return True


def extract_project_name(url: str) -> str:
    """
    Extract project name from USGS download URL.

    Args:
        url: USGS download URL.

    Returns:
        Project name extracted from URL.

    Raises:
        MalformedURLError: If URL doesn't contain expected project structure.
    """
    try:
        return url.split("Projects/")[1].split("/")[0]
    except (IndexError, AttributeError):
        raise MalformedURLError(f"Could not extract project name from URL: {url}")


def safe_download(session: requests.Session, url: str, filename: str) -> None:
    """
    Download file with comprehensive error handling.

    Args:
        session: Requests session with retry configuration.
        url: URL to download from.
        filename: Local path to save file.

    Raises:
        MalformedURLError: If URL is invalid.
        DiskSpaceError: If insufficient disk space.
        ConnectionFailedError: If connection fails.
        DownloadInterruptedError: If download is incomplete.
        FileWriteError: If file cannot be written.
    """
    if not validate_url(url):
        raise MalformedURLError(f"Invalid URL format: {url}")

    try:
        r = session.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT, verify=True)
        r.raise_for_status()

        # Check content length for disk space
        content_length = int(r.headers.get('content-length', 0))
        if content_length > 0:
            output_dir = os.path.dirname(filename)
            if not check_disk_space(output_dir, int(content_length * DISK_SPACE_BUFFER)):
                raise DiskSpaceError(
                    f"Insufficient disk space. Need approximately "
                    f"{content_length // (1024*1024)}MB for {filename}"
                )

        bytes_written = 0
        try:
            with open(filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        bytes_written += len(chunk)
        except IOError as e:
            # Clean up partial download
            if os.path.exists(filename):
                os.remove(filename)
            raise FileWriteError(f"Failed to write file {filename}: {e}")

        # Verify download completed
        if content_length > 0 and bytes_written < content_length:
            if os.path.exists(filename):
                os.remove(filename)
            raise DownloadInterruptedError(
                f"Download incomplete: {bytes_written}/{content_length} bytes for {filename}"
            )

    except ConnectionError as e:
        raise ConnectionFailedError(f"Connection failed during download of {url}: {e}")
    except Timeout as e:
        raise ConnectionFailedError(f"Download timed out for {url}: {e}")
    except RequestException as e:
        raise DownloadError(f"Download failed for {url}: {e}")


def create_session() -> requests.Session:
    """
    Create a requests session with retry configuration.

    Returns:
        Configured requests Session.
    """
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def download_data(args, download_information: list, output_dir: str) -> None:
    """
    Download, save and merge (depending on datatypes) the files.

    Args:
        args: Command line arguments from the cli.
        download_information: List of dicts containing dataset info and download URLs.
        output_dir: Base output directory for downloaded files.

    Raises:
        DownloadError: If download fails.
        MalformedURLError: If URL is malformed.
    """
    # Load existing projects to reuse cached data
    dem_project_dirs = _load_existing_projects(output_dir, "dem")
    lidar_project_dirs = _load_existing_projects(output_dir, "lidar")
    code = None  # Track CRS code for lidar reprojection

    print(f"Downloading {len(download_information)} {args.type} datasets")

    session = create_session()

    for i in tqdm(range(len(download_information))):
        title = download_information[i].get('title', '')
        url = download_information[i].get('url')

        if not url:
            print(f"Warning: No URL for item {i}, skipping...")
            continue

        # Determine data type from title
        if "Lidar" in title and "1 Meter" not in title:
            data_type = "lidar"
        else:
            data_type = "dem"

        # Extract project name and create directory
        try:
            project_name = extract_project_name(url)
        except MalformedURLError as e:
            print(f"Warning: {e}, skipping...")
            continue

        project_dir = os.path.join(output_dir, data_type, project_name)
        os.makedirs(project_dir, exist_ok=True)

        filename = os.path.join(project_dir, url.split("/")[-1])

        # Track files by project
        if data_type == "lidar":
            append_to_dict_list(lidar_project_dirs, project_dir, filename)
        else:
            append_to_dict_list(dem_project_dirs, project_dir, filename)

        # Skip downloading if the file already exists (reuse cached data)
        if os.path.exists(filename):
            print(f"Found existing file, skipping download: {filename}")
        else:
            print(f"Saving: {filename}")
            # Download the file
            try:
                safe_download(session, url, filename)
            except DownloadError as e:
                print(f"Error downloading {url}: {e}")
                continue

        # Post-download processing for DEM files
        if data_type == "dem" and args.dem_output != "tif":
            print("Converting file ...")
            output_filename = os.path.join(
                project_dir,
                f"heightmap{len(dem_project_dirs[project_dir])}.{args.dem_output}"
            )
            convert_tiff(filename, args.dem_output, output_filename, args.png_precision)

        if data_type == "dem" and args.dem_filter_type == "all":
            output_filtered = os.path.join(
                project_dir,
                f"heightmap{len(dem_project_dirs[project_dir])}_filtered.tif"
            )
            output_warped = os.path.join(project_dir, "warped.tif")
            code, units = warp_dem([filename], output_warped)
            filter_dem(output_warped, output_filtered, code, args.aoi, args.dem_resolution)

            try:
                os.remove(output_warped)
            except OSError as e:
                print(f"Warning: Could not remove temporary file {output_warped}: {e}")

            if args.dem_output != "tif":
                print("Converting filtered file ...")
                output_filename = os.path.join(
                    project_dir,
                    f"heightmap{len(dem_project_dirs[project_dir])}_filtered.{args.dem_output}"
                )
                convert_tiff(output_filtered, args.dem_output, output_filename, args.png_precision)

    # Merge DEM files if requested
    if (args.type == "dem" or args.type == "both") and args.dem_merge in ("merge-keep", "merge-delete"):
        should_filter = args.dem_filter_type in ("merge", "all")
        if should_filter:
            print("Filtering files")

        keep_files = args.dem_merge == "merge-keep"
        code = merge_dem(
            dem_project_dirs,
            keep_files,
            args.dem_output,
            args.dem_merge_method,
            args.png_precision,
            should_filter,
            args.aoi,
            args.dem_resolution,
            args.yes
        )

    # Reproject LiDAR if requested
    if (args.type == "lidar" or args.type == "both") and args.lidar_reproject == "auto":
        if code:
            print(f"Reprojecting lidar to {code}")
            lidar_project_dirs = reproject_lidar(lidar_project_dirs, code)
        else:
            print("Warning: No CRS code available for lidar reprojection")

    # Merge LiDAR files if requested
    if (args.type == "lidar" or args.type == "both") and args.merge_lidar in ("merge-keep", "merge-delete"):
        keep_files = args.merge_lidar == "merge-keep"
        merged_files = merge_lidar(lidar_project_dirs, keep_files)

        if args.lidar_filter == "filter":
            filter_lidar(merged_files, "merged_filtered.laz", args.aoi)
