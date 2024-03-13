import os
import sys
import time
import datetime
import json
import re
import logging
import subprocess
from urllib.request import Request, urlopen
from urllib.error import URLError

# Define variables
client_url = "http://127.0.0.1:5031/process_request"
output_path = "finalizer/output"
logging.basicConfig(filename='finalizer.log', level=logging.INFO)

def log_message(message):
    logging.info(message)

def run_python_script(python_script_path):
    
    execution_date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Activate virtual environment
    venv_path = os.path.join(os.getcwd(), "/venv/scripts")
    os.chdir(venv_path)
    os.system("activate")

    # Run python script and pipe output to a datetime_stamped file
    script_args = [sys.executable, python_script_path]
    script_args += sys.argv[1:]
    with open(python_script_path, 'r') as file:
        process = subprocess.Popen(script_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()
        output_file = os.path.join(output_path, f"{execution_date}.log")
        with open(output_file, 'wb') as out_file:
            out_file.write(process.stdout.read())

            message = f'''
<s>[INST]Here is the current code:
```
{file.read()}
```
When I run the code, this is the current output:
```
{outfile.read()}
```
Generate ONLY a full revision of this code that completely implements all features and addresses issues identified in the output above.
[/INST]
'''

        # Get response from web request
        data = {
            'prompt': message,
            'fileContents': file.read()
        }
        
        req = Request(client_url, json.dumps(data).encode(), method="POST")

        try:
            response = urlopen(req)
            response_content = response.read()
            revision = response_content.decode()
            log_message(f"Revision:\n\n{revision}")
            
            os.rename(python_script_path, os.path.join(output_path, f"{execution_date}{python_script_path}"))
            with open(python_script_path, 'w') as new_file:
                new_file.write(revision)
        except URLError as e:
            log_message(f"Error: {e}")

# Run python script and do it again
while True:
    run_python_script("game.py")