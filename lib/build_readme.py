import os
from llama_cpp import Llama

# Call the function to revise the prompt
# readme = build_readme(original_code, llama_model)

def run(original_code, llama_model):
    messages = [{"role": "system", "content": f"Please generate a comprehensive Readme in markdown for the following code: {original_code}"}]
    response = llama_model.create_chat_completion(messages=messages)
    readme = response['choices'][0]['message']['content']
    return readme