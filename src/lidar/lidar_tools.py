import json, re
import glob
import pdal
from pathlib import Path
import os 
from pyproj import CRS

def detect_epsg_from_las(path):
    print(path)
    pipeline_dict = {"pipeline": [{"type": "readers.las", "filename": path}]}
    pipeline = pdal.Pipeline(json.dumps(pipeline_dict))
    pipeline.execute()

    srs = pipeline.metadata["metadata"]["readers.las"]["srs"]

    print(srs)
    wkt = srs.get("wkt") or srs.get("horizontal")  # depending on PDAL version

    if not wkt:
        return None

    # 1) Try robust EPSG detection via pyproj
    try:
        crs = CRS.from_wkt(wkt)
        epsg = crs.to_epsg()  # returns int or None
        if epsg is not None:
            return f"EPSG:{epsg}"
    except Exception:
        pass

    # 2) Fallback: regex for the last AUTHORITY["EPSG","####"]
    matches = re.findall(r'AUTHORITY\s*\[\s*"EPSG"\s*,\s*"(\d+)"\s*\]', wkt)
    if matches:
        return f"EPSG:{matches[-1]}"  # usually the projected CRS code is last

    return None


def merge_lidar(files: dict , keep_files: bool):
 
    """
    Merge files in lidar pointcloud and save to a new file

    Args:
        dictonary where the keys are folders and the filenames are the value
        keep_files: weather to keep the original files afterwards
        
    """
    for key in files:
        print(f"Merging laz files in {key} ")
        output_file = key + "/merged.laz"
        
        #lidar_dir = input_dir + "/*.laz"
        #files = glob.glob(lidar_dir)
        # if not files:
        #     raise FileNotFoundError(f"No .laz files found in {lidar_dir}")
        
        laz_files = files[key]
        
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

        # Convert to JSON string
        pipeline_json = json.dumps(pipeline_dict)

        # Run PDAL pipeline
        pipeline = pdal.Pipeline(pipeline_json)
        count = pipeline.execute()

        print(f"Merged {len(laz_files)} files into {output_file}")
        print(f"Total points written: {count}")

        if not keep_files:
            print("Removing files")
            for filename in os.listdir(key):
                file_path = os.path.join(key, filename)

                # Delete only if it's a file and not the one to keep
                if os.path.isfile(file_path) and file_path != output_file:
                    os.remove(file_path)



def reproject_lidar(files: dict, out_srs):
    new_files = {}
    for key in files:
        folder = files[key]
        #legacy files typically do not contain a valid CRS
        if "legacy" in folder[0]:
            continue
        
        for i in range(0, len(folder)):
            in_srs = detect_epsg_from_las(folder[i])


            
            filename = f"{key}/reprojected{i}.laz"
            print(filename)
            print(key)
            pipeline_def = {
                "pipeline": [
                    folder[i],
                    {
                        "type": "filters.reprojection",
                        "in_srs": in_srs,      # Georgia West ftUS
                        "out_srs": out_srs     # UTM 17N meters
                    },
                    filename
                ]
            }

            if key in new_files:
                new_files[key].append(filename)
            else:
                new_files[key] = [filename]
        

            # Convert pipeline to JSON
            pipeline_json = json.dumps(pipeline_def)

            # Create PDAL pipeline object
            pipeline = pdal.Pipeline(pipeline_json)

            # Execute pipeline
            try:
                #pipeline.validate()     # Optional but useful
                count = pipeline.execute()
                print(f"Pipeline executed successfully.")
                print(f"Points processed: {count}")
            except Exception as e:
                print("Pipeline execution failed:")
                print(e)

            
    return new_files
            


# def filter_lidar(input_cloud, output_cloud, bounds):
#     """
#     Filter a pointcloud to be within the specified bounds

#     Args:
#         dictonary where the keys are folders and the filenames are the value
#         keep_files: weather to keep the original files afterwards
        
#     """


#     in_crs = detect_crs(input_cloud)
#     print("Filtering input cloud")
#     pipeline_dict = {
#     "pipeline": [
#         {"type": "readers.las", "filename": input_cloud},
#         {
#             "type": "filters.reprojection",
#             "in_srs": in_crs,
#             "out_srs": "EPSG:4326"
#         },
#         {
#             "type": "filters.crop",
#             "bounds": f"([{bounds[0]}, {bounds[2]}], [{bounds[1]}, {bounds[3]}])"
#         },
#         #we are converting back for easy cloud compare viewing
#         {
#             "type": "filters.reprojection",
#             "in_srs": "EPSG:4326",
#             "out_srs": in_crs
#         },
#         {
#             "type": "writers.las",
#             "filename": output_cloud
#         }
#     ]
#     }



#     pipeline = pdal.Pipeline(json.dumps(pipeline_dict))
#     pipeline.execute()

#     arrays = pipeline.arrays  # numpy arrays of filtered point
#     print("Saving filtered point cloud")
#     pts = arrays[0]

#     if len(pts["X"]) != 0:
#         print("X:", float(pts["X"].min()), float(pts["X"].max()))
#         print("Y:", float(pts["Y"].min()), float(pts["Y"].max()))
#         print("Z:", float(pts["Z"].min()), float(pts["Z"].max()))                    
