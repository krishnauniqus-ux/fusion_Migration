"""
Sidebar component - EXACT from vnew.py
"""
import streamlit as st
import os
from config.settings import AUTO_SAVE_FILE
from core.session import init_session_state

def render_sidebar():
    """Render sidebar controls"""
    with st.sidebar:
        st.markdown("##  Control Panel")
        
        # Quick Stats
        st.markdown("###  Quick Stats")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Template Sheets",
                len(st.session_state.template_file.sheets),
                delta=None
            )
        with col2:
            st.metric(
                "Source Sheets",
                len(st.session_state.source_file.sheets),
                delta=None
            )
        
        st.metric("Active Mappings", len(st.session_state.mappings))
        
        # Reset
        st.markdown("---")
        if st.button(" Reset Application", type="secondary", use_container_width=True):
            # Delete auto-save file
            if os.path.exists(AUTO_SAVE_FILE):
                try:
                    os.remove(AUTO_SAVE_FILE)
                except:
                    pass
            
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style='font-size: 0.75rem; color: rgba(255,255,255,0.4); text-align: center;'>
            <strong>Mapper Enterprise v2.0</strong><br>
            Built with Streamlit<br>
            &copy; 2024 Enterprise Data Solutions
        </div>
        """, unsafe_allow_html=True)
