import os
import re
from llama_cpp import Llama
from config_manager import load_config, get_config, update_config

def extract_code_from_markdown(markdown):
    code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', markdown, re.DOTALL)
    return code_blocks[0].strip() if code_blocks else markdown.strip()

def run(original_code, llama_model, prompt):
    # Load configuration from config.json
    config = load_config()

    # Get default prompt from config or use a default value
    default_prompt = get_config('default_prompt', "Revise and enhance the provided code by addressing issues, optimizing, and expanding features; implement pseudocode, comments, and placeholders; suggest additional features or improvements in comments or pseudocode for iterative development in subsequent rounds. If you implement something that was suggested in a placeholder, or if you see that the code already implements it, YOU MUST remove the placeholder. Include a properly-commented summary of the overall intent of the code that mentions every intended feature. Use the same programming language as the provided code. Include at least five TODO items for potential new features in the places in the code where they should be implemented.")

    # Check if extracting from Markdown is enabled in config
    extract_from_markdown = get_config('extract_from_markdown', True)

    # Use the provided prompt if given, else use the one from config
    prompt = prompt if prompt else config.get('prompt', default_prompt)    

    messages = [{"role": "system", "content": prompt + " Here is the provided code: ```" + original_code + "```"}]
    
    response = llama_model.create_chat_completion(messages=messages)

    revised_markdown = response['choices'][0]['message']['content']

    # Extract code from the revised markdown if enabled
    revised_code = extract_code_from_markdown(revised_markdown) if extract_from_markdown else revised_markdown

    return revised_code