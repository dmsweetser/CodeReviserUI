import os
import sqlite3
import requests
import tempfile
from flask import abort
import psutil
import difflib
from markupsafe import escape

from llama_cpp import Llama

from lib.config_manager import *
from lib.job_manager import *

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def find_process_by_port(port):
    port = int(port)
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.status == 'LISTEN':
            process = psutil.Process(conn.pid)
            return process.name(), process.pid
    return None, None

def init_db(revisions_db):
    conn = sqlite3.connect(revisions_db)
    c = conn.cursor()
    # Create table for revisions if it doesn't exist, with columns: id, file_name, revision, user_id
    c.execute('''CREATE TABLE IF NOT EXISTS revisions (id INTEGER PRIMARY KEY AUTOINCREMENT, file_name TEXT, revision TEXT, user_id INT, initial_instruction TEXT)''')  # Add user_id column for authentication
    conn.commit()
    conn.close()
    
def get_latest_revision(filename, user_id, revisions_db, count=2):
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("SELECT revision, initial_instruction FROM revisions WHERE file_name=? AND user_id=? ORDER BY id DESC LIMIT ?", (filename, user_id, count))
    revision = c.fetchmany(1)
    conn.close()

    if revision:
        return revision
    else:
        return None
    
def save_revision(revisions_db, filename, user_id, revision, initial_instruction):
    """Save a new revision of the given file in the SQLite database."""
    conn = sqlite3.connect(revisions_db)
    c = conn.cursor()

    # Insert a new revision into the revisions table
    c.execute("INSERT INTO revisions (file_name, revision, user_id, initial_instruction) VALUES (?, ?, ?, ?)", (filename, revision, user_id, initial_instruction))
    conn.commit()

    # Close the connection to the database
    conn.close()

def load_model(model_url, model_folder, model_filename, max_context):

    model_path = model_folder + model_filename

    if not os.path.isfile(model_path):
        try:
            response = requests.get(model_url)
            with open(model_path, 'wb') as model_file:
                model_file.write(response.content)
        except Exception as e:
            print("Failed to download or save the model:", str(e))
            return None

    # Define default llama.cpp parameters
    default_llama_params = {
        "n_threads": 0,
        "n_threads_batch": 0,
        "n_batch": 512,
        "use_mmap": False,
        "use_mlock": False,
        "n_gpu_layers": 36,
        "main_gpu": 0,
        "tensor_split": "",
        "n_ctx": max_context,
        "rope_freq_base": 0,
        "numa": False,
        "max_tokens": max_context,
        "verbose": True
    }

    # Update llama_params with values from config or use defaults
    llama_params = {key: get_config(key, default_value) for key, default_value in default_llama_params.items()}

    try:
        return Llama(model_path, **llama_params)
    except Exception as e:
        print("Failed to create Llama object:", str(e))
        return None

# Helper function to connect to the revisions database
def connect_db(revisions_db):
    return sqlite3.connect(revisions_db)

def get_revisions_with_max_rows(user_id, revisions_db, max_rows):
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("""
        SELECT id, revision, file_name, initial_instruction
        FROM (
            SELECT id, revision, file_name, initial_instruction,
                   ROW_NUMBER() OVER (PARTITION BY file_name ORDER BY id DESC) AS row_num
            FROM revisions
            WHERE user_id=?
        ) ranked_revisions
        WHERE row_num <= ?
        ORDER BY file_name, id DESC
        """, (str(user_id), max_rows))
    revisions = c.fetchall()
    conn.close()
    return revisions

def get_all_revisions(user_id, revisions_db):
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("SELECT id, revision, file_name, initial_instruction FROM revisions WHERE user_id=? ORDER BY id desc", (str(user_id)))
    revisions = c.fetchall()
    conn.close()
    return revisions

# Helper function to get revisions for a given user
def get_prior_revision(user_id, revisions_db, filename, revision_id1):
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("SELECT id, revision, file_name, initial_instruction FROM revisions WHERE user_id=? AND file_name=? AND id < ? ORDER BY id desc", (str(user_id), filename, revision_id1))
    revision = c.fetchone()[0]
    conn.close()
    return revision

# Helper function to download a specific revision
def download_revision_file(revisions_db, filename, revision_id, user_id):
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

def update_revision_content(revisions_db, filename, revision_id, user_id, new_content, new_instruction):
    """Update the content of a specific revision in the SQLite database."""
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("UPDATE revisions SET revision=?, initial_instruction=? WHERE id=? AND file_name=? AND user_id=?", (new_content, new_instruction, revision_id, filename, user_id))
    conn.commit()
    conn.close()

def get_revision_content(revisions_db, filename, revision_id, user_id):
    """Retrieve the content of a specific revision from the SQLite database."""
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("SELECT revision, initial_instruction FROM revisions WHERE id=? AND file_name=? AND user_id=?", (revision_id, filename, user_id))
    revision_content, initial_instruction = c.fetchone()
    conn.close()
    return revision_content, initial_instruction if revision_content else None

def get_revision_content_bytes(revisions_db, filename, revision_id, user_id):
    """Retrieve the content of a specific revision from the SQLite database as bytes."""
    conn = connect_db(revisions_db)
    c = conn.cursor()
    c.execute("SELECT revision FROM revisions WHERE id=? AND file_name=? AND user_id=?", (revision_id, filename, user_id))
    revision_content = c.fetchone()
    conn.close()
    return revision_content[0].encode() if revision_content else None

def compare_two_revisions(revisions_db, filename, revision_id1, revision_id2, user_id, context):
    """Compare two revisions using the unified_diff and generate basic HTML representation."""
    content1 = get_revision_content(revisions_db, filename, revision_id1, user_id)
    content2 = get_revision_content(revisions_db, filename, revision_id2, user_id)

    # Check if there are no differences between the two revisions
    if content1[0] == content2[0]:
        return "No differences found between the two revisions."

    # Generate the unified diff with a larger context to show the whole file
    diff = difflib.unified_diff(content2[0].splitlines(), content1[0].splitlines(), n=context)

    # Create a basic HTML representation of the unified diff
    html_diff = '<html><head><style>pre { white-space: pre-wrap; }</style></head><body>'
    html_diff += '<h2>Unified Diff</h2><pre>'
    for line in diff:
        if line.startswith('+'):
            html_diff += '<span style="color: green;">{}</span><br>'.format(escape(line))
        elif line.startswith('-'):
            html_diff += '<span style="color: red;">{}</span><br>'.format(escape(line))
        else:
            html_diff += '{}<br>'.format(escape(line))
    html_diff += '</pre></body></html>'

    return html_diff
