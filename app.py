import streamlit as st
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load env locally
load_dotenv()

# --- Page config ---
st.set_page_config(page_title="Virtual Strategy Office", layout="wide")

# --- Password Gate ---
if "authenticated" not in st.session_state:
    pwd = st.text_input("Enter Access Code", type="password")
    correct_pwd = os.getenv("APP_PASSWORD") or st.secrets.get("APP_PASSWORD", "demo123")
    if pwd == correct_pwd:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

st.title("Virtual Strategy Office — Executive Console")
st.info("Private advisory console — powered by founder-led strategic intelligence.")

# --- Load OpenAI ---
api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# --- Load Context ---
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

contextual = load_json("context/contextual_layer.json")
data_snapshot = load_json("context/data_snapshot.json")
audit_snapshot = load_json("context/audit_snapshot.json")

with open("prompts/advisory_prompt.txt") as f:
    system_prompt = f.read()

# --- Memory ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Display history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- User input ---
user_input = st.chat_input("Ask a strategic question...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):

            full_system = f"""
{system_prompt}

Context:
{json.dumps(contextual, indent=2)}

Data Snapshot:
{json.dumps(data_snapshot, indent=2)}

Audit Snapshot:
{json.dumps(audit_snapshot, indent=2)}
"""

            response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[
        {"role": "system", "content": full_system},
        *st.session_state.messages
    ]
)

            reply = response.choices[0].message.content
            st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})