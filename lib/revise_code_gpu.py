import time
import gc
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig, TextStreamer
from lib.config_manager import load_config, get_config, update_config

def extract_code_from_markdown(markdown):
    code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', markdown, re.DOTALL)
    return code_blocks[0].strip() if code_blocks else markdown.strip()

def run(original_code, max_context, prompt):

    model_name_or_path = get_config("model_filename", "TheBloke_Mistral-7B-Instruct-v0.2-AWQ")
    model_folder = get_config("model_folder", "models/")

    full_path = model_folder + model_name_or_path

    # Get default prompt from config or use a default value
    default_prompt = get_config('default_prompt', "Improve the provided code by addressing identified issues, optimizing, and extending functionality. Provide ONLY ONE complete revision so that anyone reviewing your new code can do so without having access to the prior code. Use pseudocode, comments, and placeholders to document changes. Propose additional features or improvements through comments or pseudocode for subsequent iterations. Remove placeholders when the suggested feature is implemented or already present. Embed at least five TODO items specifying potential new features inline in the code.")

    # Check if extracting from Markdown is enabled in config
    extract_from_markdown = get_config('extract_from_markdown', True)

    # Use the provided prompt if given, else use the one from config
    prompt = prompt if prompt else default_prompt

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(full_path)
    model = AutoModelForCausalLM.from_pretrained(full_path)

    # Move model to CUDA device
    model = model.cuda()

    prompt=f"<s>[INST] {default_prompt} Here is the current code: ```{original_code}``` [/INST]"

    # Move prompt tensor to CUDA device
    inputs = tokenizer.encode(prompt, return_tensors="pt", add_special_tokens=False).cuda()

    generation_config = GenerationConfig(
        max_new_tokens=max_context, 
        do_sample=True, 
        temperature=1.0,
        top_p=0.99,
        top_k=85,
        repetition_penalty=1.01,
        eos_token_id=model.config.eos_token_id,
        num_return_sequences=1,
        pad_token_id=model.config.pad_token_id,
        max_context=max_context
    )

    print(torch.cuda.memory_summary(device=None, abbreviated=False))

    # Measure the time taken for generation
    start_time = time.time()
    outputs = model.generate(inputs, generation_config=generation_config)
    end_time = time.time()

    # Calculate tokens per second
    total_tokens = outputs.shape[1]  # Assuming outputs is a tensor with generated tokens
    elapsed_time = end_time - start_time
    tokens_per_second = total_tokens / elapsed_time

    # Extract only the assistant's response
    response = tokenizer.decode(outputs[0], skip_special_tokens=True).split("[/INST]")[1].strip()

    print("GENERATED RESPONSE")
    print(response)
    print("END GENERATED RESPONSE")

    # Print the results
    print(f"Generated {total_tokens} tokens in {elapsed_time:.2f} seconds.")
    print(f"Tokens per second: {tokens_per_second:.2f}")

    revised_code = extract_code_from_markdown(response) if extract_from_markdown else response

    return revised_code