"""
Database helper functions for Streamlit dashboard.
Provides cached queries and data processing for UI components.
"""
import sqlite3
import streamlit as st
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd


# ==================== Database Connection ====================

def get_db_connection():
    """Get database connection."""
    return sqlite3.connect('match_pulse.db')


# ==================== Cached Query Functions ====================

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_all_jobs() -> List[Dict]:
    """Get all jobs from database."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM push_history ORDER BY match_score DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@st.cache_data(ttl=60)
def get_jobs_by_status(status: str) -> List[Dict]:
    """Get jobs filtered by status."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM push_history WHERE status = ? ORDER BY match_score DESC', (status,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@st.cache_data(ttl=60)
def get_jobs_by_company(company: str) -> List[Dict]:
    """Get jobs filtered by company."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM push_history WHERE company = ? ORDER BY match_score DESC', (company,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@st.cache_data(ttl=60)
def get_statistics() -> Dict:
    """Get overall statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total jobs
    cursor.execute('SELECT COUNT(*) FROM push_history')
    total_jobs = cursor.fetchone()[0]
    
    # Matched jobs (matched + pushed)
    cursor.execute("SELECT COUNT(*) FROM push_history WHERE status IN ('matched', 'pushed')")
    matched_jobs = cursor.fetchone()[0]
    
    # Pushed jobs
    cursor.execute("SELECT COUNT(*) FROM push_history WHERE status = 'pushed'")
    pushed_jobs = cursor.fetchone()[0]
    
    # Average score (only for matched/pushed)
    cursor.execute("SELECT AVG(match_score) FROM push_history WHERE status IN ('matched', 'pushed')")
    avg_score = cursor.fetchone()[0] or 0
    
    # Top score
    cursor.execute('SELECT MAX(match_score) FROM push_history')
    top_score = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'total_jobs': total_jobs,
        'matched': matched_jobs,
        'pushed': pushed_jobs,
        'avg_score': avg_score,
        'top_score': top_score
    }


@st.cache_data(ttl=60)
def get_score_distribution() -> Dict:
    """Get score distribution for histogram with meaningful ranges."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            CASE 
                WHEN match_score >= 0.90 THEN '0.90+'
                WHEN match_score >= 0.85 THEN '0.85-0.90'
                WHEN match_score >= 0.80 THEN '0.80-0.85'
                WHEN match_score >= 0.75 THEN '0.75-0.80'
                WHEN match_score >= 0.70 THEN '0.70-0.75'
                WHEN match_score >= 0.65 THEN '0.65-0.70'
                WHEN match_score >= 0.60 THEN '0.60-0.65'
                ELSE '<0.60'
            END as score_range,
            COUNT(*) as count
        FROM push_history
        WHERE match_score IS NOT NULL
        GROUP BY score_range
        ORDER BY 
            CASE 
                WHEN score_range = '0.90+' THEN 1
                WHEN score_range = '0.85-0.90' THEN 2
                WHEN score_range = '0.80-0.85' THEN 3
                WHEN score_range = '0.75-0.80' THEN 4
                WHEN score_range = '0.70-0.75' THEN 5
                WHEN score_range = '0.65-0.70' THEN 6
                WHEN score_range = '0.60-0.65' THEN 7
                ELSE 8
            END
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    return {row[0]: row[1] for row in results}


@st.cache_data(ttl=60)
def get_company_distribution() -> Dict:
    """Get company distribution for pie chart."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT company, COUNT(*) as count
        FROM push_history
        GROUP BY company
        ORDER BY count DESC
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    return {row[0]: row[1] for row in results}


@st.cache_data(ttl=60)
def search_jobs(query: str) -> List[Dict]:
    """Search jobs by title or company."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    search_pattern = f'%{query}%'
    cursor.execute('''
        SELECT * FROM push_history 
        WHERE title LIKE ? OR company LIKE ?
        ORDER BY match_score DESC
    ''', (search_pattern, search_pattern))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@st.cache_data(ttl=60)
def get_top_matches(limit: int = 10) -> List[Dict]:
    """Get top N matched jobs."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM push_history 
        WHERE match_score IS NOT NULL
        ORDER BY match_score DESC
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@st.cache_data(ttl=60)
def get_matched_jobs() -> List[Dict]:
    """Get matched and pushed jobs (for display)."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM push_history 
        WHERE status IN ('matched', 'pushed')
        ORDER BY match_score DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@st.cache_data(ttl=60)
def get_recent_jobs(limit: int = 5) -> List[Dict]:
    """Get recently matched/pushed jobs."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM push_history 
        WHERE status IN ('matched', 'pushed')
        ORDER BY match_score DESC
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@st.cache_data(ttl=60)
def get_companies() -> List[str]:
    """Get list of all companies."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT company FROM push_history ORDER BY company')
    companies = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return companies


def filter_jobs(
    jobs: List[Dict],
    company: Optional[str] = None,
    status: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None
) -> List[Dict]:
    """Filter jobs by multiple criteria."""
    filtered = jobs
    
    if company and company != 'All':
        filtered = [j for j in filtered if j['company'] == company]
    
    if status and status != 'All':
        filtered = [j for j in filtered if j['status'] == status]
    
    if min_score is not None:
        filtered = [j for j in filtered if j.get('match_score', 0) >= min_score]
    
    if max_score is not None:
        filtered = [j for j in filtered if j.get('match_score', 0) <= max_score]
    
    return filtered


def jobs_to_dataframe(jobs: List[Dict]) -> pd.DataFrame:
    """Convert jobs list to pandas DataFrame for display."""
    if not jobs:
        return pd.DataFrame()
    
    df = pd.DataFrame(jobs)
    
    # Select and rename columns for display
    display_columns = {
        'company': 'Company',
        'title': 'Title',
        'match_score': 'Score',
        'status': 'Status'
    }
    
    # Keep only existing columns
    available_cols = [col for col in display_columns.keys() if col in df.columns]
    df = df[available_cols]
    df = df.rename(columns=display_columns)
    
    # Format score
    if 'Score' in df.columns:
        df['Score'] = df['Score'].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "N/A")
    
    return df


# ==================== Design System (8pt Grid + Shadcn Style) ====================

DESIGN_TOKENS = {
    # Spacing (8pt grid)
    "spacing": {
        "xs": "4px",
        "sm": "8px",
        "md": "12px",
        "base": "16px",
        "lg": "24px",
        "xl": "32px",
        "2xl": "40px",
        "3xl": "48px"
    },
    
    # Typography
    "typography": {
        "h1": {"size": "32px", "line_height": "40px", "weight": "600"},
        "h2": {"size": "24px", "line_height": "32px", "weight": "600"},
        "h3": {"size": "18px", "line_height": "28px", "weight": "600"},
        "body": {"size": "14px", "line_height": "22px", "weight": "400"},
        "caption": {"size": "12px", "line_height": "18px", "weight": "400"}
    },
    
    # Components
    "components": {
        "card_padding": "24px",
        "card_gap": "16px",
        "button_height": "40px",
        "input_height": "40px",
        "icon_sm": "16px",
        "icon_md": "20px",
        "border_radius": "10px",
        "border_width": "1px",
        "max_width": "1200px",
        "page_padding": "24px"
    }
}

# Light/Dark Theme Colors (Shadcn Style)
THEMES = {
    "light": {
        # Brand
        "primary": "#0F172A",           # Slate 900
        "primary_hover": "#1E293B",     # Slate 800
        
        # Backgrounds
        "bg_page": "#FFFFFF",
        "bg_card": "#FFFFFF",
        "bg_muted": "#F8FAFC",          # Slate 50
        
        # Borders
        "border": "#E2E8F0",            # Slate 200
        "border_hover": "#CBD5E1",      # Slate 300
        
        # Text
        "text_primary": "#0F172A",      # Slate 900
        "text_secondary": "#64748B",    # Slate 500
        "text_muted": "#94A3B8",        # Slate 400
        
        # Status
        "success": "#10B981",           # Green 500
        "warning": "#F59E0B",           # Amber 500
        "danger": "#EF4444",            # Red 500
        
        # Shadows
        "shadow_sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        "shadow_md": "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
    },
    
    "dark": {
        # Brand
        "primary": "#F8FAFC",           # Slate 50
        "primary_hover": "#E2E8F0",     # Slate 200
        
        # Backgrounds
        "bg_page": "#0F172A",           # Slate 900
        "bg_card": "#1E293B",           # Slate 800
        "bg_muted": "#334155",          # Slate 700
        
        # Borders
        "border": "#334155",            # Slate 700
        "border_hover": "#475569",      # Slate 600
        
        # Text
        "text_primary": "#F8FAFC",      # Slate 50
        "text_secondary": "#94A3B8",    # Slate 400
        "text_muted": "#64748B",        # Slate 500
        
        # Status
        "success": "#10B981",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        
        # Shadows
        "shadow_sm": "0 1px 2px 0 rgba(0, 0, 0, 0.3)",
        "shadow_md": "0 4px 6px -1px rgba(0, 0, 0, 0.4)"
    }
}


def get_theme_colors(mode: str = "light") -> dict:
    """Get color palette for light/dark mode."""
    return THEMES.get(mode, THEMES["light"])


def apply_design_system(mode: str = "light"):
    """Apply professional design system with 8pt grid and Shadcn style."""
    colors = get_theme_colors(mode)
    tokens = DESIGN_TOKENS
    
    css = f"""
    <style>
        /* Design System Variables */
        :root {{
            /* Colors */
            --primary: {colors['primary']};
            --primary-hover: {colors['primary_hover']};
            --bg-page: {colors['bg_page']};
            --bg-card: {colors['bg_card']};
            --bg-muted: {colors['bg_muted']};
            --border: {colors['border']};
            --border-hover: {colors['border_hover']};
            --text-primary: {colors['text_primary']};
            --text-secondary: {colors['text_secondary']};
            --text-muted: {colors['text_muted']};
            --success: {colors['success']};
            --warning: {colors['warning']};
            --danger: {colors['danger']};
            --shadow-sm: {colors['shadow_sm']};
            --shadow-md: {colors['shadow_md']};
            
            /* Spacing (8pt grid) */
            --space-xs: {tokens['spacing']['xs']};
            --space-sm: {tokens['spacing']['sm']};
            --space-md: {tokens['spacing']['md']};
            --space-base: {tokens['spacing']['base']};
            --space-lg: {tokens['spacing']['lg']};
            --space-xl: {tokens['spacing']['xl']};
            --space-2xl: {tokens['spacing']['2xl']};
            --space-3xl: {tokens['spacing']['3xl']};
            
            /* Components */
            --card-padding: {tokens['components']['card_padding']};
            --card-gap: {tokens['components']['card_gap']};
            --radius: {tokens['components']['border_radius']};
            --border-width: {tokens['components']['border_width']};
        }}
        
        /* Base Styles */
        .stApp {{
            background-color: var(--bg-page);
            color: var(--text-primary);
            max-width: {tokens['components']['max_width']};
            margin: 0 auto;
            padding: 0 var(--space-lg);
        }}
        
        /* Typography */
        h1 {{
            font-size: {tokens['typography']['h1']['size']};
            line-height: {tokens['typography']['h1']['line_height']};
            font-weight: {tokens['typography']['h1']['weight']};
            color: var(--text-primary);
            margin: 0 0 var(--space-sm) 0;
        }}
        
        h2 {{
            font-size: {tokens['typography']['h2']['size']};
            line-height: {tokens['typography']['h2']['line_height']};
            font-weight: {tokens['typography']['h2']['weight']};
            color: var(--text-primary);
            margin: 0 0 var(--space-xs) 0;
        }}
        
        h3 {{
            font-size: {tokens['typography']['h3']['size']};
            line-height: {tokens['typography']['h3']['line_height']};
            font-weight: {tokens['typography']['h3']['weight']};
            color: var(--text-primary);
            margin: 0 0 var(--space-xs) 0;
        }}
        
        p, .body-text {{
            font-size: {tokens['typography']['body']['size']};
            line-height: {tokens['typography']['body']['line_height']};
            color: var(--text-primary);
            margin: 0;
        }}
        
        .caption {{
            font-size: {tokens['typography']['caption']['size']};
            line-height: {tokens['typography']['caption']['line_height']};
            color: var(--text-secondary);
        }}
        
        /* Cards */
        .card {{
            background: var(--bg-card);
            border: var(--border-width) solid var(--border);
            border-radius: var(--radius);
            padding: var(--card-padding);
            margin-bottom: var(--card-gap);
            box-shadow: var(--shadow-sm);
            transition: all 0.2s ease;
        }}
        
        .card:hover {{
            border-color: var(--border-hover);
            box-shadow: var(--shadow-md);
        }}
        
        /* Streamlit container fixes */
        [data-testid="stVerticalBlock"] {{
            gap: 0 !important;
        }}
        
        [data-testid="column"] > div {{
            overflow: visible !important;
        }}
        
        /* Fix card content overflow */
        .element-container {{
            overflow: visible !important;
        }}
        
        /* Buttons */
        .stButton>button {{
            height: {tokens['components']['button_height']};
            background-color: var(--primary);
            color: var(--bg-page) !important;
            border: none;
            border-radius: var(--radius);
            padding: 0 var(--space-base);
            font-size: {tokens['typography']['body']['size']};
            font-weight: 500;
            transition: all 0.2s ease;
            box-shadow: var(--shadow-sm);
        }}
        
        .stButton>button:hover {{
            background-color: var(--primary-hover);
            box-shadow: var(--shadow-md);
        }}
        
        /* Primary button text color fix */
        .stButton>button[kind="primary"] {{
            background-color: var(--primary);
            color: var(--bg-page) !important;
        }}
        
        .stButton>button[kind="primary"]:hover {{
            background-color: var(--primary-hover);
        }}
        
        /* Button text color for dark theme */
        .stButton>button p {{
            color: var(--bg-page) !important;
        }}
        
        /* Inputs */
        .stTextInput>div>div>input,
        .stSelectbox>div>div>select {{
            height: {tokens['components']['input_height']};
            background: var(--bg-card);
            border: var(--border-width) solid var(--border);
            border-radius: var(--radius);
            color: var(--text-primary);
            font-size: {tokens['typography']['body']['size']};
            padding: 0 var(--space-md);
        }}
        
        /* Links */
        a {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s ease;
        }}
        
        a:hover {{
            color: var(--primary-hover);
        }}
        
        /* Metrics */
        [data-testid="stMetricValue"] {{
            font-size: {tokens['typography']['h1']['size']};
            font-weight: 600;
            color: var(--text-primary);
        }}
        
        [data-testid="stMetricLabel"] {{
            font-size: {tokens['typography']['caption']['size']};
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        /* Empty State */
        .empty-state {{
            text-align: center;
            padding: var(--space-3xl) var(--space-lg);
            background: linear-gradient(135deg, var(--bg-muted) 0%, var(--bg-card) 100%);
            border-radius: var(--radius);
            border: var(--border-width) dashed var(--border);
        }}
        
        .empty-state-icon {{
            width: 64px;
            height: 64px;
            margin: 0 auto var(--space-base);
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-hover) 100%);
            border-radius: var(--radius);
            opacity: 0.1;
        }}
        
        /* Score Badge */
        .score-badge {{
            display: inline-block;
            padding: var(--space-xs) var(--space-md);
            background: var(--success);
            color: white;
            border-radius: calc(var(--radius) * 2);
            font-size: {tokens['typography']['caption']['size']};
            font-weight: 600;
            line-height: 1;
        }}
        
        /* Section Header */
        .section-header {{
            margin-bottom: var(--space-lg);
        }}
        
        .section-title {{
            font-size: {tokens['typography']['h2']['size']};
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: var(--space-xs);
        }}
        
        .section-description {{
            font-size: {tokens['typography']['body']['size']};
            color: var(--text-secondary);
            margin-bottom: 0;
        }}
    </style>
    """
    
    st.markdown(css, unsafe_allow_html=True)


# ==================== Threshold Presets ====================

THRESHOLD_PRESETS = {
    "🔥 High Match (0.80+)": 0.80,
    "⭐ Good Match (0.75+)": 0.75,
    "✓ Decent Match (0.70+)": 0.70,
    "📊 All Matches (0.60+)": 0.60
}


def get_threshold_from_preset(preset_name: str) -> float:
    """Get threshold value from preset name."""
    return THRESHOLD_PRESETS.get(preset_name, 0.70)

