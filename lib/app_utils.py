import os
import sqlite3
import requests
import tempfile
import uuid
from flask import abort
from llama_cpp import Llama
from multiprocessing import Process
from lib import revise_prompt, compare_texts, revise_code, build_readme

def init_db(revisions_db):
    conn = sqlite3.connect(revisions_db)
    c = conn.cursor()
    # Create table for revisions if it doesn't exist, with columns: id, file_name, revision, user_id
    c.execute('''CREATE TABLE IF NOT EXISTS revisions (id INTEGER PRIMARY KEY AUTOINCREMENT, file_name TEXT, revision TEXT, user_id INT)''')  # Add user_id column for authentication
    conn.commit()
    conn.close()


def load_model(model_url, upload_folder, model_filename, max_context):
    llm = None
    if not os.path.isfile(upload_folder + model_filename):
        try:
            response = requests.get(model_url)
            open(upload_folder + model_filename, 'wb').write(response.content)
        except Exception as e:
            print("Failed to download model:", str(e))
            return None
    try:

        # Define llama.cpp parameters
        llama_params = {
            "loader": "llama.cpp",
            "cpu": False,
            "threads": 0,
            "threads_batch": 0,
            "n_batch": 512,
            "no_mmap": False,
            "mlock": False,
            "no_mul_mat_q": False,
            "n_gpu_layers": 0,
            "tensor_split": "",
            "n_ctx": max_context,
            "compress_pos_emb": 1,
            "alpha_value": 1,
            "rope_freq_base": 0,
            "numa": False,
            "model": model_filename,
            "temperature": 1.0,
            "top_p": 0.99,
            "top_k": 85,
            "repetition_penalty": 1.01,
            "typical_p": 0.68,
            "tfs": 0.68,
            "max_tokens": max_context
        }

        llm = Llama(upload_folder + model_filename, **llama_params)

    except FileNotFoundError:
        print("Model file not found locally, downloading...")
        return load_model(model_url, upload_folder, model_filename, max_context)

    return llm


def update_job_status(active_jobs, filename, user_id, status):
    # Update the status of the job in the active jobs list
    for job in active_jobs:
        if job['filename'] == filename and job['user_id'] == user_id:
            job['status'] = status

# Helper functions for revising code and saving revisions in SQLite database
def generate_code_revision(revisions_db, upload_folder, filename, user_id):
    """Revise the given file using the LLM model and save it in the SQLite database."""
    with open(os.path.join(upload_folder, filename), 'r') as file:
        code = file.read()
    revision = revise_code.run(code, llm)
    save_revision(filename, user_id, revision)  # Save the revision in SQLite database

def save_revision(revisions_db, filename, user_id, revision):
    """Save a new revision of the given file in the SQLite database."""
    conn = sqlite3.connect(revisions_db)
    c = conn.cursor()
    c.execute("INSERT INTO revisions (file_name, revision, user_id) VALUES (?, ?, ?)", (filename, revision, user_id))
    conn.commit()
    conn.close()

def process_background_job(revisions_db, upload_folder, filename, user_id, active_jobs, llm):
    try:
        update_job_status(active_jobs, filename, user_id, 'Processing...')
        generate_code_revision(revisions_db, upload_folder, filename, user_id, llm)
        cleanup_uploaded_file(upload_folder, filename)
        update_job_status(active_jobs, filename, user_id, 'Completed')
    except Exception as e:
        handle_job_error(active_jobs, filename, user_id, str(e))

def cleanup_uploaded_file(upload_folder, filename):
    os.remove(os.path.join(upload_folder, filename))

def handle_job_error(active_jobs, filename, user_id, error_message):
    print(f"Error processing job: {error_message}")
    update_job_status(active_jobs, filename, user_id, f'Error: {error_message}')

# Helper function to connect to the revisions database
def connect_db(revisions_db):
    return sqlite3.connect(revisions_db)

# Helper function to get revisions for a given user
def get_all_revisions(user_id, revisions_db):
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("SELECT id, revision FROM revisions WHERE user_id=?", (str(user_id)))
    revisions = c.fetchall()
    conn.close()
    return revisions


# Helper function to download a specific revision
def download_revision_file(filename, revision_id, user_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT revision FROM revisions WHERE id=? AND file_name=? AND user_id=?", (revision_id, filename, user_id))
    revision = c.fetchone()[0]
    conn.close()

    if not revision:
        abort(404, description="Revision not found")

    temp_file = tempfile.TemporaryFile()
    temp_file.write(revision.encode())
    temp_file.seek(0)
    return temp_file

# Helper function to delete a specific revision
def delete_revision_file(filename, revision_id, user_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("DELETE FROM revisions WHERE id=? AND file_name=? AND user_id=?", (revision_id, filename, user_id))
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Revision deleted.'}