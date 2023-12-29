from flask import Flask, render_template, request, send_file, abort, jsonify, redirect, url_for
import os
import sqlite3
import tempfile
import uuid
from flask_login import LoginManager, UserMixin, current_user
from multiprocessing import Process
from urllib.error import HTTPError
from app_utils import init_db, load_model, update_job_status, process_background_job, connect_db, get_all_revisions, download_revision_file, delete_revision_file


app = Flask(__name__)

app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['REVISIONS_DB'] = 'revisions.db'
app.config['MODEL_URL'] = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q5_K_S.gguf"
app.config['MODEL_FILENAME'] = "mistral-7b-instruct-v0.2.Q5_K_S.gguf"
app.config['MAX_CONTEXT'] = 32768
app.config['REVISIONS_PER_PAGE'] = 10
app.config['SESSION_TYPE'] = 'filesystem'
app.config['MAX_FILE_SIZE'] = 5 * 1024 * 1024

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

current_user = User(1, "developer")

init_db(app.config['REVISIONS_DB'])  # Pass the database path

active_jobs = None
if active_jobs is None:
    active_jobs = []

llm = None
if llm is None:
    llm = load_model(app.config['MODEL_URL'], app.config['UPLOAD_FOLDER'], app.config['MODEL_FILENAME'], app.config['MAX_CONTEXT'])

@app.route('/')
def index():
    return render_template('index.html', active_jobs=active_jobs, revisions=get_all_revisions(current_user.id, app.config['REVISIONS_DB']))

@app.route('/queue', methods=['POST'])
def queue():
    if 'file' not in request.files or not request.files['file'].filename:
        abort(400, description="No file part")

    file = request.files['file']
    file_size = len(file.getvalue())
    if file_size > app.config['MAX_FILE_SIZE']:
        abort(413, description="File size exceeds the limit.")

    filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    try:
        file.save(filename)
    except IOError as e:
        abort(500, description=str(e))

    user_id = current_user.id
    background_process = Process(target=process_background_job, args=(app.config['REVISIONS_DB'], app.config['UPLOAD_FOLDER'], filename, user_id, active_jobs, llm))
    background_process.start()

    active_jobs.append({
        'filename': filename,
        'user_id': user_id,
        'status': 'Running',
    })

    return redirect(url_for('index'))

@app.route('/revise-prompt', methods=['POST'])
def revise_prompt():
    if not request.is_json or 'prompt' not in request.json:
        abort(400, description="No prompt provided")

    data = request.get_json()
    prompt = data['prompt']
    revision = revise_prompt.run(prompt, llama_model)
    return jsonify({'status': 'success', 'message': 'Prompt revised.', 'revision': revision})

@app.route('/download/<string:filename>/<int:revision_id>')
def download_revision(filename, revision_id):
    temp_file = download_revision_file(filename, revision_id, current_user.id)
    return send_file(temp_file, as_attachment=True, filename=f"{filename}-revision-{revision_id}.txt")

# Delete a specific revision of the given file
@app.route('/delete/<string:filename>/<int:revision_id>')
def delete_revision(filename, revision_id):
    result = delete_revision_file(filename, revision_id, current_user.id)
    return jsonify(result)

# Handle model loading errors in download routes using try-except blocks
@app.errorhandler(FileNotFoundError)
def handle_model_not_found(e):
    abort(500, description="Model not found")

@app.errorhandler(HTTPError)
def handle_http_errors(e):
    abort(500, description="Failed to download model.")


if __name__ == '__main__':
    app.run(debug=True)