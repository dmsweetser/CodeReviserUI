import os
import re
from llama_cpp import Llama

# Call the function to revise the prompt
# revised_code = revise_code(original_code, llama_model)

def extract_code_from_markdown(markdown):
    # Regular expression to find code blocks in markdown with optional language specifier
    code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', markdown, re.DOTALL)
    
    # Extracting code from the first code block (assuming there's only one)
    if code_blocks:
        return code_blocks[0].strip()  # Trimming whitespace
    else:
        return markdown  # Return the original if no code block is found

def run(original_code, llama_model, prompt):

    if prompt == "":
        prompt = "Revise and enhance the provided code by addressing issues, optimizing, and expanding features; implement pseudocode, comments, and placeholders; suggest additional features or improvements in comments or pseudocode for iterative development in subsequent rounds. If you implement something that was suggested in a placeholder, or if you see that the code already implements it, YOU MUST remove the placeholder. Include a properly-commented summary of the overall intent of the code that mentions every intended feature. Use the same programming language as the provided code. Include at least five TODO items for potential new features in the places in the code where they should be implemented."

    messages = [{"role": "system", "content": prompt + " Here is the provided code: ```" + original_code + "```"}]
    
    response = llama_model.create_chat_completion(messages=messages)

    revised_markdown = response['choices'][0]['message']['content']

    # Extract code from the revised markdown
    revised_code = extract_code_from_markdown(revised_markdown)

    return revised_code