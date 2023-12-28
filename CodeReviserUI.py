# Import required libraries
from flask import Flask, render_template, request, send_file, url_for, flash, redirect, jsonify, abort, Response, session  # Add session module for authentication
import os
import sqlite3
import requests
import tempfile
import uuid
import shutil
import re
import sys
import urllib.request
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from lib import revise_prompt, compare_texts, revise_code, build_readme
from urllib.error import HTTPError
from llama_cpp import Llama
from multiprocessing import Process

# Initialize Flask app and configure settings
app = Flask(__name__)
app.secret_key = 'GOISDFYuizxdfjkljaskdf@#$517389&*(aasdfjkl;)'  
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['REVISIONS_DB'] = 'revisions.db'
app.config['MODEL_URL'] = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q5_K_S.gguf"
app.config['MODEL_FILENAME'] = "mistral-7b-instruct-v0.2.Q5_K_S.gguf"
app.config['MAX_CONTEXT'] = 32768  # Maximum context length for LLM model
app.config['REVISIONS_PER_PAGE'] = 10  # Number of revisions to display per page
app.config['SESSION_TYPE'] = 'filesystem'  # Use in-memory session store for simplicity
app.config['MAX_FILE_SIZE'] = 5 * 1024 * 1024  # Maximum file size limit (5MB)

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

current_user = User(1, "developer")

def init_db():
    conn = sqlite3.connect(app.config['REVISIONS_DB'])
    c = conn.cursor()
    # Create table for revisions if it doesn't exist, with columns: id, file_name, revision, user_id
    c.execute('''CREATE TABLE IF NOT EXISTS revisions (id INTEGER PRIMARY KEY AUTOINCREMENT, file_name TEXT, revision TEXT, user_id INT)''')  # Add user_id column for authentication
    conn.commit()
    conn.close()


init_db()

# Load model
llm = None
def load_model():
    global llm
    if not os.path.isfile(app.config['UPLOAD_FOLDER'] + app.config['MODEL_FILENAME']):
        try:
            response = requests.get(app.config['MODEL_URL'])
            open(app.config['UPLOAD_FOLDER'] + app.config['MODEL_FILENAME'], 'wb').write(response.content)
        except Exception as e:
            print("Failed to download model:", str(e))
            return
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
            "n_ctx": app.config['MAX_CONTEXT'],
            "compress_pos_emb": 1,
            "alpha_value": 1,
            "rope_freq_base": 0,
            "numa": False,
            "model": app.config['MODEL_FILENAME'],
            "temperature": 1.0,
            "top_p": 0.99,
            "top_k": 85,
            "repetition_penalty": 1.01,
            "typical_p": 0.68,
            "tfs": 0.68,
            "max_tokens": app.config['MAX_CONTEXT']
        }
        
        llm = Llama(app.config['UPLOAD_FOLDER'] + app.config['MODEL_FILENAME'], **llama_params)

    except FileNotFoundError:
        print("Model file not found locally, downloading...")
        load_model()

load_model()


@app.route('/')
def index():
    return render_template('index.html')

# Queue code for revision and save it in SQLite database
@app.route('/queue', methods=['POST'])
def queue():
    """Queue a file for revision and save it in the SQLite database."""
    if 'file' not in request.files or not request.files['file'].filename:
        abort(400, description="No file part")

    file = request.files['file']
    file_size = len(file.getvalue())
    if file_size > app.config['MAX_FILE_SIZE']:
        abort(413, description="File size exceeds the limit.")

    filename = str(uuid.uuid4()) + '.' + file.filename.split('.')[-1]
    try:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    except IOError as e:
        abort(500, description=str(e))

    user_id = current_user.id
    # Start a new process for the background job
    background_process = Process(target=background_revision_job, args=(filename, user_id))
    background_process.start()

    return jsonify({'status': 'success', 'message': 'Code revision queued.'})


def background_revision_job(filename, user_id):
    # This function runs in a separate process
    revision = generate_code_revision(filename, user_id)
    save_revision(filename, user_id, revision)
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))

# Revise prompt using LLM model
@app.route('/revise-prompt', methods=['GET', 'POST'])
def revise_prompt():
    if request.method == 'GET':
        return render_template('revise_prompt.html')
    elif request.method == 'POST':
        """Revise a given prompt using the LLM model."""
        if not request.is_json or not 'prompt' in request.json:
            abort(400, description="No prompt provided")

        data = request.get_json()
        prompt = data['prompt']
        revision = revise_prompt.run(prompt, llama_model)
        return jsonify({'status': 'success', 'message': 'Prompt revised.', 'revision': revision})
    
# View revisions and download individual revisions
@app.route('/revisions/<string:filename>')
def view_revisions(filename):
    """Display the given file's revisions."""
    page = int(request.args.get('page', 1)) * app.config['REVISIONS_PER_PAGE']
    offset = (page - 1) * app.config['REVISIONS_PER_PAGE']

    conn = sqlite3.connect(app.config['REVISIONS_DB'])
    c = conn.cursor()
    c.execute("SELECT id, revision FROM revisions WHERE file_name=? AND user_id=? LIMIT ? OFFSET ?", (filename, current_user.id, app.config['REVISIONS_PER_PAGE'], offset))
    revisions = c.fetchall()
    total_revisions = c.execute("SELECT COUNT(*) FROM revisions WHERE file_name=? AND user_id=?", (filename, current_user.id)).fetchone()[0]
    conn.close()

    return render_template('revisions.html', filename=filename, revisions=revisions, total_revisions=total_revisions, page=page)

@app.route('/download/<string:filename>/<int:revision_id>')
def download_revision(filename, revision_id):
    """Download a specific revision of the given file."""
    conn = sqlite3.connect(app.config['REVISIONS_DB'])
    c = conn.cursor()
    c.execute("SELECT revision FROM revisions WHERE id=? AND file_name=? AND user_id=?", (revision_id, filename, current_user.id))
    revision = c.fetchone()[0]
    if not revision:
        abort(404, description="Revision not found")

    temp_file = tempfile.TemporaryFile()
    temp_file.write(revision.encode())
    temp_file.seek(0)
    return send_file(temp_file, as_attachment=True, filename=f"{filename}-revision-{revision_id}.txt")

# Download all revisions of a file
@app.route('/download/all/<string:filename>')
def download_all_revisions(filename):
    """Download all revisions of the given file."""
    conn = sqlite3.connect(app.config['REVISIONS_DB'])
    c = conn.cursor()
    c.execute("SELECT id, revision FROM revisions WHERE file_name=? AND user_id=?", (filename, current_user.id))
    revisions = c.fetchall()
    conn.close()

    if not revisions:
        return jsonify({'status': 'error', 'message': 'No revisions found for this file.'})

    temp_dir = tempfile.TemporaryDirectory()
    responses = []

    for revision in revisions:
        temp_file = tempfile.TemporaryFile(prefix=f"{filename}-revision-", dir=temp_dir.name, delete=False)
        temp_file.write(revision[1].encode())
        temp_file.seek(0)
        response = send_file(temp_file, as_attachment=True, filename=f"{filename}-revision-{revision[0]}.txt")
        os.remove(temp_file.name)
        responses.append(response)

    temp_dir.cleanup()
    return response if len(responses) == 1 else Response(body="\n".join([str(r.data) for r in responses]), mimetype='text/plain')

# Delete a specific revision of the given file
@app.route('/delete/<string:filename>/<int:revision_id>')
def delete_revision(filename, revision_id):
    """Delete a specific revision of the given file."""
    conn = sqlite3.connect(app.config['REVISIONS_DB'])
    c = conn.cursor()
    c.execute("DELETE FROM revisions WHERE id=? AND file_name=? AND user_id=?", (revision_id, filename, current_user.id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Revision deleted.'})

# Helper functions for revising code and saving revisions in SQLite database
def generate_code_revision(filename, user_id):
    """Revise the given file using the LLM model and save it in the SQLite database."""
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'r') as file:
        code = file.read()
    revision = revise_code.run(code, llm)
    save_revision(filename, user_id, revision)  # Save the revision in SQLite database

def save_revision(filename, user_id, revision):
    """Save a new revision of the given file in the SQLite database."""
    conn = sqlite3.connect(app.config['REVISIONS_DB'])
    c = conn.cursor()
    c.execute("INSERT INTO revisions (file_name, revision, user_id) VALUES (?, ?, ?)", (filename, revision, user_id))
    conn.commit()
    conn.close()

# Handle model loading errors in download routes using try-except blocks
@app.errorhandler(FileNotFoundError)
def handle_model_not_found(e):
    abort(500, description="Model not found")

@app.errorhandler(HTTPError)
def handle_http_errors(e):
    abort(500, description="Failed to download model.")

# Route for handling paginated download of multiple revisions at once
@app.route('/download/<string:filename>/page/<int:page>')
def download_revisions(filename, page):
    """Download multiple revisions of the given file in one request."""
    offset = (page - 1) * app.config['REVISIONS_PER_PAGE']

    conn = sqlite3.connect(app.config['REVISIONS_DB'])
    c = conn.cursor()
    c.execute("SELECT id, revision FROM revisions WHERE file_name=? AND user_id=? LIMIT ? OFFSET ?", (filename, current_user.id, app.config['REVISIONS_PER_PAGE'], offset))
    revisions = c.fetchall()
    total_revisions = c.execute("SELECT COUNT(*) FROM revisions WHERE file_name=? AND user_id=?", (filename, current_user.id)).fetchone()[0]
    conn.close()

    temp_dir = tempfile.TemporaryDirectory()
    responses = []

    for revision in revisions:
        temp_file = tempfile.TemporaryFile(prefix=f"{filename}-revision-", dir=temp_dir.name, delete=False)
        temp_file.write(revision[1].encode())
        temp_file.seek(0)
        response = send_file(temp_file, as_attachment=True, filename=f"{filename}-revision-{revision[0]}.txt")
        os.remove(temp_file.name)
        responses.append(response)

    temp_dir.cleanup()
    return response if len(responses) == 1 else Response(body="\n".join([str(r.data) for r in responses]), mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True)