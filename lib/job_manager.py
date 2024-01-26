import os
import json
import time
import base64
from multiprocessing import Process, Queue
from flask import abort
from lib.config_manager import load_config, get_config
from lib.app_utils import *
import gc
from itertools import cycle
import ast
from threading import Lock

def load_jobs():
    jobs = []

    try:
        config = load_config()
        job_file = get_config("job_file", "jobs.json")

        with open(job_file, 'r') as json_file:
            data = json.load(json_file)

        for request_data in data:
            jobs.append({
                'job_id': request_data['job_id'],
                'filename': request_data['filename'],
                'status': request_data['status'],
                'rounds': request_data['rounds'],
                'prompt': request_data['prompt']
            })
    except FileNotFoundError:
        # Handle if the file is not found (initial case)
        pass

    # Define a custom sorting order for statuses
    status_order = {'NEW': 0, 'STARTED': 1, 'FINISHED': 2, 'ERROR': 3}

    # Sort the list of dictionaries based on the custom sorting order and 'rounds'
    sorted_jobs = sorted(jobs, key=lambda x: (status_order[x['status']], x['rounds']))

    return sorted_jobs

# Create a lock
update_job_status_lock = Lock()

def update_job_status(job_file, job_id, status, rounds=None):
    with update_job_status_lock:
        existing_contents = []
        if os.path.exists(job_file):
            with open(job_file, 'r') as existing_file:
                existing_contents = json.load(existing_file)

        for job in existing_contents:
            if job.get('job_id') == job_id:
                job['status'] = status
                if rounds is not None:
                    job['rounds'] = rounds
                break

        with open(job_file, 'w') as json_file:
            json.dump(existing_contents, json_file, indent=2)

def start_batch_job(revisions_db, model_folder, model_url, model_filename, max_context):

    config = load_config()
    job_file = get_config("job_file", "jobs.json")

    batch_process = Process(target=process_batch, args=(job_file, revisions_db, model_folder, model_url, model_filename, max_context))
    batch_process.start()

def add_job(max_file_size, filename, file_contents, model_folder, revisions_db, current_user, rounds, prompt):
    if not filename:
        abort(400, description="No filename provided")

    file_size = len(file_contents)
    if file_size > int(max_file_size):
        abort(413, description="File size exceeds the limit.")

    user_id = current_user.id

    config = load_config()
    job_file = get_config("job_file", "jobs.json")

    save_request_to_json(job_file, filename, file_contents, user_id, rounds, prompt)

def save_request_to_json(batch_requests_file, filename, file_contents, user_id, rounds, prompt):
    # Load existing contents if the file exists
    existing_contents = []
    if os.path.exists(batch_requests_file):
        with open(batch_requests_file, 'r') as existing_file:
            existing_contents = json.load(existing_file)

    encoded_contents = base64.b64encode(file_contents).decode('utf-8')

    # Generate a unique ID using current ticks
    job_id = int(time.time() * 1000)

    request_data = {
        'job_id': job_id,
        'filename': filename,
        'file_contents': encoded_contents,
        'user_id': user_id,
        'rounds': rounds,
        'prompt': prompt,
        'status': 'NEW'
    }

    existing_contents.append(request_data)

    with open(batch_requests_file, 'w') as json_file:
        json.dump(existing_contents, json_file, indent=2)

def clear_job(job_id):
    config = load_config()
    batch_requests_file = get_config("job_file", "jobs.json")

    # Clear a specific job based on job_id
    existing_contents = []
    if os.path.exists(batch_requests_file):
        with open(batch_requests_file, 'r') as existing_file:
            existing_contents = json.load(existing_file)

    # Find and remove the job with the specified job_id
    existing_contents = [job for job in existing_contents if job.get('job_id') != job_id]

    # Save the updated contents back to the file
    with open(batch_requests_file, 'w') as json_file:
        json.dump(existing_contents, json_file, indent=2)

def process_batch(batch_requests_file, revisions_db, model_folder, model_url, model_filename, max_context):
    config = load_config()
    batch_requests_file = get_config("job_file", "")

    client_instances = get_config("other_instances","")
    client_instances = ast.literal_eval(client_instances)

    client_queue = Queue()

    if len(client_instances) > 0:

        for client in client_instances:
            client_queue.put(client)

        while True:
            
            with open(batch_requests_file, 'r') as json_file:
                data = json.load(json_file)

            all_finished = all(request_data['status'] == "FINISHED" for request_data in data)

            if all_finished:
                break

            processes = []

            for request_data in data:
                filename = request_data['filename']
                job_id = request_data['job_id']

                current_client = None
                while True:
                    if client_queue.empty():
                        time.sleep(10)
                    else:
                        current_client = client_queue.get()
                        break

                client_url = f'http://{current_client}'

                process = Process(target=process_job, args=(revisions_db, request_data, client_url, client_queue, current_client))
                processes.append(process)
                process.start()

            for process in processes:
                process.join()
    else:
        while True:
            with open(batch_requests_file, 'r') as json_file:
                data = json.load(json_file)

            all_finished = all(request_data['status'] == "FINISHED" for request_data in data)

            if all_finished:
                break

            for request_data in data:
                filename = request_data['filename']
                file_contents = base64.b64decode(job_data['file_contents'])
                if isinstance(file_contents, bytes):
                    file_contents = file_contents.decode('utf-8')
                user_id = request_data['user_id']
                rounds = request_data['rounds']
                prompt = request_data['prompt']
                status = request_data['status']
                job_id = request_data['job_id']

                if status == "FINISHED":
                    continue

                try:
                    update_job_status(batch_requests_file, job_id, "STARTED")
                    print("\n\n\n\n\n")
                    if rounds == -1:
                        llm = load_model(model_url, model_folder, model_filename, max_context, True)
                        generate_code_revision(revisions_db, filename, file_contents, user_id, llm, prompt)
                        del llm
                        gc.collect()
                        time.sleep(10)
                    else:
                        for current_round in range(1, rounds + 1):
                            llm = load_model(model_url, model_folder, model_filename, max_context, True)
                            generate_code_revision(revisions_db, filename, file_contents, user_id, llm, prompt)
                            update_job_status(batch_requests_file, job_id, "STARTED", rounds - current_round)
                            del llm
                            gc.collect()
                            time.sleep(10)
                        update_job_status(batch_requests_file, job_id, "FINISHED")
                except Exception as e:
                    print(str(e))
                    update_job_status(batch_requests_file, job_id, "ERROR")

def process_job(revisions_db, job_data, client_url, client_queue, current_client):

    batch_requests_file = get_config("job_file", "")

    try:
        update_job_status(batch_requests_file, job_data['job_id'], "STARTED")
        print("\n\n\n\n\n")
        filename = job_data['filename']
        file_contents = base64.b64decode(job_data['file_contents'])
        if isinstance(file_contents, bytes):
            file_contents = file_contents.decode('utf-8')
        rounds = job_data['rounds']
        user_id = job_data['user_id']
        prompt = job_data['prompt']

        # Get default prompt from config or use a default value
        default_prompt = get_config('default_prompt', "")
        revision_prompt = get_config('revision_prompt', "") 

        # Check if extracting from Markdown is enabled in config
        extract_from_markdown = get_config('extract_from_markdown', True)

        if "TODO" in file_contents.upper() or "PLACEHOLDER" in file_contents.upper():
            # Use the provided prompt if given, else use the one from config
            prompt = prompt if prompt else revision_prompt
        else:
            # Use the provided prompt if given, else use the one from config
            prompt = prompt if prompt else default_prompt

        message = f"<s>[INST]\n{prompt}\nHere is the current code:\n```\n{file_contents}\n```\n[/INST]\n"

        revisions = get_latest_revisions(filename, user_id, revisions_db)

        if revisions and len(revisions) == 2:
            existing_revision, prior_revision = revisions
            file_contents = existing_revision
        elif revisions and len(revisions) == 1:
            existing_revision = revisions[0]
            file_contents = existing_revision
        else:
            save_revision(revisions_db, filename, user_id, file_contents)

        if client_url.endswith("_OPENAI"):

            if len(message) > 4000:
                client_queue.put(current_client)
                return

            url = client_url.replace("_OPENAI","/v1/completions")
            headers = {
            "Content-Type": "application/json"
            }
            data = {
                "prompt": message,
                "max_tokens": 8196,
                "temperature": get_config('temperature', 1.0),
                "top_p": get_config('top_p', 0.99),
                "top_k": get_config('top_k', 85),
                "repeat_penalty": get_config('repetition_penalty', 0.99),
            }
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                revision = response.json()['choices'][0]['text']
                save_revision(revisions_db, filename, user_id, revision)
                print(f"Job {job_data['job_id']} completed. Result: {revision}")
                if rounds != -1:
                    update_job_status(batch_requests_file, job_data['job_id'], "FINISHED")
            else:
                print(f"Job {job_data['job_id']} failed. Status Code: {response.status_code}")
                update_job_status(batch_requests_file, job_data['job_id'], "ERROR")
        else:
            url = f'{client_url}/process_request'
            data = {
                'prompt': message,
                'fileName': filename,
                'fileContents': file_contents
            }
            response = requests.post(url, data=data)
            if response.status_code == 200:
                revision = response.content.decode()
                save_revision(revisions_db, filename, user_id, revision)
                print(f"Job {job_data['job_id']} completed. Result: {revision}")
                if rounds != -1:
                    update_job_status(batch_requests_file, job_data['job_id'], "FINISHED")
            else:
                print(f"Job {job_data['job_id']} failed. Status Code: {response.status_code}")
                update_job_status(batch_requests_file, job_data['job_id'], "ERROR")
    except Exception as e:
        print(str(e))
        update_job_status(batch_requests_file, job_data['job_id'], "ERROR")

    client_queue.put(current_client)