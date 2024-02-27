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

    if len(revised_code) < .9 * len(original_code):
        print(f"Generated code was too short\n\n\nRevised Code\n\n\n{revised_code}")
        return original_code
    else:
        return revised_code
