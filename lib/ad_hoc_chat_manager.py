import os
import re
import math
import gc
from llama_cpp import Llama
from lib.config_manager import load_config, get_config, update_config
from multiprocessing import Process

global current_result

def run(llama_model, prompt):
    global current_result  # Declare current_result as a global variable

    current_result = ""

    stream = llama_model.create_completion(
        prompt,
        max_tokens=get_config('n_ctx', 32768),
        stream=True)

    for output in stream:
        current_result += output['choices'][0]['text']
        print(current_result)

    del llama_model
    gc.collect()

def run_batch(llama_model, prompt):
    batch_process = Process(target=run, args=(llama_model, prompt))
    batch_process.start()

def get():
    global current_result
    if current_result is None:
        current_result = ""
    return current_result
