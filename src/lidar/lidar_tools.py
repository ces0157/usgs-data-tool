import json
import glob
import pdal
import os

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
                        
