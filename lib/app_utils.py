import os
import sqlite3
import requests
import tempfile
import uuid
from flask import abort
from multiprocessing import Process

import difflib
from markupsafe import escape

from llama_cpp import Llama
import json
import base64

from lib.config_manager import *
from lib.job_manager import *
from lib import revise_code, revise_code_gpu

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exllamav2 import(
    ExLlamaV2,
    ExLlamaV2Config,
    ExLlamaV2Cache,
    ExLlamaV2Tokenizer,
)

from exllamav2.generator import (
    ExLlamaV2BaseGenerator,
    ExLlamaV2Sampler
)

def init_db(revisions_db):
    conn = sqlite3.connect(revisions_db)
    c = conn.cursor()
    # Create table for revisions if it doesn't exist, with columns: id, file_name, revision, user_id
    c.execute('''CREATE TABLE IF NOT EXISTS revisions (id INTEGER PRIMARY KEY AUTOINCREMENT, file_name TEXT, revision TEXT, user_id INT)''')  # Add user_id column for authentication
    conn.commit()
    conn.close()

def generate_code_revision(revisions_db, filename, file_contents, user_id, llm, rounds, prompt):
    """Revise the given file using the LLM model and save it in the SQLite database."""
    
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

def generate_code_revision_gpu(revisions_db, filename, file_contents, user_id, llm, llm_settings, max_context, rounds, prompt):
    """Revise the given file using the LLM model and save it in the SQLite database."""
    
    code = file_contents.decode('utf-8')

    for _ in range(rounds):
        existing_revision = get_latest_revision(filename, user_id, revisions_db)
        if existing_revision:
            revision = revise_code_gpu.run(existing_revision, llm, llm_settings, max_context, prompt)
        else:
            save_revision(revisions_db, filename, user_id, code)
            revision = revise_code_gpu.run(code, llm, llm_settings, max_context, prompt)
        save_revision(revisions_db, filename, user_id, revision)
        code = revision

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

    # Load configuration from config.json
    config = load_config()

    # Define default llama.cpp parameters
    default_llama_params = {
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

    # Update llama_params with values from config or use defaults
    llama_params = {key: get_config(key, default_value) for key, default_value in default_llama_params.items()}

    try:
        return Llama(model_path, **llama_params)
    except Exception as e:
        print("Failed to create Llama object:", str(e))
        return None


def load_model_gpu(model_folder, model_filename, max_context):

    model_path = model_folder + model_filename

    if not os.path.isdir(model_path):
        print("Model not found in path " + model_path)
        return None

    # Load configuration from config.json
    config = load_config()

        # Initialize model and cache
    model_config = ExLlamaV2Config()
    model_config.model_dir = model_path
    model_config.prepare()

    model = ExLlamaV2(model_config)
    print("Loading model: " + model_path)

    cache = ExLlamaV2Cache(model, lazy = True)
    model.load_autosplit(cache)

    tokenizer = ExLlamaV2Tokenizer(model_config)
    generator = ExLlamaV2BaseGenerator(model, cache, tokenizer)

    settings = ExLlamaV2Sampler.Settings()
    settings.temperature = int(get_config("temperature", 1.0))
    settings.top_k = int(get_config("top_k", 85))
    settings.top_p = int(get_config("top_p", 0.99))
    settings.top_a = 0.0
    settings.token_repetition_penalty = int(get_config("repetition_penalty", 1.01))
    settings.disallow_tokens(tokenizer, [tokenizer.eos_token_id])

    return generator, settings

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
    """Compare two revisions using the unified_diff and generate basic HTML representation."""
    content1 = get_revision_content(revisions_db, filename, revision_id1, user_id)
    content2 = get_revision_content(revisions_db, filename, revision_id2, user_id)

    # Check if there are no differences between the two revisions
    if content1 == content2:
        return "No differences found between the two revisions."

    # Generate the unified diff with a larger context to show the whole file
    diff = difflib.unified_diff(content2.splitlines(), content1.splitlines(), n=context)

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
