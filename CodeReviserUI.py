from flask import Flask, render_template, request, send_file, abort, jsonify, redirect, url_for
import gc
from flask_login import UserMixin, current_user
from multiprocessing import Array
from urllib.error import HTTPError
from urllib.parse import quote_plus, unquote_plus
from werkzeug.utils import secure_filename

from lib.config_manager import *
from lib.job_manager import *
from lib.app_utils import *
from lib import revise_code

app = Flask(__name__)

current_result = Array('c', b'\0' * 32768)

# Load existing config or set defaults
config = load_config()

# Set defaults if not present in the config
app.secret_key = get_config('secret_key', '')
app.config['MODEL_FOLDER'] = get_config('model_folder', '')
app.config['REVISIONS_DB'] = get_config('revisions_db', '')
app.config['MODEL_URL'] = get_config('model_url', "")
app.config['MODEL_FILENAME'] = get_config('model', "")
app.config['MAX_CONTEXT'] = get_config('n_ctx', "")
app.config['REVISIONS_PER_PAGE'] = get_config('revisions_per_page', "")
app.config['SESSION_TYPE'] = get_config('session_type', '')
app.config['MAX_FILE_SIZE'] = get_config('max_file_size', "")

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

current_user = User(1, "developer")

init_db(app.config['REVISIONS_DB'])  # Pass the database path

@app.route('/')
def index():
    jobs = load_jobs()
    all_revisions = get_all_revisions(current_user.id, app.config['REVISIONS_DB'])
    all_revisions = tuple((revision[0], revision[1], quote_plus(revision[2])) for revision in all_revisions)
    return render_template('index.html', jobs=jobs, revisions=all_revisions)

@app.route('/edit_config')
def edit_config():
  config = json.load(open('user_config.json'))
  return render_template('edit_config.html', config=json.dumps(config, indent=4))

@app.route('/save_config', methods=['POST'])
def save_config():
  config = request.get_json()
  open('user_config.json', 'w').write(json.dumps(config, indent=4))
  return jsonify({'message': 'Config saved successfully.'})

@app.route('/queue', methods=['POST'])
def queue():
    rounds = int(request.form.get('rounds', 1))
    prompt = request.form.get('prompt', '')
    if 'file' in request.files and request.files['file'].filename != '':
        # File Upload Scenario
        file = request.files['file']
        filename = secure_filename(file.filename)
        file_contents = file.read()
    else:
        # Manual Input Scenario
        filename = request.form.get('fileName', '')
        file_contents = request.form.get('fileContents', '').encode('utf-8')

    add_job(app.config['MAX_FILE_SIZE'], filename, file_contents, app.config['MODEL_FOLDER'], app.config['REVISIONS_DB'], current_user, rounds, prompt)
    return redirect(url_for('index'))

@app.route('/process_request', methods=['POST'])
def process_request():

    prompt = request.form.get('prompt', '')
    file_contents = request.form.get('fileContents', '')

    llm = load_model(app.config['MODEL_URL'], app.config['MODEL_FOLDER'], app.config['MODEL_FILENAME'], app.config['MAX_CONTEXT'])
    revision = revise_code.run(file_contents, llm, prompt)

    del llm
    gc.collect()
    time.sleep(10)
    return revision

@app.route('/start-batch', methods=['GET'])
def start_batch():
    start_batch_job(app.config['REVISIONS_DB'], app.config['MODEL_FOLDER'], app.config['MODEL_URL'], app.config['MODEL_FILENAME'], app.config['MAX_CONTEXT'])
    return redirect(url_for('index'))

@app.route('/clear_batch_job/<int:job_id>', methods=['POST'])
def clear_batch_job(job_id):
    clear_job(job_id)
    return redirect(url_for('index'))

@app.route('/reset_batch_job_status/<int:job_id>', methods=['POST'])
def reset_batch_job_status(job_id):
    batch_requests_file = get_config("job_file", "")
    update_job_status(batch_requests_file, job_id, "NEW", clear_file_contents=False)
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
    
@app.route('/edit-revision/<string:filename>/<int:revision_id>', methods=['GET', 'POST'])
def edit_revision(filename, revision_id):
   if request.method == 'GET':
       latest_revisions = get_latest_revisions(filename, current_user.id, app.config['REVISIONS_DB'])
       initial_instruction = get_initial_instruction(filename, app.config['REVISIONS_DB'])
       return render_template('edit_revision.html', filename=filename, revision_id=revision_id, latest_revisions=latest_revisions, initial_instruction=initial_instruction)
   elif request.method == 'POST':
       new_content = request.form['new_content']
       update_revision_content(app.config['REVISIONS_DB'], filename, revision_id, current_user.id, new_content)
       return redirect(url_for('index'))

@app.route('/compare-revisions/<string:filename>/<int:revision_id1>', methods=['GET'])
def compare_revisions(filename, revision_id1):
    try:
        revision_id2 = get_prior_revision(current_user.id, app.config['REVISIONS_DB'], filename, revision_id1)
        comparison_result = compare_two_revisions(app.config['REVISIONS_DB'], unquote_plus(filename), revision_id1, revision_id2, current_user.id, 10000)
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

@app.route('/revise-from-revision/<string:filename>/<int:revision_id>', methods=['POST'])
def revise_from_revision(filename, revision_id):
    rounds = int(request.form.get('rounds', 1))  
    prompt = request.form.get('prompt', '')
    revision_content = get_revision_content_bytes(app.config['REVISIONS_DB'], unquote_plus(filename), revision_id, current_user.id)
    add_job(app.config['MAX_FILE_SIZE'], filename, revision_content, app.config['MODEL_FOLDER'], app.config['REVISIONS_DB'], current_user, rounds, prompt)
    return redirect(url_for('index'))

@app.route('/delete/<string:filename>/<int:revision_id>', methods=['GET'])
def delete_revision(filename, revision_id):
    result = delete_revision_file(app.config['REVISIONS_DB'], unquote_plus(filename), revision_id, current_user.id)
    return redirect(url_for('index'))

@app.errorhandler(FileNotFoundError)
def handle_model_not_found(e):
    abort(500, description="Model not found")

def check_and_define_variable(var_name, default_value):
    if var_name not in globals():
        globals()[var_name] = default_value

@app.errorhandler(HTTPError)
def handle_http_errors(e):
    abort(500, description="Failed to download model.")

if __name__ == '__main__':
    
    port_number = get_config("port","")
    process_name, process_pid = find_process_by_port(port_number)

    if process_name and process_pid:
        print(f"App cannot start: Port {port_number} is being used by process '{process_name}' (PID: {process_pid})")
    else:
        app.run(host=get_config("host",""),port=get_config("port",""))

    