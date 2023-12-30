import os
import sqlite3
import requests
import tempfile
import uuid
from flask import abort
from multiprocessing import Process
import difflib
from llama_cpp import Llama

from lib import revise_code, build_readme
from globals import active_jobs

def init_db(revisions_db):
    conn = sqlite3.connect(revisions_db)
    c = conn.cursor()
    # Create table for revisions if it doesn't exist, with columns: id, file_name, revision, user_id
    c.execute('''CREATE TABLE IF NOT EXISTS revisions (id INTEGER PRIMARY KEY AUTOINCREMENT, file_name TEXT, revision TEXT, user_id INT)''')  # Add user_id column for authentication
    conn.commit()
    conn.close()

def update_job_status(active_jobs, filename, user_id, status):
    # Update the status of the job in the active jobs list
    for job in active_jobs:
        if job['filename'] == filename and job['user_id'] == user_id:
            job['status'] = status

def generate_code_revision(revisions_db, filename, file_contents, user_id, llm, rounds, prompt):
    """Revise the given file using the LLM model and save it in the SQLite database."""
    
    try:
        code = file_contents.decode('utf-8')

        for _ in range(rounds):
            existing_revision = get_latest_revision(filename, user_id, revisions_db)
            if existing_revision:
                revision = revise_code.run(existing_revision, llm, prompt)
            else:
                save_revision(revisions_db, filename, user_id, code)
                revision = revise_code.run(code, llm, prompt)
            save_revision(revisions_db, filename, user_id, revision)
            code = revision

    except FileNotFoundError:
        handle_job_error(active_jobs, filename, user_id, f"File not found: {filename}")
    except Exception as e:
        handle_job_error(active_jobs, filename, user_id, str(e))

# Helper function to get the latest revision for a given file and user
def get_latest_revision(filename, user_id, revisions_db):
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("SELECT revision FROM revisions WHERE file_name=? AND user_id=? ORDER BY id DESC LIMIT 1", (filename, user_id))
    revision = c.fetchone()
    conn.close()
    return revision[0] if revision else None


def save_revision(revisions_db, filename, user_id, revision):
    """Save a new revision of the given file in the SQLite database."""
    conn = sqlite3.connect(revisions_db)
    c = conn.cursor()
    c.execute("INSERT INTO revisions (file_name, revision, user_id) VALUES (?, ?, ?)", (filename, revision, user_id))
    conn.commit()
    conn.close()

def process_file_and_background_job(max_file_size, filename, file_contents, upload_folder, revisions_db, active_jobs, current_user, rounds, prompt, model_url, model_filename, max_context):
    if not filename:
        abort(400, description="No filename provided")

    file_size = len(file_contents)
    if file_size > max_file_size:
        abort(413, description="File size exceeds the limit.")

    file_path = os.path.join(upload_folder, filename)
    try:
        with open(file_path, 'wb') as file:
            file.write(file_contents)
    except IOError as e:
        abort(500, description=str(e))

    user_id = current_user.id
    background_process = Process(target=process_background_job, args=(revisions_db, upload_folder, filename, file_contents, user_id, active_jobs, rounds, prompt, model_url, model_filename, max_context))
    background_process.start()

    active_jobs.append({
        'filename': filename,
        'user_id': user_id,
        'status': 'Running',
    })

def load_model(model_url, upload_folder, model_filename, max_context):

    model_path = upload_folder + model_filename

    if not os.path.isfile(model_path):
        try:
            response = requests.get(model_url)
            with open(model_path, 'wb') as model_file:
                model_file.write(response.content)
        except Exception as e:
            print("Failed to download or save the model:", str(e))
            return None

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

    try:
        return Llama(model_path, **llama_params)
    except Exception as e:
        print("Failed to create Llama object:", str(e))
        return None

def process_background_job(revisions_db, upload_folder, filename, file_contents, user_id, active_jobs, rounds, prompt, model_url, model_filename, max_context):
    
    try:
        update_job_status(active_jobs, filename, user_id, 'Processing...')

        llm = load_model(model_url, upload_folder, model_filename, max_context)        

        generate_code_revision(revisions_db, filename, file_contents, user_id, llm, rounds, prompt)
        update_job_status(active_jobs, filename, user_id, 'Completed')
    except Exception as e:
        handle_job_error(active_jobs, filename, user_id, str(e))

def cleanup_uploaded_file(filename):
    abs_filepath = os.path.abspath(filename)
    os.remove(abs_filepath)

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
    c.execute("SELECT id, revision, file_name FROM revisions WHERE user_id=?", (str(user_id)))
    revisions = c.fetchall()
    conn.close()
    return revisions


# Helper function to download a specific revision
def download_revision_file(revisions_db, filename, revision_id, user_id):
    print(revisions_db)
    print(filename)
    print(revision_id)
    print(user_id)
    conn = connect_db(revisions_db)
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
def delete_revision_file(revisions_db, filename, revision_id, user_id):
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("DELETE FROM revisions WHERE id=? AND file_name=? AND user_id=?", (revision_id, filename, user_id))
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Revision deleted.'}

def update_revision_content(revisions_db, filename, revision_id, user_id, new_content):
    """Update the content of a specific revision in the SQLite database."""
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("UPDATE revisions SET revision=? WHERE id=? AND file_name=? AND user_id=?", (new_content, revision_id, filename, user_id))
    conn.commit()
    conn.close()

def get_revision_content(revisions_db, filename, revision_id, user_id):
    """Retrieve the content of a specific revision from the SQLite database."""
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("SELECT revision FROM revisions WHERE id=? AND file_name=? AND user_id=?", (revision_id, filename, user_id))
    revision_content = c.fetchone()
    conn.close()
    return revision_content[0] if revision_content else None

def get_revision_content_bytes(revisions_db, filename, revision_id, user_id):
    """Retrieve the content of a specific revision from the SQLite database as bytes."""
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("SELECT revision FROM revisions WHERE id=? AND file_name=? AND user_id=?", (revision_id, filename, user_id))
    revision_content = c.fetchone()
    conn.close()
    return revision_content[0].encode() if revision_content else None

def compare_two_revisions(revisions_db, filename, revision_id1, revision_id2, user_id, context):
    """Compare two revisions using the compare_texts.run function."""
    content1 = get_revision_content(revisions_db, filename, revision_id1, user_id)
    content2 = get_revision_content(revisions_db, filename, revision_id2, user_id)
    
    differ = difflib.HtmlDiff()
    comparison_result = differ.make_file(content2.splitlines(), content1.splitlines(), context=context)

    return comparison_result