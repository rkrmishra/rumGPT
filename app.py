import os
import streamlit as st
from langfuse.openai import OpenAI
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
from datetime import datetime


os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""
os.environ["LANGFUSE_HOST"] = "http://localhost:3000/"
os.environ["LANGFUSE_TRACING_ENVIRONMENT"] = "dev-env"

langfuse = Langfuse()
openai_gpt = OpenAI()
openai_llama = OpenAI(
    base_url = 'http://localhost:11434/v1',
    api_key='ollama', # required, but unused
)
st.title("rumGPT")
langfuse_context.update_current_trace(user_id="rum")

#-----------------------------------------------------------------------------------------
# Below code has been inspired from -
# https://docs.streamlit.io/develop/tutorials/chat-and-llm-apps/build-conversational-apps
#-----------------------------------------------------------------------------------------

# This callback is for test purpose.
def slider_on_change():
    if st.session_state["temperature_slider"]:
        print(f"st.session_state.temperature_slider: {st.session_state.temperature_slider}")

def save_feedback(index):
    print(f"index - {index}")
    st.session_state.history[index]["feedback"] = st.session_state[f"feedback_{index}"]

with st.sidebar:
    llm_to_use = st.radio(
        label="Select LLM:",
        options=["gpt-3.5-turbo", "llama3.1:8b"],
        key="llm_to_use"
    )

    add_session_input = st.text_input(
        label="Session Name:",
        value="rum-session-9",
        max_chars=50, 
        key="session_id",
    )
    add_temperature_slider = st.slider("Temperature:", min_value=0.0, 
                           max_value=2.0, value=1.0, step=0.1, 
                           key="temperature_slider", on_change=slider_on_change)
    
    add_token_slider = st.slider("Max Tokens:", min_value=1, 
                           max_value=5000, value=200, step=10, 
                           key="token_slider")
    


@observe
def process_request():
    # langfuse_context.score_current_trace(
    #     name="feedback-on-trace",
    #     value=1,
    #     comment="I like how personalized the response is",
    # )
    session_id = st.session_state.session_id
    print(f"session_id: {session_id}")
    langfuse_context.update_current_trace(session_id=session_id)

    if st.session_state.llm_to_use == "gpt-3.5-turbo":
        client = openai_gpt
    elif st.session_state.llm_to_use == "llama3.1:8b":
        client = openai_llama
    else:
        client = openai_gpt

    stream = client.chat.completions.create(
            #model=st.session_state["openai_model"],
            model=st.session_state.llm_to_use if st.session_state["llm_to_use"] else "gpt-3.5-turbo",
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.history
            ],
            temperature = st.session_state.temperature_slider if st.session_state["temperature_slider"] else 1,
            max_completion_tokens = st.session_state.token_slider if st.session_state["token_slider"] else 100,
            stream=True,
        )
    response = st.write_stream(stream)
    return response

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

# if "messages" not in st.session_state:
#     st.session_state.messages = []

# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])

if "history" not in st.session_state:
    st.session_state.history = []

for i, message in enumerate(st.session_state.history):
    with st.chat_message(message["role"]):
        #st.write(message["content"])
        st.markdown(message["content"])
        if message["role"] == "assistant":
            feedback = message.get("feedback", None)
            print(f"feedback: {feedback}")
            st.session_state[f"feedback_{i}"] = feedback
            st.feedback(
                "thumbs",
                key=f"feedback_{i}",
                disabled=feedback is not None,
                on_change=save_feedback,
                args=[i],
            )

if prompt := st.chat_input("What is up?"):
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("human"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = process_request()
        st.feedback(
            "thumbs",
            key=f"feedback_{len(st.session_state.history)}",
            on_change=save_feedback,
            args=[len(st.session_state.history)],
        )

    langfuse.flush()
    st.session_state.history.append({"role": "assistant", "content": response})
