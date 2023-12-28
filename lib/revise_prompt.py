import os
from llama_cpp import Llama  # Assuming llama_cpp is the module containing the Llama class

# Call the function to revise the prompt
# revised_prompt = revise_prompt(original_prompt, llama_model)

def revise_prompt(original_prompt, llama_model):
    messages = [{"role": "system", "content": f"Can you revise this prompt to be more clear to an LLM? It should contain all required details from the original. If any sample records are provided, the characteristics of those files should be conveyed as requirements. The revised prompt should be conveyed as a list of tasks with as much detail as possible. Here is the current prompt: {original_prompt}"}]
    response = llama_model.create_chat_completion(messages=messages)
    revised_prompt = response['choices'][0]['message']['content']
    return revised_prompt