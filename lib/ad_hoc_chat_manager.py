from multiprocessing import Process, Array
from lib.config_manager import get_config
from llama_cpp import Llama

def run(llama_model, prompt, result):

    result.value += prompt.encode('utf-8')
    result.value += "\n\n".encode('utf-8')

    stream = llama_model.create_completion(
        f"[INST]{prompt}[/INST]<s>",
        max_tokens=get_config('n_ctx', 32768),
        temperature=get_config('temperature', 1.0),
        top_p=get_config('top_p', 0.99),
        top_k=get_config('top_k', 85),
        repeat_penalty=get_config('repetition_penalty', 0.99),
        stream=True)

    for output in stream:
        with result.get_lock():
            result.value += output['choices'][0]['text'].encode('utf-8')
        print(result.value)

def run_batch(llama_model, prompt, result):
    batch_process = Process(target=run, args=(llama_model, prompt, result))
    batch_process.start()