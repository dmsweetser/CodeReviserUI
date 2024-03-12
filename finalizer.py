import os
import sys
import time
import datetime
import json
import re
import logging
import subprocess
import tempfile
import hashlib
from urllib.request import Request, urlopen
from urllib.error import URLError
from db import save_revision, load_revision

# Define variables
client_url = "http://example.com/process_request"
message = "Custom message"

logging.basicConfig(filename='job.log', level=logging.INFO)

def log_message(message):
    logging.info(message)

def run_python_script(python_script_path, output_file_prefix):
    # Activate virtual environment
    venv_path = os.path.join(os.getcwd(), "/venv/scripts")
    os.chdir(venv_path)
    os.system("activate")

    # Get current file hash to identify the file to be updated
    current_file_hash = hashlib.md5(open(python_script_path, 'rb').read()).hexdigest()

    # Run python script and pipe output to a datetime_stamped file
    script_args = [sys.executable, python_script_path]
    script_args += sys.argv[1:]
    with tempfile() as tmp_file:
        script_args += [ "--logfile", tmp_file.name ]
        process = subprocess.Popen(script_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()
        output_file = os.path.join("output", f"{output_file_prefix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        with open(output_file, 'wb') as out_file:
            out_file.write(process.stdout.read())

        # Get response from web request
        data = {
            'prompt': message,
            'fileName': os.path.basename(python_script_path),
            'fileHash': current_file_hash,
            'fileContents': open(tmp_file.name, 'rb').read()
        }
        req = Request(client_url, json.dumps(data).encode(), method="POST")

        try:
            response = urlopen(req)
            response_content = response.read()
            revision = response_content.decode()
            log_message("Job completed.")

            # Archive old python script and replace it with new version containing just the response
            new_python_script_path = os.path.join("path/to/python/scripts", f"new_{os.path.basename(python_script_path)}")
            with open(new_python_script_path, 'w') as new_file:
                new_file.write(revision)
                os.remove(python_script_path)
                os.rename(new_python_script_path, python_script_path)
        except URLError as e:
            log_message(f"Error: {e}")
            os.remove(tmp_file.name)

# Run python script and do it again
run_python_script("game.py", "output_")