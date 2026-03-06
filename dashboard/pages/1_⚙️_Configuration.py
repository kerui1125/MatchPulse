"""
Configuration Page - Settings and Manual Scan
"""
import streamlit as st
import sys
import os
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dashboard.utils.db_helper import apply_design_system, THEMES, THRESHOLD_PRESETS, get_threshold_from_preset, DB_PATH

# Determine environment
db_name = os.path.basename(DB_PATH)
is_production = 'prod' in db_name.lower()
env_prefix = "🌐 PROD" if is_production else "💻 DEV"

st.set_page_config(page_title=f"{env_prefix} | Configuration", page_icon="⚙️", layout="wide")

# Theme sync
if 'theme_mode' not in st.session_state:
    st.session_state.theme_mode = 'dark'

with st.sidebar:
    # Environment indicator in sidebar
    if is_production:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 8px; padding: 12px; margin-bottom: 16px; text-align: center;">
            <div style="color: white; font-size: 18px; font-weight: bold;">
                🌐 PRODUCTION
            </div>
            <div style="color: rgba(255,255,255,0.8); font-size: 12px; margin-top: 4px;">
                Port 8502
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                    border-radius: 8px; padding: 12px; margin-bottom: 16px; text-align: center;">
            <div style="color: white; font-size: 18px; font-weight: bold;">
                💻 DEVELOPMENT
            </div>
            <div style="color: rgba(255,255,255,0.8); font-size: 12px; margin-top: 4px;">
                Port 8501
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    theme = st.selectbox("Theme", list(THEMES.keys()), 
                        index=list(THEMES.keys()).index(st.session_state.theme_mode),
                        key="config_theme")
    if theme != st.session_state.theme_mode:
        st.session_state.theme_mode = theme
        st.rerun()

apply_design_system(st.session_state.theme_mode)

st.title("⚙️ Configuration")
st.divider()

# Resume Management
st.subheader("📄 Resume Management")
st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])
with col1:
    resume_file = st.file_uploader("Upload Resume (PDF)", type=['pdf'])
    if resume_file:
        st.success(f"✓ Uploaded: {resume_file.name}")
with col2:
    st.info("Current: Kerui Liu Resume.pdf")

st.divider()

# Telegram Settings
st.subheader("📱 Telegram Settings")
st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    chat_id = st.text_input("Chat ID", value="5622433525")
with col2:
    bot_token = st.text_input("Bot Token", value="6135115101:AAH...", type="password")

st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

if st.button("🧪 Test Connection"):
    if not chat_id or not bot_token or bot_token == "6135115101:AAH...":
        st.error("❌ Please enter valid Chat ID and Bot Token")
    else:
        try:
            import requests
            with st.spinner("Testing Telegram connection..."):
                # Test by sending a simple message
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": "🧪 Test connection from MatchPulse Dashboard"
                }
                response = requests.post(url, json=payload, timeout=10)
                
                if response.status_code == 200:
                    st.success("✅ Connection successful! Check your Telegram for test message.")
                else:
                    error_msg = response.json().get('description', 'Unknown error')
                    st.error(f"❌ Connection failed: {error_msg}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

st.divider()

# Matching Parameters
st.subheader("🎚️ Matching Parameters")
st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    threshold_preset = st.selectbox(
        "Match Quality",
        options=list(THRESHOLD_PRESETS.keys()),
        index=1  # Default to "Good Match (0.75+)"
    )
    threshold = get_threshold_from_preset(threshold_preset)
    st.caption(f"Threshold: {threshold}")
with col2:
    top_k = st.slider("Top-K Chunks (RAG)", 1, 10, 3)
    st.caption("Number of resume sections to analyze")

st.divider()

# Manual Scan
st.subheader("🚀 Manual Scan")
st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    limit = st.number_input("Limit (optional)", min_value=0, value=20, step=10)

st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

col2, col3 = st.columns(2)
with col2:
    if st.button("▶️ Run Scan", use_container_width=True, type="primary"):
        st.info("🔄 Starting scan... Check your terminal for logs.")
        try:
            # Run without capturing output so logs appear in terminal
            cmd = ['python', 'src/main.py', '--limit', str(limit), '--threshold', str(threshold), '--top-k', str(top_k)]
            st.code(' '.join(cmd), language='bash')
            
            # Run in background without capturing output
            process = subprocess.Popen(cmd, stdout=None, stderr=None)
            st.success(f"✓ Scan started! (PID: {process.pid})")
            st.info("📋 Check your terminal for real-time logs and progress.")
        except Exception as e:
            st.error(f"✗ Error starting scan: {str(e)}")
            
with col3:
    if st.button("🧪 Dry Run", use_container_width=True):
        st.info("🔄 Starting dry-run... Check your terminal for logs.")
        try:
            cmd = ['python', 'src/main.py', '--limit', str(limit), '--threshold', str(threshold), '--top-k', str(top_k), '--dry-run']
            st.code(' '.join(cmd), language='bash')
            
            # Run in background without capturing output
            process = subprocess.Popen(cmd, stdout=None, stderr=None)
            st.success(f"✓ Dry-run started! (PID: {process.pid})")
            st.info("📋 Check your terminal for real-time logs and progress.")
        except Exception as e:
            st.error(f"✗ Error starting dry-run: {str(e)}")
