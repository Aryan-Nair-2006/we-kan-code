import streamlit as st

def inject_custom_css():
    st.markdown("""
    <style>
        /* 1. GOOGLE FONTS & DESIGN TOKENS */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

        :root {
            /* Palette: Enterprise Dark */
            --tkf-bg: #0B1120;
            --tkf-surface-1: #111827;
            --tkf-surface-2: #1E293B;
            --tkf-card: #172033;
            --tkf-border: #334155;
            
            /* Text colors */
            --tkf-text-primary: #F8FAFC;
            --tkf-text-secondary: #CBD5E1;
            --tkf-text-muted: #94A3B8;
            
            /* Accents */
            --tkf-orange: #F97316;
            --tkf-orange-dark: #EA580C;
            --tkf-orange-glow: rgba(249, 115, 22, 0.15);
            
            --tkf-cyan: #38BDF8;
            --tkf-cyan-glow: rgba(56, 189, 248, 0.15);
            
            /* Statuses */
            --tkf-success: #22C55E;
            --tkf-success-bg: rgba(34, 197, 94, 0.12);
            --tkf-warning: #F59E0B;
            --tkf-warning-bg: rgba(245, 158, 11, 0.12);
            --tkf-error: #EF4444;
            --tkf-error-bg: rgba(239, 68, 68, 0.12);
            --tkf-info: #38BDF8;

            /* Utilities */
            --tkf-radius: 12px;
            --tkf-radius-sm: 8px;
            --tkf-radius-lg: 16px;
            --tkf-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
            --tkf-font: 'Outfit', 'Inter', sans-serif;
        }

        /* 2. BASE DOCUMENT RESET */
        html, body, [class*="css"] {
            font-family: var(--tkf-font);
            background-color: var(--tkf-bg) !important;
            color: var(--tkf-text-primary) !important;
        }

        /* Hide Streamlit default headers & footers */
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        .stDeployButton { display: none !important; }

        /* Container padding */
        .block-container {
            padding-top: 1.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 1280px !important;
            margin: 0 auto;
        }

        /* 3. SIDEBAR NAVIGATION STYLING */
        [data-testid="stSidebar"] {
            background-color: var(--tkf-surface-1) !important;
            border-right: 1px solid var(--tkf-border) !important;
        }
        [data-testid="stSidebar"] * {
            color: var(--tkf-text-primary) !important;
        }
        [data-testid="stSidebar"] .stButton button {
            width: 100% !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            color: var(--tkf-text-secondary) !important;
            justify-content: flex-start !important;
            text-align: left !important;
            padding: 10px 16px !important;
            border-radius: var(--tkf-radius-sm) !important;
            font-weight: 500 !important;
            font-size: 0.95rem !important;
            margin-bottom: 4px !important;
        }
        [data-testid="stSidebar"] .stButton button:hover {
            background: var(--tkf-surface-2) !important;
            color: var(--tkf-text-primary) !important;
            border-color: var(--tkf-border) !important;
        }
        [data-testid="stSidebar"] .stButton button[data-active="true"] {
            background: var(--tkf-orange-glow) !important;
            color: var(--tkf-orange) !important;
            border-color: var(--tkf-orange) !important;
            font-weight: 600 !important;
        }

        /* 4. TYPOGRAPHY HIERARCHY */
        .tkf-eyebrow {
            color: var(--tkf-orange);
            font-weight: 700;
            font-size: 0.8rem;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }
        .tkf-hero-title {
            font-size: 2.2rem;
            font-weight: 700;
            color: var(--tkf-text-primary);
            line-height: 1.2;
            margin-bottom: 0.5rem;
            letter-spacing: -0.5px;
        }
        .tkf-hero-subtitle {
            font-size: 1.05rem;
            color: var(--tkf-text-secondary);
            max-width: 700px;
            line-height: 1.5;
            margin-bottom: 1.75rem;
        }
        .tkf-section-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--tkf-text-primary);
            margin-bottom: 0.85rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* 5. CARDS & CONTAINERS */
        .tkf-card {
            background: var(--tkf-card);
            border: 1px solid var(--tkf-border);
            border-radius: var(--tkf-radius);
            padding: 1.25rem 1.5rem;
            box-shadow: var(--tkf-shadow);
            margin-bottom: 1rem;
        }
        .tkf-card-interactive {
            background: var(--tkf-card);
            border: 1px solid var(--tkf-border);
            border-radius: var(--tkf-radius);
            padding: 1.25rem 1.5rem;
            box-shadow: var(--tkf-shadow);
            transition: all 0.2s ease-in-out;
            margin-bottom: 1rem;
        }
        .tkf-card-interactive:hover {
            border-color: var(--tkf-cyan);
            transform: translateY(-2px);
        }

        /* METRIC CARDS */
        .metric-card {
            background: var(--tkf-card);
            border: 1px solid var(--tkf-border);
            border-radius: var(--tkf-radius);
            padding: 1.15rem 1.25rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            box-shadow: var(--tkf-shadow);
        }
        .metric-icon {
            font-size: 1.4rem;
            background: var(--tkf-surface-2);
            width: 44px;
            height: 44px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--tkf-cyan);
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--tkf-text-primary);
            line-height: 1;
            margin-bottom: 4px;
        }
        .metric-label {
            font-size: 0.82rem;
            color: var(--tkf-text-muted);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* 6. STATUS BADGES */
        .badge {
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            display: inline-block;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }
        .badge.ready {
            background: var(--tkf-success-bg);
            color: var(--tkf-success);
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .badge.processing, .badge.uploaded {
            background: var(--tkf-warning-bg);
            color: var(--tkf-warning);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }
        .badge.failed {
            background: var(--tkf-error-bg);
            color: var(--tkf-error);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .badge.archived, .badge.pending_review {
            background: rgba(148, 163, 184, 0.12);
            color: var(--tkf-text-secondary);
            border: 1px solid var(--tkf-border);
        }

        /* 7. EVIDENCE & SOURCE CARDS */
        .source-card {
            background: var(--tkf-card);
            border: 1px solid var(--tkf-border);
            border-left: 4px solid var(--tkf-orange);
            border-radius: var(--tkf-radius-sm);
            padding: 1rem 1.25rem;
            margin-bottom: 0.85rem;
        }
        .source-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        .source-badge {
            background: var(--tkf-orange-glow);
            color: var(--tkf-orange);
            border: 1px solid rgba(249, 115, 22, 0.3);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .trust-indicator {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 16px;
            background: rgba(34, 197, 94, 0.08);
            border: 1px solid rgba(34, 197, 94, 0.25);
            border-radius: var(--tkf-radius-sm);
            margin-bottom: 1.25rem;
        }
        .trust-indicator .trust-icon {
            color: var(--tkf-success);
            font-size: 1.2rem;
            font-weight: bold;
        }
        .trust-text {
            font-weight: 600;
            color: var(--tkf-text-primary);
            font-size: 0.9rem;
        }

        /* 8. OVERRIDES FOR STREAMLIT INPUTS, BUTTONS, AND SELECTBOXES */
        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
            background-color: var(--tkf-surface-2) !important;
            color: var(--tkf-text-primary) !important;
            border: 1px solid var(--tkf-border) !important;
            border-radius: var(--tkf-radius-sm) !important;
        }
        .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within, .stTextArea textarea:focus {
            border-color: var(--tkf-orange) !important;
            box-shadow: 0 0 0 1px var(--tkf-orange) !important;
        }
        .stTextInput label, .stSelectbox label, .stTextArea label, .stFileUploader label {
            color: var(--tkf-text-secondary) !important;
            font-weight: 500 !important;
            font-size: 0.9rem !important;
        }

        /* Streamlit Buttons */
        .stButton button {
            border-radius: var(--tkf-radius-sm) !important;
            font-weight: 600 !important;
            font-size: 0.92rem !important;
            padding: 8px 18px !important;
            transition: all 0.2s ease !important;
        }
        .stButton button[kind="primary"] {
            background-color: var(--tkf-orange) !important;
            color: #FFFFFF !important;
            border: none !important;
            box-shadow: 0 2px 10px rgba(249, 115, 22, 0.3) !important;
        }
        .stButton button[kind="primary"]:hover {
            background-color: var(--tkf-orange-dark) !important;
            transform: translateY(-1px);
        }
        .stButton button[kind="secondary"] {
            background-color: var(--tkf-surface-2) !important;
            border: 1px solid var(--tkf-border) !important;
            color: var(--tkf-text-primary) !important;
        }
        .stButton button[kind="secondary"]:hover {
            border-color: var(--tkf-cyan) !important;
            color: var(--tkf-cyan) !important;
            background: var(--tkf-card) !important;
        }

        /* Expanders & Tabs */
        .stExpander {
            background-color: var(--tkf-card) !important;
            border: 1px solid var(--tkf-border) !important;
            border-radius: var(--tkf-radius-sm) !important;
            margin-bottom: 0.75rem !important;
        }
        .stExpander header {
            color: var(--tkf-text-primary) !important;
        }

        /* Dataframes & Tables */
        [data-testid="stTable"], [data-testid="stDataFrame"] {
            background-color: var(--tkf-card) !important;
            border-radius: var(--tkf-radius-sm) !important;
            border: 1px solid var(--tkf-border) !important;
        }

        /* Alert Boxes */
        .stAlert {
            background-color: var(--tkf-card) !important;
            border-radius: var(--tkf-radius-sm) !important;
            border: 1px solid var(--tkf-border) !important;
            color: var(--tkf-text-primary) !important;
        }
    </style>
    """, unsafe_allow_html=True)
