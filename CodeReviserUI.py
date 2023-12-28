# Import required libraries
from flask import Flask, render_template, request, send_file, url_for, flash, redirect, jsonify, abort, Response, session  # Add session module for authentication
import os
import sqlite3
import requests
import tempfile
import uuid
import shutil
import re
import urllib.request
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from lib import revise_prompt, text_diff

# Initialize Flask app and configure settings
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['REVISIONS_DB'] = 'revisions.db'
app.config['MODEL_URL'] = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q5_K_S.gguf"
app.config['MODEL_FILENAME'] = "mistral-7b-instruct-v0.2.Q5_K_S.gguf"
app.config['MAX_CONTEXT'] = 32768  # Maximum context length for LLM model
app.config['REVISIONS_PER_PAGE'] = 10  # Number of revisions to display per page
app.config['SESSION_TYPE'] = 'filesystem'  # Use in-memory session store for simplicity
app.config['MAX_FILE_SIZE'] = 5 * 1024 * 1024  # Maximum file size limit (5MB)

# Initialize Flask-Login and SQLite database, download model if not present locally
login_manager = LoginManager()
login_manager.init_app(app)

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

# Login manager and user loader
@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(app.config['REVISIONS_DB'])
    c = conn.cursor()
    user = c.execute("SELECT * FROM revisions WHERE id=?", (int(user_id),)).fetchone()
    if not user:
        return None
    user_data = {k: v for k, v in user}
    del user_data['id']
    return User(**user_data)

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user."""
    if request.method == 'POST':
        flash("Registration successful.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Log in a user."""
    if request.method == 'POST':
        user = User(username='username', id=1)
        login_user(user)
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    return redirect(url_for('index'))

# Queue code for revision and save it in SQLite database
@app.route('/queue', methods=['POST'])
@login_required
def queue():
    """Queue a file for revision and save it in the SQLite database."""
    if 'file' not in request.files or not request.files['file'].filename:
        abort(400, description="No file part")

    file = request.files['file']
    if file.size > app.config['MAX_FILE_SIZE']:
        abort(413, description="File size exceeds the limit.")

    filename = str(uuid.uuid4()) + '.' + file.filename.split('.')[-1]
    try:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    except IOError as e:
        abort(500, description=str(e))

    user_id = current_user.id  # Get user ID from Flask-Login session for authentication
    revision = revise_code(filename, user_id)  # Revise the code using LLM model
    save_revision(filename, user_id, revision)  # Save the revision in SQLite database
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))  # Delete the original file
    return jsonify({'status': 'success', 'message': 'Code revised and saved.'})

# Revise prompt using LLM model
@app.route('/revise-prompt', methods=['POST'])
@login_required
def revise_prompt():
    """Revise a given prompt using the LLM model."""
    if not request.is_json or not 'prompt' in request.json:
        abort(400, description="No prompt provided")

    data = request.get_json()
    prompt = data['prompt']
    revision = lib.revise_prompt(prompt, llama_model)
    return jsonify({'status': 'success', 'message': 'Prompt revised.', 'revision': revision})

# View revisions and download individual revisions
@app.route('/revisions/<string:filename>')
@login_required
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
@login_required
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
@login_required
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
@login_required
def delete_revision(filename, revision_id):
    """Delete a specific revision of the given file."""
    conn = sqlite3.connect(app.config['REVISIONS_DB'])
    c = conn.cursor()
    c.execute("DELETE FROM revisions WHERE id=? AND file_name=? AND user_id=?", (revision_id, filename, current_user.id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Revision deleted.'})

# Helper functions for revising code and saving revisions in SQLite database
def revise_code(filename, user_id):
    """Revise the given file using the LLM model and save it in the SQLite database."""
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'r') as file:
        code = file.read()
    revision = lib.revise_code(code, llm)
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
@login_required
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