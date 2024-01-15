import os
import re
import math
import gc
from llama_cpp import Llama
from lib.config_manager import load_config, get_config, update_config

current_result = ""

def run(llama_model, prompt):
    
    current_result = ""

    stream = llama_model.create_completion(
        prompt, 
        stream=True)
        
    for output in stream:
        current_result += output['choices'][0]['text']
        print(current_result)

    del llama_model
    gc.collect()

def get():
    return current_result
