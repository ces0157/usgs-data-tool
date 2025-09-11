import json
import glob
import pdal
import os

def merge_lidar(folders: list[str], keep_files: bool):
 
    """
    Merge files in lidar pointcloud and save to a new file

    Args:
        folders: list of all the project folders (one merge per each folder)
        keep_files: weather to keep the original files afterwards
        

    Returns:
        list of dicts containing dataset info and download URLs.
    """
    for input_dir in folders:
        print(f"Merging laz files in {input_dir} ")
        output_file = input_dir + "/merged.laz"
        
        lidar_dir = input_dir + "/*.laz"
        files = glob.glob(lidar_dir)
        if not files:
            raise FileNotFoundError(f"No .laz files found in {lidar_dir}")
        
        readers = [{"type": "readers.las", "filename": f} for f in files]

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

        print(f"Merged {len(files)} files into {output_file}")
        print(f"Total points written: {count}")

        if not keep_files:
            print("Removing files")
            for filename in os.listdir(input_dir):
                file_path = os.path.join(input_dir, filename)

                print(filename)
                print(output_file)
                # Delete only if it's a file and not the one to keep
                if os.path.isfile(file_path) and file_path != output_file:
                    os.remove(file_path)
                        
