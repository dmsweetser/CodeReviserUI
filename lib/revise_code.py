import re
from lib.config_manager import get_config
from lib.linter import Linter

def extract_code_from_markdown(markdown):
    code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', markdown, re.DOTALL)
    return code_blocks[0].strip() if code_blocks else markdown.strip()

def run(original_code, llama_model, initial_prompt):
    # Get default prompt from config or use a default value
    default_prompt = get_config('default_prompt', "")
    revision_prompt = get_config('revision_prompt', "") 

    # Check if extracting from Markdown is enabled in config
    extract_from_markdown = get_config('extract_from_markdown', True)

    if "TODO" in original_code.upper() or "PLACEHOLDER" in original_code.upper():
        # Use the provided prompt if given, else use the one from config
        prompt = revision_prompt
    else:
        # Use the provided prompt if given, else use the one from config
        prompt = default_prompt

    language = ""
    if "python" in initial_prompt.lower():
        language = "python"
    elif "javascript" in initial_prompt.lower():
        language = "javascript"
    elif "c#" in initial_prompt.lower():
        language = "csharp"
    linter = Linter(original_code, language)
    current_errors = linter.lint()

    if initial_prompt != "":
        message = f"<s>[INST]\n{prompt}\nHere is the original instruction:\n{initial_prompt}\nHere is the current code:\n```\n{original_code}\n```\nHere are the current compiler errors:\n{current_errors}\n[/INST]\n"
    else:
        message = f"<s>[INST]\n{prompt}\nHere is the current code:\n```\n{original_code}\n```\nHere are the current compiler errors:\n{current_errors}\n[/INST]\n"

    print(f"[LATEST MESSAGE]\n\n\n\n\n\n{message}\n\n\n\n\n\n")

    response = llama_model.create_completion(
        message,
        temperature=get_config("temperature",""),
        top_p=get_config("top_p",""),
        top_k=get_config("top_k",""),
        repeat_penalty=get_config("repeat_penalty",""),
        typical_p=get_config("typical_p",""),
        max_tokens=get_config("max_tokens","")
        )

    revised_markdown = response['choices'][0]['text']

    # Extract code from the revised markdown if enabled
    revised_code = extract_code_from_markdown(revised_markdown) if extract_from_markdown else revised_markdown

    if len(revised_code) < .3 * len(original_code):
        print("Generated code was too short")
        return original_code
    else:
        return revised_code
