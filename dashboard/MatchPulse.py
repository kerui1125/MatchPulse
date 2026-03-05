"""
MatchPulse Dashboard - Main Entry Point
"""
import streamlit as st
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dashboard.utils.db_helper import (
    get_statistics, get_recent_jobs, apply_design_system, THEMES
)

# Page config
st.set_page_config(
    page_title="MatchPulse",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize theme in session state (default to dark)
if 'theme_mode' not in st.session_state:
    st.session_state.theme_mode = 'dark'

# Theme selector in sidebar
with st.sidebar:
    st.title("🎨 Theme")
    theme = st.selectbox(
        "Mode",
        options=list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.theme_mode),
        key="theme_selector"
    )
    if theme != st.session_state.theme_mode:
        st.session_state.theme_mode = theme
        st.rerun()

# Apply theme
apply_design_system(st.session_state.theme_mode)

# Header
st.title("🎯 MatchPulse")
st.markdown("""
<p class="body-text" style="color: var(--text-secondary); margin-bottom: 24px;">
Centralized dashboard for managing AI-matched job opportunities. 
View match history, analyze fit explanations, and configure scanning parameters.
</p>
""", unsafe_allow_html=True)

# Supported companies info
st.markdown("""
<div style="background: var(--bg-muted); border-left: 4px solid var(--primary); border-radius: 8px; padding: 16px; margin-bottom: 24px;">
    <p style="margin: 0; color: var(--text-primary); font-size: 14px; line-height: 22px;">
        <strong>📌 MVP Version:</strong> Currently supports 7 companies: NVIDIA, Google, Amazon, Microsoft, Salesforce, Oracle, and Expedia. 
        <span style="color: var(--text-secondary);">Additional companies coming soon.</span>
    </p>
</div>
""", unsafe_allow_html=True)

st.divider()

# Current Settings Info
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div class="caption">
    <strong>Current Threshold:</strong> 0.72 (Good Match) • <strong>Top-K:</strong> 3 chunks
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="caption" style="text-align: right;">
    Last scan: Recently • Next scan: Manual
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Quick stats
st.subheader("📊 Quick Statistics")
st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)
stats = get_statistics()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Jobs", stats['total_jobs'])
with col2:
    st.metric("Matched", stats['matched'])
with col3:
    st.metric("Pushed", stats['pushed'])
with col4:
    st.metric("Avg Score", f"{stats['avg_score']:.3f}")

st.divider()

# Recent matches
st.subheader("🔥 Recent Matches")
st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)
recent = get_recent_jobs(limit=5)

if recent:
    for i, job in enumerate(recent, 1):
        st.markdown(f"""
        <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span class="score-badge">{job['match_score']:.3f}</span>
                    <strong style="margin-left: 12px; font-size: 16px; color: var(--text-primary);">{job['company'].upper()}</strong>
                </div>
            </div>
            <div style="margin-top: 8px;">
                <a href="{job['job_url']}" target="_blank" style="font-size: 15px; color: var(--primary);">{job['title']}</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No recent matches yet. Run a scan to get started!")

# Quick actions
st.subheader("⚡ Quick Actions")
st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)
col1, col2 = st.columns(2, gap="large")
with col1:
    if st.button("📊 View All Jobs", use_container_width=True, type="primary"):
        st.switch_page("pages/2_📊_Jobs.py")
with col2:
    if st.button("⚙️ Configuration", use_container_width=True, type="primary"):
        st.switch_page("pages/1_⚙️_Configuration.py")
