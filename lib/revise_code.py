import os
import re
from llama_cpp import Llama

# Call the function to revise the prompt
# revised_code = revise_code(original_code, llama_model)

def run(original_code, llama_model):

    # Alternate generation and cleanup
    if "TODO" in original_code or "PLACEHOLDER" in original_code:
        messages = [{"role": "system", "content": "Revise and enhance the provided code by implementing any placeholder or TODO items. Add detailed comments throughout to explain the functionality. Clean up the code to make it more organized and clear. Include a properly-commented summary of the overall intent of the code that mentions every intended feature. Use the same programming language as the provided code. YOU MUST provide a complete revision of the provided code. Here is the provided code: ```" + original_code + "```"}]
    else:
        messages = [{"role": "system", "content": "Revise and enhance the provided code by addressing issues, optimizing, and expanding features; implement pseudocode, comments, and placeholders; suggest additional features or improvements in comments or pseudocode for iterative development in subsequent rounds. If you implement something that was suggested in a placeholder, or if you see that the code already implements it, YOU MUST remove the placeholder. Include a properly-commented summary of the overall intent of the code that mentions every intended feature. Use the same programming language as the provided code. Include at least five TODO items for potential new features in the places in the code where they should be implemented. Here is the provided code: ```" + original_code + "```"}]
    
    response = llama_model.create_chat_completion(messages=messages)

    revised_code = response['choices'][0]['message']['content']

    pattern = re.compile(r'(\w+)(.*?)', re.DOTALL)
    match = re.search(pattern, original_code)
    if match:
        revised_code = match.group(2)

    return revised_code