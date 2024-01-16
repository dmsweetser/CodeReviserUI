import os
import re
import math
from llama_cpp import Llama
from lib.config_manager import load_config, get_config, update_config

def extract_code_from_markdown(markdown):
    code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', markdown, re.DOTALL)
    return code_blocks[0].strip() if code_blocks else markdown.strip()

def run(original_code, prior_revision, llama_model, prompt):
    # Load configuration from config.json
    config = load_config()

    # Get default prompt from config or use a default value
    default_prompt = get_config('default_prompt', "Improve the provided code by addressing identified issues, optimizing, and extending functionality. Provide ONLY ONE complete revision so that anyone reviewing your new code can do so without having access to the prior code. Use pseudocode, comments, and placeholders to document changes. Propose additional features or improvements through comments or pseudocode for subsequent iterations. Remove placeholders when the suggested feature is implemented or already present. Embed at least five TODO items specifying potential new features inline in the code. Provide your revision as fast as you possibly can.")

    # Check if extracting from Markdown is enabled in config
    extract_from_markdown = get_config('extract_from_markdown', True)

    # Use the provided prompt if given, else use the one from config
    prompt = prompt if prompt else default_prompt

    # if prior_revision:
    #     message = f"<s>[INST]\n{prompt}\nHere is the current code: ```{original_code}```\nHere is the most recent prior revision: ```{prior_revision}```\n[/INST]\n"
    # else:
    #     message = f"<s>[INST]\n{prompt}\nHere is the current code: ```{original_code}```\n[/INST]\n"

    message = f"<s>[INST]\n{prompt}\nHere is the current code:\n```\n{original_code}\n```\n[/INST]\n"

    messages = [{"role": "user", "content": message}]
    
    response = llama_model.create_chat_completion(messages=messages)

    revised_markdown = response['choices'][0]['message']['content']

    # Extract code from the revised markdown if enabled
    revised_code = extract_code_from_markdown(revised_markdown) if extract_from_markdown else revised_markdown

    if len(revised_code) < .3 * len(original_code):
        print("Generated code was too short")
        return original_code
    else:
        return revised_code
