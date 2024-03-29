import gradio as gr
import torch
from transformers import AutoTokenizer, StoppingCriteria, StoppingCriteriaList, TextIteratorStreamer, AutoModelForCausalLM
from threading import Thread

model = AutoModelForCausalLM.from_pretrained("togethercomputer_RedPajama-INCITE-Chat-3B-v1", torch_dtype=torch.float16)
# list of the tokens to be used by the model
tokenizer = AutoTokenizer.from_pretrained("togethercomputer_RedPajama-INCITE-Chat-3B-v1")
# sets the model to use the GPU  for faster processing
model = model.to('cuda:0')

def echo(message, history):
    return message

# class to tell the model when to stop generating a response
class StopOnTokens(StoppingCriteria):
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        stop_ids = [29, 0]
        for stop_id in stop_ids:
            if input_ids[0][-1] == stop_id:
                return True
        return False
    
# takes in the new message and the history of the thread to generate a response
def predict(message, history):

    history_transformer_format = history + [[message, ""]]
    stop = StopOnTokens()

    messages = "".join(["".join(["\n<human>:"+item[0], "\n<bot>:"+ item[1]])
                for item in history_transformer_format])

    model_inputs = tokenizer([messages], return_tensors="pt").to("cuda")

    # Streams the response from the model so we can see the responses as it is made and don't need to wait for a full response
    streamer = TextIteratorStreamer(tokenizer, timeout=10., skip_prompt=True, skip_special_tokens=True)
    generate_kwargs = dict(
        model_inputs,
        streamer=streamer,
        max_new_tokens=1024, # limits the size the response
        do_sample=True,
        top_p=0.95, # limits selections of next token
        top_k=1000, # limits selections of next token
        temperature=1.0, # adds randomness
        num_beams=1,
        stopping_criteria=StoppingCriteriaList([stop]) # when to stop generating a response
        )
    t = Thread(target=model.generate, kwargs=generate_kwargs)
    t.start()

    partial_message  = ""
    for new_token in streamer:
        if new_token != '<':
            partial_message += new_token
            yield partial_message

demo = gr.ChatInterface(fn=predict, examples=["hello", "how are you", "hola"], title="Chatbot demo")
demo.launch()

