import requests

def get_one_meter_dem(bbox, type):
    """
    Query The National Map (TNM) API for given dataset in a given bounding box.

    Args:
        bbox (tuple): (minLon, minLat, maxLon, maxLat) in WGS84 (lon/lat).
        

    Returns:
        list of dicts containing dataset info and download URLs.
    """
    base_url = "https://tnmaccess.nationalmap.gov/api/v1/products"

    params = {
        "datasets": "Lidar Point Cloud (LPC)",
        "bbox": ",".join(map(str, bbox)),
        "prodFormats": "LAS,LAZ"  # DEMs usually available as GeoTIFF
    }

    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return []

    data = response.json()

    #print(data)
    results = []

    for item in data.get("items", []):
        results.append({
            "title": item.get("title"),
            "publicationDate": item.get("publicationDate"),
            "format": item.get("prodFormats"),
            "downloadURL": item.get("downloadURL")
        })

    return results


if __name__ == "__main__":
    # Example AOI: (minLon, minLat, maxLon, maxLat) around Denver, CO
    bbox = (-84.45688,33.62848,-84.40212,33.65607)

    dem_results = get_one_meter_dem(bbox)

    if dem_results:
        for r in dem_results:
            print(f"Title: {r['title']}")
            print(f"Date: {r['publicationDate']}")
            print(f"Format: {r['format']}")
            print(f"Download: {r['downloadURL']}\n")
    else:
        print("No results found.")