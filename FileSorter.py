import os
import zipfile
import tempfile
from shutil import copy2, rmtree
from pathlib import Path
from datetime import datetime

def traverse_and_collect(input_dir, output_dir):
    collected_files = []

    def process_file(file_path, relative_path):
        # Get file information
        file_name = os.path.basename(file_path)
        last_modified = os.path.getmtime(file_path)

        # Read the file contents
        with open(file_path, 'rb') as file:
            file_contents = file.read()

        # Append to the collection
        collected_files.append({
            'filename': file_name,
            'last_modified': last_modified,
            'contents': file_contents
        })

    def process_zip(zip_path, output_subdir=""):
        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(temp_dir)

                # If the file is a zip, process its contents
                if file.lower().endswith('.zip'):
                    # Flatten hierarchy by not passing output_subdir
                    process_zip(file_path)
                else:
                    # Process regular file
                    process_file(file_path, relative_path)

        # Clean up the temporary directory
        rmtree(temp_dir)

    # Traverse the directory
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, input_dir)

            # If the file is a zip, process its contents
            if file.lower().endswith('.zip'):
                process_zip(file_path)
            else:
                # Process regular file
                process_file(file_path, relative_path)

    # Sort collected files by last modified timestamp
    collected_files.sort(key=lambda x: x['last_modified'])

    # Output to the Sorted directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for file_info in collected_files:
        filename = file_info['filename']
        timestamp = file_info['last_modified']
        contents = file_info['contents']

        # Retain the original file extension
        _, file_extension = os.path.splitext(filename)

        # Convert timestamp to datetime for a readable format
        dt_object = datetime.fromtimestamp(timestamp)
        timestamp_str = dt_object.strftime("%Y%m%d%H%M%S")

        new_file_name = f"{filename.replace('.', '_')}_timestamp_{timestamp_str}{file_extension}"
        destination_path = os.path.join(output_dir, new_file_name)

        # Write the contents to the Sorted directory
        with open(destination_path, 'wb') as output_file:
            output_file.write(contents)

        print(f"Processed file: {new_file_name}")

if __name__ == "__main__":
    input_directory = "Original"
    output_directory = "Sorted"

    traverse_and_collect(input_directory, output_directory)
