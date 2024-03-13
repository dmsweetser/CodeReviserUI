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
logging.basicConfig(filename='finalizer.log', level=logging.INFO)

def log_message(message):
    logging.info(message)

def run_python_script(venv_path, python_script_path, output_path):
    os.makedirs(output_path, exist_ok=True)
    execution_date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Activate virtual environment
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
            out_file.write(f"{process.stdout.read()}\n\n{process.stderr.read()}".encode())

        with open(output_file, "r") as output:
            message = f"<s>[INST]Here is the current code:\n```{file.read()}\n```\nWhen I run the code, this is the current output:\n```\n{output.read()}\n```\nGenerate ONLY a full revision of this code that completely implements all features and addresses issues identified in the output above.\n[/INST]"
        file_contents = file.read()
        logging.info(message)
        
    # Get response from web request
    data = {
        'prompt': message,
        'fileContents': file_contents
    }
    
    req = Request(client_url, json.dumps(data).encode(), method="POST")
    req.add_header('Content-Type', 'application/json')

    try:
        response = urlopen(req)
        response_content = response.read()
        revision = response_content.decode()
        log_message(f"Revision:\n\n{revision}")
        
        os.rename(python_script_path, os.path.join(output_path, f"{execution_date}{os.path.basename(python_script_path)}"))
        with open(python_script_path, 'w') as new_file:
            new_file.write(revision)
    except URLError as e:
        log_message(f"Error: {e}")

# Run python script and do it again
while True:
    run_python_script(
        "C:\\Files\\source\\unversioned\\snake_game_infinite\\venv\\scripts",
        "C:\\Files\\source\\unversioned\\snake_game_infinite\\game.py",
        "C:\\Files\\source\\unversioned\\snake_game_infinite\\finalizer\\")