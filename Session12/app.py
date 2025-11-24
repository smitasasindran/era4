import streamlit as st
import torch
from model import GPT, GPTConfig
import tiktoken
from torch.nn import functional as F


st.set_page_config(page_title="Mini GPT2 Text Generator", layout="centered")

st.title("🧠 Mini GPT2")
st.write("Generate Shakespearean text")



@st.cache_resource
def load_model(weights_file, device="cpu"):
    model = GPT(GPTConfig())
    model.eval()  # evaluation mode
    model = model.to(device)
    checkpoint = torch.load(weights_file, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["model_state"])
    return model


weights_file = "gpt2-shakespeare-S12.pth"
model = load_model(weights_file)

# Some batch and token size
B = 1
T = 32


def run_inference():
    print(f"Generating some text")
    max_length = 50

    # input_text = st.session_state['input_text']

    # if user_input:
    input_text = "\n"
    print(f"Sending input to enc: {input_text}")
    enc = tiktoken.get_encoding('gpt2')
    tokens = enc.encode(input_text)
    tokens = torch.tensor(tokens)
    x = tokens.unsqueeze(0) # (1, T)
    print(f"x size: {x.size()}")

    for _ in range(max_length):
        # forward the model to get the logits
        with torch.no_grad():
            logits = model(x)[0]  # (B, T, vocab_size)
            # take the logits at the last position
            logits = logits[:, -1, :]  # (B, vocab_size)
            # get the probabilities
            probs = F.softmax(logits, dim=-1)

            # do top-k sampling of 50 (huggingface pipeline default)
            # topk_probs here becomes (5, 50), topk_indices is (5, 50)
            topk_probs, topk_indices = torch.topk(probs, 50, dim=-1)

            # select a token from the top-k probabilities
            # note: multinomial does not demand the input to sum to 1
            ix = torch.multinomial(topk_probs, 1)  # (B, 1)

            # gather the corresponding indices
            xcol = torch.gather(topk_indices, -1, ix)  # (B, 1)

            # append to the sequence
            x = torch.cat((x, xcol), dim=1)

    # Return output tokens as a sentence
    print(f"output size: {x.size()}")
    outputs = [enc.decode(out.tolist()) for out in x]
    print(f"Outputs are: {outputs}")
    output_str = "".join(outputs)
    st.session_state['text_content'] = output_str

    # else:
    #     st.session_state['text_content'] = "Greetings, Earthlings!"

# -----------------------------
# Streamlit UI
# -----------------------------
col1, col2 = st.columns([1, 2])

# my_area =  st.text_area(":blue[My text here :]",height=2000)

if 'text_content' not in st.session_state:
    st.session_state['text_content'] = ""


with col1:
    # user_input = st.text_area("**Enter text**", key="input_text", height=200)
    generate_button = st.button("Generate Text", on_click=run_inference)

with col2:
    generate_output = st.text_area("**Response**", key="output_text", height=300, value=st.session_state['text_content'])