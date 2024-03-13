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
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"{timestamp} - {message}")

def run_python_script(git_path, venv_path, python_script_path):
    
    if not is_git_repo_initialized(git_path):
        log_message("Repository not initialized. Initializing...")
        git_init(git_path)
        log_message("Repository initialized.")
    else:
        log_message("Repository already initialized.")
    
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
        output_file = f"finalizer_{execution_date}.log"
        with open(output_file, 'wb') as out_file:
            out_file.write(f"{process.stdout.read()}\n\n{process.stderr.read()}".encode())

        with open(output_file, "r") as output:
            message = f"<s>[INST]Here is the current code:\n```{file.read()}\n```\nWhen I run the code, this is the current output:\n```\n{output.read()}\n```\nGenerate ONLY a full revision of this code that completely implements all features and addresses issues identified in the output above.\n[/INST]"
        original_code = file.read()
        
    # Get response from web request
    data = {
        'prompt': message,
        'fileContents': original_code
    }
    
    req = Request(client_url, json.dumps(data).encode(), method="POST")
    req.add_header('Content-Type', 'application/json')

    try:
        response = urlopen(req)
        response_content = response.read()
        revised_code = response_content.decode()        
        
        if len(revised_code) < .9 * len(original_code):
            log_message(f"Generated code was too short")
            revised_code = original_code
        elif len(revised_code) > 1.2 * len(original_code) and len(original_code) > 10000:
            log_message(f"Generated code was too long")
            revised_code = original_code
        
        os.remove(python_script_path)
        
        with open(python_script_path, 'w') as new_file:
            new_file.write(revised_code)
            
        git_commit(git_path, "Revision done by Code Reviser UI via finalizer.py")
        log_message("Commit made")
        
    except URLError as e:
        log_message(f"Error: {e}")

def is_git_repo_initialized(path):
    try:
        output = subprocess.check_output(["git", "rev-parse", "--is-initial-branch", path], stderr=subprocess.STDOUT, universal_newlines=True)
        if output:
            return False
        else:
            return True
    except subprocess.CalledProcessError:
        return False

def git_init(path):
    subprocess.check_call(["git", "init", path])
    
def git_commit(path, message):
    subprocess.check_call(["git", "commit", "-m", message, path])

# Run python script and do it again
while True:
    run_python_script(
        "C:\\Files\\source\\unversioned\\snake_game_infinite\\",
        "C:\\Files\\source\\unversioned\\snake_game_infinite\\venv\\scripts",
        "C:\\Files\\source\\unversioned\\snake_game_infinite\\game.py")