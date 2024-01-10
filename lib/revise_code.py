import os
import re
import math
from llama_cpp import Llama
from lib.config_manager import load_config, get_config, update_config

def extract_code_from_markdown(markdown):
    code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', markdown, re.DOTALL)
    return code_blocks[0].strip() if code_blocks else markdown.strip()

def run(original_code, llama_model, prompt):
    # Load configuration from config.json
    config = load_config()

    # Get default prompt from config or use a default value
    default_prompt = get_config('default_prompt', "Iteratively improve the provided code by addressing identified issues, optimizing, and extending functionality. Provide a complete revision so that anyone reviewing your new code can do so without having access to the prior code. Use pseudocode, comments, and placeholders to document changes. Propose additional features or improvements through comments or pseudocode for subsequent iterations. Remove placeholders when the suggested feature is implemented or already present. Embed at least five TODO items specifying potential new features inline in the code.")

    # Check if extracting from Markdown is enabled in config
    extract_from_markdown = get_config('extract_from_markdown', True)

    # Use the provided prompt if given, else use the one from config
    prompt = prompt if prompt else default_prompt

    messages = [{"role": "user", "content": f"<s>[INST] {prompt} Here is the current code: ```{original_code}``` [/INST]"}]
    
    response = llama_model.create_chat_completion(messages=messages)

    revised_markdown = response['choices'][0]['message']['content']

    # Extract code from the revised markdown if enabled
    revised_code = extract_code_from_markdown(revised_markdown) if extract_from_markdown else revised_markdown

    # Check if the revised code is at least 40% smaller than the original
    if len(revised_code) < 0.6 * len(original_code):
        return original_code

    return revised_code
