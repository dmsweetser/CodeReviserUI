import re
from lib.config_manager import get_config
from lib.linter import Linter
from lib.custom_logger import *
import time

logger = CustomLogger(get_config("log_folder",""))

def run(original_code, llama_model, prompt):

    start_time = time.time() # Get the start time

    response = llama_model.create_completion(
        prompt,
        temperature=get_config("temperature",""),
        top_p=get_config("top_p",""),
        top_k=get_config("top_k",""),
        repeat_penalty=get_config("repeat_penalty",""),
        typical_p=get_config("typical_p",""),
        max_tokens=get_config("max_tokens","")
        )

    revised_code = response['choices'][0]['text']
    
    # Check if extracting from Markdown is enabled in config
    extract_from_markdown = get_config('extract_from_markdown', '')
    
    if extract_from_markdown:
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', revised_code, re.DOTALL)
        revised_code = '\n'.join(code_blocks) if code_blocks else revised_code

    original_tokens = llama_model.tokenize(original_code)
    new_tokens = llama_model.tokenize(revised_code)
    
    end_time = time.time() # Get the end time
    duration = end_time - start_time # Calculate the duration

    print(f"Total duration in seconds: {duration}")
    
    logger.log(f"Original token count: {len(original_tokens)}")
    logger.log(f"New token count: {len(new_tokens)}")

    if len(revised_code) < .3 * len(original_code):
        logger.log(f"Generated code was too short")
        return original_code
    elif len(revised_code) > 1.7 * len(original_code) and len(original_code) > 4000:
        logger.log(f"Generated code was too long")
        return original_code
    else:
        return revised_code
