import os
import requests
from llama_cpp import Llama

max_tokens = 16384

def download_file(file_url, file_name):
    if not os.path.exists(file_name):
        response = requests.get(file_url)
        with open(file_name, "wb") as file:
            file.write(response.content)
        print(f"{file_name} downloaded successfully.")
    else:
        print(f"{file_name} already exists in the current directory.")

def initialize_llama_model(model_name):
    # Define llama.cpp parameters
    llama_params = {
        "loader": "llama.cpp",
        "cpu": False,
        "threads": 0,
        "threads_batch": 0,
        "n_batch": 512,
        "no_mmap": False,
        "mlock": True,
        "no_mul_mat_q": False,
        "n_gpu_layers": 0,
        "tensor_split": "",
        "n_ctx": max_tokens,
        "compress_pos_emb": 1,
        "alpha_value": 1,
        "rope_freq_base": 0,
        "numa": False,
        "model": model_name,
        "temperature": 0.87,
        "top_p": 0.99,
        "top_k": 85,
        "repetition_penalty": 1.01,
        "typical_p": 0.68,
        "tfs": 0.68,
        "max_tokens": max_tokens
    }
    return Llama(model_name, **llama_params)

def process_file(file_path, output_directory, llama_model, rounds=1):
    with open(file_path, 'r') as file:
        file_content = file.read()

    for round_number in range(1, rounds + 1):
        messages = [{"role": "system", "content": f"Can you revise this prompt to be more clear to an LLM? It should contain all required details from the original. If any sample records are provided, the characteristics of those files should be conveyed as requirements. The revised prompt should be conveyed as a list of tasks with as much detail as possible. Here is the current prompt: {file_content}"}]
        response = llama_model.create_chat_completion(messages=messages)
        result = response['choices'][0]['message']['content']
        output_path = os.path.join(output_directory, f"{os.path.splitext(os.path.basename(file_path))[0]}_round{round_number}.txt")

        with open(output_path, "w") as file:
            file.write(result)

        print(f"Revised prompt written to '{output_path}':\n{result}")

if __name__ == "__main__":
    file_url = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/blob/main/mistral-7b-instruct-v0.2.Q5_K_S.gguf"
    file_name = "mistral-7b-instruct-v0.2.Q5_K_S.gguf"
    download_file(file_url, file_name)

    model_name = file_name
    llama_model = initialize_llama_model(model_name)

    directory_path = ".\\Prompt\\Source"
    output_directory = ".\\Prompt\\Output"
    os.makedirs(output_directory, exist_ok=True)

    files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]

    for file_name in files:
        file_path = os.path.join(directory_path, file_name)
        print(f"Processing file: {file_name}")
        process_file(file_path, output_directory, llama_model)
