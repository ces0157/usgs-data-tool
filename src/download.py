import os
import requests
from tqdm import tqdm

def download_data(type: str, download_information: dict, output_dir:str):
    """
    Download, save and merge (depending on datatypes) the file

    Args:
        type: (lidar, dem) datatype
        
        usgs_Data (Dict): json configuration holding names and format tpes 
        

    Returns:
        list of dicts containing dataset info and download URLs.
    """
    print(f"Downloading {len(download_information)} {type} datasets")
    for i in tqdm(range(0, len(download_information))):
        
        #get the name of the project we are downloading from
        url = download_information[i]["url"]

        project_name = url.split("Projects/")[1].split("/")[0]
        project_dir = output_dir + "/" + type + "/" + project_name
        os.makedirs(project_dir, exist_ok=True)

        filename = os.path.join(project_dir, url.split("/")[-1])
        r = requests.get(url, stream=True, timeout=20)
        r.raise_for_status()   # raise if HTTP error (404, 500, etc.)

        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)



