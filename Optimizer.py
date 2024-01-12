import os
import re
import math
from llama_cpp import Llama
import time
import json
import gc

threads = [0,2,4]
threads_batch = [0,2,4,6,8]
n_batch = [4, 8, 16, 32, 64, 128, 256, 512]
no_mmap = [True, False]
mlock = [True, False]
n_gpu_layers = [5,10,15,20,25,30,33]
n_ctx = [32768]
model_filename = ["mistral-7b-instruct-v0.2.Q2_K.gguf",
                  "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
                  "mistral-7b-instruct-v0.2.Q5_K_M.gguf",
                  "mistral-7b-instruct-v0.2.Q8_0.gguf"]
max_tokens = [32768]

# Define default llama.cpp parameters
default_llama_params = {
    "loader": "llama.cpp",
    "cpu": False,
    "threads": 0,
    "threads_batch": 0,
    "n_batch": 512,
    "no_mmap": False,
    "mlock": False,
    "no_mul_mat_q": False,
    "n_gpu_layers": 0,
    "tensor_split": "",
    "n_ctx": 32768,
    "compress_pos_emb": 1,
    "alpha_value": 1,
    "rope_freq_base": 0,
    "numa": False,
    "model": "models/",
    "temperature": 1.0,
    "top_p": 0.99,
    "top_k": 85,
    "repetition_penalty": 1.01,
    "typical_p": 0.68,
    "tfs": 0.68,
    "max_tokens": 32768
}

# List to store results
results = []

# Iterate through every combination of variables
for thread in threads:
    for thread_batch in threads_batch:
        for batch_size in n_batch:
            for mmap_value in no_mmap:
                for lock_value in mlock:
                    for gpu_layer in n_gpu_layers:
                        for context_size in n_ctx:
                            for model_file in model_filename:
                                for token_limit in max_tokens:
                                    try:
                                        # Update llama_params with current variable values
                                        llama_params = default_llama_params.copy()
                                        llama_params["threads"] = thread
                                        llama_params["threads_batch"] = thread_batch
                                        llama_params["n_batch"] = batch_size
                                        llama_params["no_mmap"] = mmap_value
                                        llama_params["mlock"] = lock_value
                                        llama_params["n_gpu_layers"] = gpu_layer
                                        llama_params["n_ctx"] = context_size
                                        llama_params["model"] += model_file
                                        llama_params["max_tokens"] = token_limit

                                        # Print selected variable values
                                        print("\n\n\n\n\n\nSelected Variable Values:")
                                        print(llama_params)

                                        llama_model = Llama(llama_params["model"], **llama_params)

                                        # Execute the process that runs inference and track tokens per second
                                        start_time = time.time()

                                        prompt = "Improve the provided code by addressing identified issues, optimizing, and extending functionality. Provide ONLY ONE complete revision so that anyone reviewing your new code can do so without having access to the prior code. Use pseudocode, comments, and placeholders to document changes. Propose additional features or improvements through comments or pseudocode for subsequent iterations. Remove placeholders when the suggested feature is implemented or already present. Embed at least five TODO items specifying potential new features inline in the code."
                                        messages = [{"role": "user", "content": f"<s>[INST] {prompt} Here is the current code: ```PSEUDOCODE C# Console app that says hello world``` [/INST]"}]

                                        response = llama_model.create_chat_completion(messages=messages)
                                        
                                        revised_markdown = response['choices'][0]['message']['content']

                                        end_time = time.time()

                                        # Dispose of the llama_model
                                        del llama_model
                                        gc.collect()

                                        # Store results in the list
                                        results.append({
                                            "config": llama_params,
                                            "time per char (not token)": (end_time - start_time) / len(revised_markdown)
                                        })

                                        # Sort results by time
                                        sorted_results = sorted(results, key=lambda x: x["time per char (not token)"])

                                        # Save results to file
                                        with open("results.txt", "w") as file:
                                            json.dump(sorted_results, file, indent=2)

                                    except Exception as e:
                                        # Log failures
                                        print(f"Error occurred: {e}")

                                        results.append({
                                            "config": llama_params,
                                            "time per char (not token)": f"Error occurred: {e}"
                                        })
                                        
                                        # Sort results by time
                                        sorted_results = sorted(results, key=lambda x: x["time per char (not token)"])

                                        # Save results to file
                                        with open("results.txt", "w") as file:
                                            json.dump(sorted_results, file, indent=2)