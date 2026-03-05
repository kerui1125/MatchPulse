"""
Jobs Page - All Job History with Filters
"""
import streamlit as st
import sys
import os
import plotly.graph_objects as go
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dashboard.utils.db_helper import (
    get_all_jobs, get_companies, get_company_distribution, 
    apply_design_system, THEMES, get_theme_colors
)

st.set_page_config(page_title="Jobs", page_icon="📊", layout="wide")

# Theme sync (default to dark)
if 'theme_mode' not in st.session_state:
    st.session_state.theme_mode = 'dark'

with st.sidebar:
    theme = st.selectbox("Theme", list(THEMES.keys()), 
                        index=list(THEMES.keys()).index(st.session_state.theme_mode),
                        key="jobs_theme")
    if theme != st.session_state.theme_mode:
        st.session_state.theme_mode = theme
        st.rerun()

apply_design_system(st.session_state.theme_mode)
colors = get_theme_colors(st.session_state.theme_mode)

# Header
st.title("📊 All Jobs")
st.markdown("""
<p class="caption">
Complete history of scraped jobs with match scores and status tracking.
</p>
""", unsafe_allow_html=True)
st.divider()

# ROW 1: Filters + Job Table
st.markdown('<div class="section-header"><h2>🔍 Filters & Jobs</h2></div>', unsafe_allow_html=True)

col_filters, col_table = st.columns([1, 3], gap="large")

with col_filters:
    st.markdown("""
    <style>
    [data-testid="column"]:nth-of-type(1) > div:first-child {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 24px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h3 style="margin-bottom: 24px; color: var(--text-primary);">Filters</h3>', unsafe_allow_html=True)
    
    # Company filter
    companies = ['All'] + get_companies()
    company_filter = st.selectbox("Company", companies)
    
    # Score preset filter
    score_preset = st.selectbox(
        "Minimum Score",
        options=["All Jobs", "0.60+", "0.70+", "0.75+", "0.80+", "0.85+", "0.90+"],
        index=2  # Default 0.70+
    )
    min_score = 0.0 if score_preset == "All Jobs" else float(score_preset.replace("+", ""))
    
    # Status filter - only matched and not_matched
    status_filter = st.selectbox(
        "Status",
        options=['All', 'Matched', 'Not Matched']
    )
    
    # Map display status to DB status
    status_map = {
        'All': None,
        'Matched': ['matched', 'pushed'],
        'Not Matched': 'not_matched'
    }
    
    # Search
    search_query = st.text_input("Search", placeholder="Search by job title...")

with col_table:
    st.markdown("""
    <style>
    [data-testid="column"]:nth-of-type(2) > div:first-child {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 24px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Get and filter jobs
    jobs = get_all_jobs()
    
    # Apply status filter
    db_status = status_map[status_filter]
    if db_status:
        if isinstance(db_status, list):
            filtered = [j for j in jobs if j['status'] in db_status]
        else:
            filtered = [j for j in jobs if j['status'] == db_status]
    else:
        filtered = jobs
    
    # Apply other filters
    if company_filter != 'All':
        filtered = [j for j in filtered if j['company'] == company_filter]
    
    if min_score > 0:
        filtered = [j for j in filtered if j.get('match_score', 0) >= min_score]
    
    # Apply search
    if search_query:
        filtered = [j for j in filtered if search_query.lower() in j['title'].lower()]
    
    st.markdown(f'<h3 style="margin-bottom: 24px; color: var(--text-primary);">💼 {len(filtered)} Jobs</h3>', unsafe_allow_html=True)
    
    if filtered:
        # Convert to DataFrame for table display
        df_data = []
        for job in filtered:
            status_emoji = {
                'pushed': '✅',
                'matched': '🎯',
                'fetched': '📥',
                'not_matched': '❌'
            }.get(job['status'], '❓')
            
            df_data.append({
                'Score': f"{job.get('match_score', 0):.3f}" if job.get('match_score') else 'N/A',
                'Status': f"{status_emoji} {job['status']}",
                'Company': job['company'],
                'Title': job['title'],
                'URL': job['job_url']
            })
        
        df = pd.DataFrame(df_data)
        
        # Display table with clickable title
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Title": st.column_config.LinkColumn(
                    "Title",
                    help="Click to view job posting"
                ),
                "URL": None  # Hide URL column
            },
            height=400
        )
    else:
        # Empty state
        st.markdown("""
        <div style="text-align: center; padding: 48px 24px;">
            <h3 style="color: var(--text-primary);">No jobs found</h3>
            <p class="caption">Adjust your filters or run a scan to fetch new jobs.</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)

# ROW 2: Job Details + Analysis
jobs_with_analysis = [j for j in filtered if j.get('explanation')]

if jobs_with_analysis:
    st.markdown('<div class="section-header"><h2>📝 Job Details & Analysis</h2></div>', unsafe_allow_html=True)
    
    # Initialize session state for job navigation
    if 'current_job_idx' not in st.session_state:
        st.session_state.current_job_idx = 0
    
    # Ensure index is within bounds
    if st.session_state.current_job_idx >= len(jobs_with_analysis):
        st.session_state.current_job_idx = 0
    
    # Navigation controls
    col_nav1, col_nav2, col_nav3 = st.columns([1, 3, 1])
    
    with col_nav1:
        if st.button("⬅️ Previous", use_container_width=True, key="prev_btn", type="secondary"):
            st.session_state.current_job_idx = max(0, st.session_state.current_job_idx - 1)
    
    with col_nav2:
        # Use on_change callback for selectbox
        def update_job_idx():
            st.session_state.current_job_idx = st.session_state.job_selector_value
        
        st.selectbox(
            "Select job to view",
            range(len(jobs_with_analysis)),
            index=st.session_state.current_job_idx,
            format_func=lambda i: f"[{jobs_with_analysis[i].get('match_score', 0):.3f}] {jobs_with_analysis[i]['company']} - {jobs_with_analysis[i]['title'][:50]}...",
            key="job_selector_value",
            on_change=update_job_idx
        )
    
    with col_nav3:
        if st.button("Next ➡️", use_container_width=True, key="next_btn", type="secondary"):
            st.session_state.current_job_idx = min(len(jobs_with_analysis) - 1, st.session_state.current_job_idx + 1)
    
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    
    # Get current job
    job = jobs_with_analysis[st.session_state.current_job_idx]
    
    # Job Details (top) - using container with inline styles
    st.markdown(f"""
    <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 24px; margin-bottom: 24px;">
        <h3 style="margin-bottom: 24px; color: var(--text-primary);">Job Details</h3>
        <div style="margin-top: 16px;">
            <div style="margin-bottom: 16px;">
                <span class="score-badge">{job.get('match_score', 0):.3f}</span>
                <strong style="margin-left: 12px; font-size: 18px; color: var(--text-primary);">{job['company'].upper()}</strong>
            </div>
            <h3 style="margin-bottom: 8px;">
                <a href="{job['job_url']}" target="_blank" style="color: var(--primary);">{job['title']}</a>
            </h3>
            <p class="caption">Status: {job['status']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Analysis (bottom) - using container with inline styles
    # Clean and format the explanation text
    explanation = job["explanation"]
    
    # Split into lines and clean each line
    lines = explanation.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Remove leading/trailing whitespace but preserve structure
        cleaned = line.strip()
        if cleaned:
            # Check if it's a header line
            if cleaned.startswith('✨') or cleaned.startswith('💡'):
                formatted_lines.append(f"\n{cleaned}\n")
            # Check if it's a bullet point
            elif cleaned.startswith('-'):
                formatted_lines.append(f"  {cleaned}")
            else:
                formatted_lines.append(cleaned)
    
    formatted_text = '\n'.join(formatted_lines)
    
    # Display with consistent formatting - font size = line height for tight spacing
    st.markdown(f"""
    <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 24px;">
        <h3 style="margin-bottom: 24px; color: var(--text-primary);">💡 Analysis</h3>
        <div style="color: var(--text-primary); white-space: pre-wrap; font-size: 17px; line-height: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
{formatted_text}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)

# ROW 3: Statistics
st.markdown('<div class="section-header"><h2>📈 Statistics</h2></div>', unsafe_allow_html=True)

st.markdown("""
<style>
div[data-testid="stVerticalBlock"] > div:last-child > div[data-testid="stVerticalBlock"] > div:first-child {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 24px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h3 style="margin-bottom: 24px; color: var(--text-primary);">Company Distribution</h3>', unsafe_allow_html=True)
st.markdown('<p class="caption" style="margin-bottom: 32px;">Jobs by company</p>', unsafe_allow_html=True)

company_dist = get_company_distribution()
if company_dist:
    # Predefined colors for known companies (brand colors)
    company_colors = {
        'nvidia': '#76B900',      # NVIDIA green
        'google': '#4285F4',      # Google blue
        'amazon': '#FF9900',      # Amazon orange
        'microsoft': '#00A4EF',   # Microsoft blue
        'salesforce': '#00A1E0',  # Salesforce blue
        'oracle': '#F80000',      # Oracle red
        'expedia': '#FFCB05'      # Expedia yellow
    }
    
    # Fallback color palette for new companies
    fallback_colors = [
        '#9333EA',  # Purple
        '#EC4899',  # Pink
        '#14B8A6',  # Teal
        '#F59E0B',  # Amber
        '#8B5CF6',  # Violet
        '#06B6D4',  # Cyan
        '#84CC16',  # Lime
        '#F97316',  # Orange
        '#A855F7',  # Purple
        '#22D3EE'   # Sky
    ]
    
    # Generate colors: use brand color if available, otherwise use fallback
    pie_colors = []
    fallback_idx = 0
    for company in company_dist.keys():
        if company.lower() in company_colors:
            pie_colors.append(company_colors[company.lower()])
        else:
            # Use fallback colors for unknown companies
            pie_colors.append(fallback_colors[fallback_idx % len(fallback_colors)])
            fallback_idx += 1
    
    fig = go.Figure(data=[
        go.Pie(
            labels=list(company_dist.keys()),
            values=list(company_dist.values()),
            marker=dict(colors=pie_colors),
            textfont=dict(color='white', size=12)
        )
    ])
    fig.update_layout(
        height=300,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=colors['text_primary'], size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(size=11)
        )
    )
    st.plotly_chart(fig, use_container_width=True)
