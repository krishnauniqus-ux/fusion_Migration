"""
Mapper Enterprise - Main Application Entry Point
Modular architecture for easy maintenance and scalability
"""
import streamlit as st
from config.settings import configure_page, load_custom_css
from core.session import init_session_state, auto_save_state
from ui.header import render_header
from ui.sidebar import render_sidebar
from ui.progress import render_progress_steps
from ui.tabs.template_tab import render_template_tab
from ui.tabs.source_tab import render_source_tab
from ui.tabs.rules_tab import render_rules_tab
from ui.tabs.mapping_tab import render_mapping_tab
from ui.tabs.validation_tab import render_validation_tab
from features.profiling import render_data_profiling

# Configure page
configure_page()
load_custom_css()

def main():
    """Main application entry point"""
    # Initialize session state
    init_session_state()
    
    # Render UI components
    render_header()
    render_sidebar()
    render_progress_steps()
    
    # Main tabs
    tabs = st.tabs([
        "Fusion Template Upload",
        "Upload Source Records",
        "Data Profile",
        "Apply Validation Rules",
        "Mapping B/W Template  & Source",
        "Validate & Export"
    ])
    
    with tabs[0]:
        render_template_tab()
    
    with tabs[1]:
        render_source_tab()
    
    with tabs[2]:
        render_data_profiling()
    
    with tabs[3]:
        render_rules_tab()
    
    with tabs[4]:
        render_mapping_tab()
    
    with tabs[5]:
        render_validation_tab()
    
    # Auto-navigate to active tab ONLY when explicitly changed by button
    # Check if active_tab was changed in this session (not on initial load)
    if 'tab_change_requested' in st.session_state and st.session_state.tab_change_requested:
        js = f"""
        <script>
            setTimeout(function() {{
                var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
                if (tabs.length > {st.session_state.active_tab}) {{
                    tabs[{st.session_state.active_tab}].click();
                }}
            }}, 100);
        </script>
        """
        st.components.v1.html(js, height=0)
        # Reset the flag after navigation
        st.session_state.tab_change_requested = False
    
    # Auto-save state after every rerun
    auto_save_state()

if __name__ == "__main__":
    main()
