import torch
import time
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig, TextStreamer

model_name = 'TheBloke/neural-chat-7B-v3-1-AWQ'
model_name = 'TheBloke/Mistral-7B-Instruct-v0.2-AWQ'

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Move model to CUDA device
model = model.cuda()

system_input = "Improve the provided code by addressing identified issues, optimizing, and extending functionality. Provide ONLY ONE complete revision so that anyone reviewing your new code can do so without having access to the prior code. Use pseudocode, comments, and placeholders to document changes. Propose additional features or improvements through comments or pseudocode for subsequent iterations. Remove placeholders when the suggested feature is implemented or already present. Embed at least five TODO items specifying potential new features inline in the code."
user_input = "PSEUDOCODE Generate a C# console app that says hello world"

system_input = "Write C# code to answer the question"
user_input = "What is 2 + 2?"

prompt = f"### System:\n{system_input}\n### User:\n{user_input}\n### Assistant:\n"
prompt=f"<s>[INST] {system_input} Here is the current code: ```{user_input}``` [/INST]"

# Move prompt tensor to CUDA device
inputs = tokenizer.encode(prompt, return_tensors="pt", add_special_tokens=False).cuda()
streamer = TextStreamer(tokenizer)

generation_config = GenerationConfig(
    max_new_tokens=32768, 
    do_sample=True, 
    temperature=1.0,
    top_p=0.99,
    top_k=85,
    repetition_penalty=1.01,
    eos_token_id=model.config.eos_token_id,
    num_return_sequences=1,
    pad_token_id=model.config.pad_token_id,
    max_context=32768
)

# Measure the time taken for generation
start_time = time.time()
outputs = model.generate(inputs, streamer=streamer, generation_config=generation_config)
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