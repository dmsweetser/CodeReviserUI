import re
from lib.config_manager import get_config
from lib.linter import Linter

def run(original_code, llama_model, prompt):

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

    if len(revised_code) < .3 * len(original_code):
        print(f"Generated code was too short\n\n\nRevised Code\n\n\n{revised_code}")
        return original_code
    elif len(revised_code) > 1.7 * len(original_code):
        print(f"Generated code was too long\n\n\nRevised Code\n\n\n{revised_code}")
        return original_code
    else:
        return revised_code
