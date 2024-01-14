import os
import json
import time
import base64
from multiprocessing import Process
from flask import abort
from lib.config_manager import load_config, get_config
from lib.app_utils import *
import gc

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

def update_job_status(job_file, job_id, status, rounds=None):
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
    batch_requests_file = get_config("job_file", "jobs.json")

    while True:
        with open(batch_requests_file, 'r') as json_file:
            data = json.load(json_file)

        all_finished = all(request_data['status'] == "FINISHED" for request_data in data)

        if all_finished:
            break

        for request_data in data:
            filename = request_data['filename']
            file_contents = base64.b64decode(request_data['file_contents'])
            user_id = request_data['user_id']
            rounds = request_data['rounds']
            prompt = request_data['prompt']
            status = request_data['status']
            job_id = request_data['job_id']

            if status == "FINISHED":
                continue

            try:
                update_job_status(batch_requests_file, job_id, "STARTED")

                if rounds == -1:
                    llm = load_model(model_url, model_folder, model_filename, max_context)
                    generate_code_revision(revisions_db, filename, file_contents, user_id, llm, prompt)
                    update_job_status(batch_requests_file, job_id, "FINISHED")
                    del llm
                    gc.collect()
                    time.sleep(10)
                else:
                    for current_round in range(1, rounds + 1):
                        llm = load_model(model_url, model_folder, model_filename, max_context)
                        generate_code_revision(revisions_db, filename, file_contents, user_id, llm, prompt)
                        update_job_status(batch_requests_file, job_id, "STARTED", rounds - current_round)
                        del llm
                        gc.collect()
                        time.sleep(10)
                    update_job_status(batch_requests_file, job_id, "FINISHED")
            except Exception as e:
                print(str(e))
                update_job_status(batch_requests_file, job_id, "ERROR")