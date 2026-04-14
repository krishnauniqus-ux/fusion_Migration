"""
Application settings and configuration
"""
import streamlit as st
import time

# Auto-save file path
AUTO_SAVE_FILE = ".mapper_autosave.pkl"

# --- Large dataset tuning (memory / UI responsiveness only) ---
# Does not change validation rules, duplicate logic, or per-cell outcomes.
VALIDATION_GC_EVERY_N_ROWS = 50_000
# Progress updates: avoid hammering Streamlit on multi-million-row runs
VALIDATION_PROGRESS_MIN_ROWS = 250
VALIDATION_PROGRESS_MAX_FRACTION = 400  # update about every (total_rows / this) rows, lower bound above
ERROR_UI_MAX_ROWS = 15_000  # full error list stays in session; table view is capped
CSV_CHUNK_LOAD_MIN_BYTES = 40 * 1024 * 1024  # same pandas result as one-shot read
CSV_READ_CHUNKSIZE = 200_000
PROFILER_STRING_STATS_CHUNK = 100_000
PROFILE_DUP_DISPLAY_MAX_KEYS = 2_500  # UI string length cap for duplicate-value lists
QUALITY_WHITESPACE_CHUNK = 100_000

def configure_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="Mapper Enterprise | Data Migration Platform",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def load_custom_css():
    """Load custom CSS styling - EXACT from vnew.py"""
    st.markdown("""
    <style>
        /* Button styling - Blue background with white text */
        .stButton>button {
            background-color: #0000D1 !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton>button:hover {
            background-color: #0000a8 !important;
            color: white !important;
        }
        
        .stButton>button:active {
            background-color: #000080 !important;
        }
        
        /* Download button styling */
        .stDownloadButton>button {
            background-color: #0000D1 !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
        }
        
        .stDownloadButton>button:hover {
            background-color: #0000a8 !important;
            color: white !important;
        }
        
        /* Tab styling - Active tab green with cool effects */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 12px !important;
            padding: 12px 24px !important;
            transition: all 0.3s ease !important;
            border: 2px solid transparent !important;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
            color: white !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4) !important;
            border: 2px solid rgba(255, 255, 255, 0.3) !important;
            transform: translateY(-2px) !important;
            font-weight: 600 !important;
        }
        
        .stTabs [aria-selected="false"] {
            background-color: rgba(255, 255, 255, 0.05) !important;
            color: #94a3b8 !important;
            border-radius: 12px !important;
        }
        
        .stTabs [aria-selected="false"]:hover {
            background-color: rgba(16, 185, 129, 0.1) !important;
            color: #10b981 !important;
            border: 2px solid rgba(16, 185, 129, 0.3) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Loading spinner
    with st.spinner('🔄 Loading application...'):
        time.sleep(0.5)  # Brief pause to show spinner
