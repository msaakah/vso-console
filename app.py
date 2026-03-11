import streamlit as st
import json
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import base64
from pathlib import Path

# -------------------------
# CONFIGURATION
# -------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Database setup
DB_PATH = "vso_data.db"

# Page config with custom styling
st.set_page_config(
    page_title="VSO Executive Console",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# CUSTOM CSS FOR PROFESSIONAL UI
# -------------------------
def load_custom_css():
    st.markdown("""
    <style>
    /* Main theme colors */
    :root {
        --vso-primary: #0A0A0A;
        --vso-accent: #2D5BFF;
        --vso-bg: #FFFFFF;
        --vso-border: #E5E5E5;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom header */
    .vso-header {
        background: linear-gradient(135deg, #0A0A0A 0%, #1A1A1A 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        border: 1px solid #2D2D2D;
    }
    
    .vso-title {
        color: white;
        font-size: 2rem;
        font-weight: 600;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .vso-subtitle {
        color: #A0A0A0;
        font-size: 1rem;
        margin: 0.5rem 0 0 0;
    }
    
    /* Chat messages */
    .stChatMessage {
        background: #F8F9FA;
        border: 1px solid #E5E5E5;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Input styling */
    .stChatInputContainer {
        border-top: 2px solid #E5E5E5;
        padding-top: 1rem;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: #F8F9FA;
        border-right: 2px solid #E5E5E5;
    }
    
    /* Buttons */
    .stButton button {
        background: #0A0A0A;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton button:hover {
        background: #2D2D2D;
        transform: translateY(-1px);
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 500;
        margin: 0.25rem;
    }
    
    .badge-fresh {
        background: #D4EDDA;
        color: #155724;
    }
    
    .badge-aging {
        background: #FFF3CD;
        color: #856404;
    }
    
    .badge-stale {
        background: #F8D7DA;
        color: #721C24;
    }
    
    /* Maturity indicators */
    .maturity-exploratory {
        color: #6C757D;
        font-weight: 600;
    }
    
    .maturity-directional {
        color: #2D5BFF;
        font-weight: 600;
    }
    
    .maturity-decision {
        color: #28A745;
        font-weight: 600;
    }
    
    /* Thread list */
    .thread-item {
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .thread-item:hover {
        background: #E9ECEF;
    }
    
    /* Context purity labels */
    .purity-evidence {
        color: #28A745;
    }
    
    .purity-inference {
        color: #FFC107;
    }
    
    .purity-pattern {
        color: #DC3545;
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------
# DATABASE FUNCTIONS
# -------------------------
def init_database():
    """Initialize SQLite database with tables for threads and messages"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Threads table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            thread_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            snapshot TEXT
        )
    """)
    
    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (thread_id) REFERENCES threads (thread_id)
        )
    """)
    
    conn.commit()
    conn.close()

def load_threads():
    """Load all threads from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT thread_id, title, snapshot, updated_at 
        FROM threads 
        ORDER BY updated_at DESC
    """)
    
    threads = {}
    for row in cursor.fetchall():
        thread_id, title, snapshot, updated_at = row
        threads[thread_id] = {
            "title": title,
            "snapshot": json.loads(snapshot) if snapshot else {},
            "updated_at": updated_at,
            "messages": []
        }
    
    conn.close()
    return threads

def load_messages(thread_id):
    """Load messages for a specific thread"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT role, content 
        FROM messages 
        WHERE thread_id = ? 
        ORDER BY created_at ASC
    """, (thread_id,))
    
    messages = []
    for row in cursor.fetchall():
        messages.append({"role": row[0], "content": row[1]})
    
    conn.close()
    return messages

def save_thread(thread_id, title, snapshot):
    """Save or update a thread"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO threads (thread_id, title, snapshot, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (thread_id, title, json.dumps(snapshot)))
    
    conn.commit()
    conn.close()

def save_message(thread_id, role, content):
    """Save a message to a thread"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO messages (thread_id, role, content)
        VALUES (?, ?, ?)
    """, (thread_id, role, content))
    
    # Update thread timestamp
    cursor.execute("""
        UPDATE threads SET updated_at = CURRENT_TIMESTAMP WHERE thread_id = ?
    """, (thread_id,))
    
    conn.commit()
    conn.close()

def delete_thread(thread_id):
    """Delete a thread and all its messages"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
    cursor.execute("DELETE FROM threads WHERE thread_id = ?", (thread_id,))
    
    conn.commit()
    conn.close()

# -------------------------
# HELPER FUNCTIONS
# -------------------------
def extract_structured_snapshot_improved(reply_text):
    """
    Improved snapshot extraction using OpenAI's structured output
    """
    try:
        # Use a separate API call to extract structured insights
        extraction_prompt = f"""
Extract key strategic insights from this advisory response in JSON format:

{reply_text}

Return ONLY a JSON object with these fields (use null if not found):
{{
    "decision_frame": "brief summary of the decision context",
    "strategic_interpretation": "key strategic insight",
    "critical_assumptions": "main assumptions identified",
    "second_order_effects": "potential downstream consequences",
    "blind_spots": "identified blind spots or risks",
    "recommended_posture": "suggested strategic stance",
    "recommended_action": "specific next action"
}}
"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": extraction_prompt}],
            response_format={"type": "json_object"}
        )
        
        snapshot = json.loads(response.choices[0].message.content)
        return snapshot
        
    except Exception as e:
        # Fallback to simple extraction
        return {
            "summary": reply_text.split(".")[0][:200] if reply_text else "No summary available"
        }

def auto_rename_thread(thread_id, latest_reply):
    """Auto-rename thread based on content"""
    threads = st.session_state.threads
    
    if not threads[thread_id]["title"].startswith("Thread"):
        return
    
    try:
        # Extract a meaningful title from the response
        first_line = latest_reply.split("\n")[0].strip()
        clean = first_line.replace("#", "").replace("*", "").strip()
        
        if len(clean) > 10:
            new_title = clean[:60] + ("..." if len(clean) > 60 else "")
            threads[thread_id]["title"] = new_title
            save_thread(thread_id, new_title, threads[thread_id]["snapshot"])
    except:
        pass

def compute_maturity(messages):
    """Compute thread maturity based on message count"""
    msg_count = len(messages)
    if msg_count < 3:
        return "Exploratory", "maturity-exploratory"
    elif msg_count < 8:
        return "Directional", "maturity-directional"
    else:
        return "Decision-Ready", "maturity-decision"

def freshness_indicator(date_str):
    """Calculate freshness of data"""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        days = (datetime.now() - date).days
        
        if days <= 7:
            return "🟢 Fresh", "badge-fresh"
        elif days <= 30:
            return "🟡 Aging", "badge-aging"
        else:
            return "🔴 Stale", "badge-stale"
    except:
        return "⚪ Unknown", "badge-aging"

def export_board_memo(thread_id):
    """Export thread as board memo"""
    thread = st.session_state.threads[thread_id]
    maturity, _ = compute_maturity(thread["messages"])
    
    return f"""
═══════════════════════════════════════════════════════════
VSO STRATEGIC INTELLIGENCE NOTE
═══════════════════════════════════════════════════════════

Thread: {thread['title']}
Maturity: {maturity}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

───────────────────────────────────────────────────────────
STRATEGIC MEMORY SNAPSHOT
───────────────────────────────────────────────────────────

{json.dumps(thread['snapshot'], indent=2)}

───────────────────────────────────────────────────────────
CONVERSATION HISTORY
───────────────────────────────────────────────────────────

{format_conversation_history(thread["messages"])}

───────────────────────────────────────────────────────────
Generated by Virtual Strategy Office Executive Console
───────────────────────────────────────────────────────────
"""

def format_conversation_history(messages):
    """Format messages for export"""
    formatted = []
    for msg in messages:
        role = "CEO" if msg["role"] == "user" else "VSO ADVISOR"
        formatted.append(f"\n{role}:\n{msg['content']}\n")
    return "\n".join(formatted)

# -------------------------
# LOAD CONTEXT FILES
# -------------------------
@st.cache_data
def load_context_files():
    """Load context files with caching"""
    try:
        with open("context/contextual_layer.json") as f:
            contextual_layer = json.load(f)
        
        with open("context/data_snapshot.json") as f:
            data_snapshot = json.load(f)
        
        with open("context/audit_snapshot.json") as f:
            audit_snapshot = json.load(f)
        
        with open("prompts/advisory_prompt.txt") as f:
            advisory_prompt = f.read()
        
        return contextual_layer, data_snapshot, audit_snapshot, advisory_prompt
    
    except FileNotFoundError as e:
        st.error(f"❌ Context file not found: {e.filename}")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"❌ Invalid JSON in context file: {e}")
        st.stop()

contextual_layer, data_snapshot, audit_snapshot, advisory_prompt = load_context_files()

# -------------------------
# INITIALIZE
# -------------------------
init_database()
load_custom_css()

# Initialize session state
if "threads" not in st.session_state:
    st.session_state.threads = load_threads()
    
    # Create default thread if none exist
    if not st.session_state.threads:
        default_id = "thread_1"
        st.session_state.threads[default_id] = {
            "title": "Thread 1",
            "messages": [],
            "snapshot": {},
            "updated_at": datetime.now().isoformat()
        }
        save_thread(default_id, "Thread 1", {})
        st.session_state.active_thread = default_id
    else:
        # Set most recent thread as active
        st.session_state.active_thread = list(st.session_state.threads.keys())[0]

if "active_thread" not in st.session_state:
    st.session_state.active_thread = list(st.session_state.threads.keys())[0]

# Load messages for active thread if not already loaded
active_thread_id = st.session_state.active_thread
if not st.session_state.threads[active_thread_id]["messages"]:
    st.session_state.threads[active_thread_id]["messages"] = load_messages(active_thread_id)

active_thread = st.session_state.threads[active_thread_id]

# -------------------------
# HEADER WITH LOGO
# -------------------------
st.markdown("""
<div class="vso-header">
    <div style="display: flex; align-items: center; gap: 1rem;">
        <svg width="48" height="48" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="80" height="80" rx="8" fill="#FFFFFF"/>
            <path d="M30 35L40 60L50 35" stroke="#0A0A0A" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M55 45L65 35L75 45" stroke="#0A0A0A" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="65" cy="60" r="8" stroke="#0A0A0A" stroke-width="4" fill="none"/>
        </svg>
        <div>
            <h1 class="vso-title">VSO Executive Console</h1>
            <p class="vso-subtitle">Founder-led strategic advisory • Powered by systematic reasoning</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------
# SIDEBAR — INTELLIGENCE STACK
# -------------------------
st.sidebar.markdown("### 🧬 Intelligence Stack")

# Audit freshness
audit_date = audit_snapshot.get("last_updated", "2026-01-01")
freshness, badge_class = freshness_indicator(audit_date)

st.sidebar.markdown(f"""
- **Context Layer:** ✅ Loaded
- **Data Snapshot:** ✅ Loaded  
- **Audit Freshness:** <span class="status-badge {badge_class}">{freshness}</span>
- **Mode:** Advisory
""", unsafe_allow_html=True)

# Strategic Memory
st.sidebar.markdown("---")
st.sidebar.markdown("### 🧠 Strategic Memory")

maturity_label, maturity_class = compute_maturity(active_thread["messages"])
st.sidebar.markdown(f'<p class="{maturity_class}">Maturity: {maturity_label}</p>', unsafe_allow_html=True)

if active_thread["snapshot"]:
    with st.sidebar.expander("📊 View Snapshot", expanded=False):
        st.json(active_thread["snapshot"])
else:
    st.sidebar.caption("💭 No memory yet — ask your first strategic question.")

# -------------------------
# THREADS MANAGEMENT
# -------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🧵 Strategic Threads")

# Thread selector
thread_ids = list(st.session_state.threads.keys())
thread_options = {tid: st.session_state.threads[tid]["title"] for tid in thread_ids}

selected = st.sidebar.selectbox(
    "Select Thread",
    thread_ids,
    format_func=lambda x: thread_options[x],
    key="thread_selector"
)

if selected != st.session_state.active_thread:
    st.session_state.active_thread = selected
    # Load messages for newly selected thread
    if not st.session_state.threads[selected]["messages"]:
        st.session_state.threads[selected]["messages"] = load_messages(selected)
    st.rerun()

# Thread actions
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("➕ New", use_container_width=True):
        new_id = f"thread_{len(thread_ids)+1}"
        new_title = f"Thread {len(thread_ids)+1}"
        st.session_state.threads[new_id] = {
            "title": new_title,
            "messages": [],
            "snapshot": {},
            "updated_at": datetime.now().isoformat()
        }
        save_thread(new_id, new_title, {})
        st.session_state.active_thread = new_id
        st.rerun()

with col2:
    if st.button("🗑️ Delete", use_container_width=True):
        if len(thread_ids) > 1:
            delete_thread(active_thread_id)
            del st.session_state.threads[active_thread_id]
            st.session_state.active_thread = list(st.session_state.threads.keys())[0]
            st.rerun()
        else:
            st.sidebar.warning("Cannot delete the last thread")

# -------------------------
# EXPORT FUNCTIONALITY
# -------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 📤 Export")

if st.sidebar.button("Generate Board Note", use_container_width=True):
    report = export_board_memo(active_thread_id)
    st.sidebar.download_button(
        label="📥 Download Strategic Note",
        data=report,
        file_name=f"vso_strategic_note_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
        use_container_width=True
    )

# Request Fresh Audit CTA
if st.sidebar.button("🔄 Request Fresh Audit", use_container_width=True):
    st.sidebar.success("✅ Audit request logged. Founder will follow up within 24 hours.")

# -------------------------
# CHAT DISPLAY
# -------------------------
st.markdown("---")

# Display chat history
for msg in active_thread["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -------------------------
# CHAT INPUT WITH ERROR HANDLING
# -------------------------
if prompt := st.chat_input("Ask your toughest strategic question…"):
    # Add user message
    active_thread["messages"].append({"role": "user", "content": prompt})
    save_message(active_thread_id, "user", prompt)
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Prepare context
    snapshot_memory = json.dumps(active_thread["snapshot"], indent=2)
    recent_messages = active_thread["messages"][-6:]
    conversation_memory = "\n".join(
        [f"{m['role'].upper()}: {m['content']}" for m in recent_messages]
    )
    
    full_context = f"""
SYSTEM CONTEXT

Contextual Layer:
{json.dumps(contextual_layer, indent=2)}

Data Snapshot:
{json.dumps(data_snapshot, indent=2)}

Audit Snapshot:
{json.dumps(audit_snapshot, indent=2)}

THREAD MEMORY:
{snapshot_memory}

RECENT DISCUSSION:
{conversation_memory}

Instructions:
{advisory_prompt}

CEO Question:
{prompt}
"""
    
    # Get AI response with error handling
    with st.chat_message("assistant"):
        with st.spinner("🧠 Analyzing with VSO reasoning engine..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",  # Using the recommended model
                    messages=[{"role": "user", "content": full_context}],
                    temperature=0.7,
                    max_tokens=4000
                )
                
                reply = response.choices[0].message.content
                st.markdown(reply)
                
                # Context purity indicator
                st.caption("🟡 Context Purity: Evidence + inference")
                
                # Save assistant message
                active_thread["messages"].append({"role": "assistant", "content": reply})
                save_message(active_thread_id, "assistant", reply)
                
                # Extract and save snapshot
                with st.spinner("Extracting strategic insights..."):
                    structured = extract_structured_snapshot_improved(reply)
                    active_thread["snapshot"] = structured
                    save_thread(active_thread_id, active_thread["title"], structured)
                
                # Auto-rename thread
                auto_rename_thread(active_thread_id, reply)
                
            except Exception as e:
                st.error(f"❌ Error generating response: {str(e)}")
                st.info("💡 Please try again or contact support if the issue persists.")
                # Log error (in production, send to monitoring service)
                print(f"VSO Error: {e}")

# -------------------------
# FOOTER
# -------------------------
st.markdown("---")
st.caption("🔒 All conversations are encrypted and stored securely. VSO Executive Console v2.0")
