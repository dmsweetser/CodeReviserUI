from flask import Flask, render_template, request, send_file, abort, jsonify, redirect, url_for
import os
import sqlite3
import tempfile
import uuid
import requests
from flask_login import LoginManager, UserMixin, current_user
from multiprocessing import Process
from urllib.error import HTTPError
from urllib.parse import quote_plus, unquote_plus
from werkzeug.utils import secure_filename
from llama_cpp import Llama

from app_utils import init_db, update_job_status, process_background_job, connect_db
from app_utils import get_all_revisions, download_revision_file, delete_revision_file, process_file_and_background_job
from app_utils import get_revision_content, compare_two_revisions, update_revision_content, get_revision_content_bytes

from globals import active_jobs

app = Flask(__name__)

app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['REVISIONS_DB'] = 'revisions.db'
app.config['MODEL_URL'] = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q5_K_S.gguf"
app.config['MODEL_FILENAME'] = "mistral-7b-instruct-v0.2.Q5_K_S.gguf"
app.config['MAX_CONTEXT'] = 32768
app.config['REVISIONS_PER_PAGE'] = 10
app.config['SESSION_TYPE'] = 'filesystem'
app.config['MAX_FILE_SIZE'] = 10 * 1024 * 1024

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

current_user = User(1, "developer")

init_db(app.config['REVISIONS_DB'])  # Pass the database path

@app.route('/')
def index():
    all_revisions = get_all_revisions(current_user.id, app.config['REVISIONS_DB'])
    all_revisions = tuple((revision[0], revision[1], quote_plus(revision[2])) for revision in all_revisions)
    return render_template('index.html', active_jobs=active_jobs, revisions=all_revisions)

@app.route('/queue', methods=['POST'])
def queue():
    rounds = int(request.form.get('rounds', 1))
    prompt = request.form.get('prompt', '')

    if 'file' in request.files:
        # File Upload Scenario
        file = request.files['file']
        filename = secure_filename(file.filename)
        file_contents = file.read()
    else:
        # Manual Input Scenario
        filename = request.form.get('fileName', '')
        file_contents = request.form.get('fileContents', '').encode('utf-8')

    print(file_contents)
    llm = load_model_if_not_exists(app.config['MODEL_URL'], app.config['UPLOAD_FOLDER'], app.config['MODEL_FILENAME'], app.config['MAX_CONTEXT'])
    process_file_and_background_job(app.config['MAX_FILE_SIZE'], filename, file_contents, app.config['UPLOAD_FOLDER'], app.config['REVISIONS_DB'], active_jobs, llm, current_user, rounds, prompt)
    return redirect(url_for('index'))

@app.route('/edit-revision/<string:filename>/<int:revision_id>', methods=['GET', 'POST'])
def edit_revision(filename, revision_id):
    if request.method == 'GET':
        revision_content = get_revision_content(app.config['REVISIONS_DB'], unquote_plus(filename), revision_id, current_user.id)
        return render_template('edit_revision.html', filename=filename, revision_id=revision_id, revision_content=revision_content)
    elif request.method == 'POST':
        new_content = request.form['new_content']
        update_revision_content(app.config['REVISIONS_DB'], unquote_plus(filename), revision_id, current_user.id, new_content)
        return redirect(url_for('index'))

@app.route('/compare-revisions/<string:filename>/<int:revision_id1>/<int:revision_id2>', methods=['GET'])
def compare_revisions(filename, revision_id1, revision_id2):
    try:
        comparison_result = compare_two_revisions(app.config['REVISIONS_DB'], unquote_plus(filename), revision_id1, revision_id2, current_user.id, 5)
        return render_template('compare_revisions.html', filename=filename, revision_id1=revision_id1, revision_id2=revision_id2, comparison_result=comparison_result)
    except Exception as e:
        print(f"Error comparing revisions: {str(e)}")
        return redirect(url_for('index'))

@app.route('/download/<string:filename>/<int:revision_id>', methods=['GET'])
def download_revision(filename, revision_id):
    temp_file = download_revision_file(app.config['REVISIONS_DB'], unquote_plus(filename), revision_id, current_user.id)
    root, extension = secure_filename(filename).rsplit('.', 1)
    new_filename = f"{root}_revision_{revision_id}.{extension}"
    return send_file(temp_file, as_attachment=True, download_name=new_filename)

@app.route('/revise-from-revision/<string:filename>/<int:revision_id>', methods=['GET'])
def revise_from_revision(filename, revision_id):
    rounds = int(request.form.get('rounds', 1))
    prompt = request.form.get('prompt', '')
    revision_content = get_revision_content_bytes(app.config['REVISIONS_DB'], unquote_plus(filename), revision_id, current_user.id)
    llm = load_model_if_not_exists(app.config['MODEL_URL'], app.config['UPLOAD_FOLDER'], app.config['MODEL_FILENAME'], app.config['MAX_CONTEXT'])
    process_file_and_background_job(app.config['MAX_FILE_SIZE'], filename, revision_content, app.config['UPLOAD_FOLDER'], app.config['REVISIONS_DB'], active_jobs, llm, current_user, rounds, prompt)
    return redirect(url_for('index'))

@app.route('/delete/<string:filename>/<int:revision_id>', methods=['GET'])
def delete_revision(filename, revision_id):
    result = delete_revision_file(app.config['REVISIONS_DB'], unquote_plus(filename), revision_id, current_user.id)
    return redirect(url_for('index'))

@app.errorhandler(FileNotFoundError)
def handle_model_not_found(e):
    abort(500, description="Model not found")

@app.errorhandler(HTTPError)
def handle_http_errors(e):
    abort(500, description="Failed to download model.")

# Global cache to store Llama instances
llama_cache = {}

def load_model_if_not_exists(model_url, upload_folder, model_filename, max_context):
    global llama_cache

    model_path = upload_folder + model_filename

    # Check if Llama instance is already in the cache
    if len(llama_cache) > 0:
        return llama_cache[0]

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
        llama_instance = Llama(model_path, **llama_params)
        # Cache the Llama instance
        llama_cache[0] = llama_instance
        print("Llama Cache Length")
        print(len(llama_cache))
        return llama_instance
    except Exception as e:
        print("Failed to create Llama object:", str(e))
        return None

if __name__ == '__main__':
    app.run()