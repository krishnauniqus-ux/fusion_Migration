"""
Progress indicator component - EXACT from vnew.py
"""
import streamlit as st

def render_progress_steps():
    """Render workflow progress indicator with tick marks for completed steps"""
    steps = [
        ("1", "Upload Template", "template_file", ""),
        ("2", "Upload Source", "source_file", ""),
        ("3", "Configure Rules", "column_rules", ""),
        ("4", "Map Columns", "mappings", ""),
        ("5", "Validate & Export", "validation_results", "")
    ]
    
    # Determine current step
    current_step = st.session_state.active_tab
    
    # Add some spacing
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Create columns for each step
    cols = st.columns(len(steps))
    
    for i, (num, label, state_key, icon) in enumerate(steps):
        with cols[i]:
            # Check if step is completed (has required data)
            is_completed = False
            if state_key == "template_file" and st.session_state.template_file.selected_sheet:
                is_completed = True
            elif state_key == "source_file" and st.session_state.source_file.selected_sheet:
                is_completed = True
            elif state_key == "column_rules" and st.session_state.column_rules:
                # Check if any rules are actually configured (not just default empty rules)
                has_configured_rules = any(
                    rule.get_active_rules() 
                    for rule in st.session_state.column_rules.values()
                )
                if has_configured_rules:
                    is_completed = True
            elif state_key == "mappings" and st.session_state.mappings:
                is_completed = True
            elif state_key == "validation_results" and st.session_state.validation_results:
                is_completed = True
            
            if i < current_step or is_completed:
                # Completed step - show tick mark
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                                color: white; display: flex; align-items: center; justify-content: center; margin: 0 auto; 
                                font-weight: 700; font-size: 1.2rem; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
                                border: 3px solid rgba(255,255,255,0.2);">
                        &#10004;
                    </div>
                    <div style="font-size: 0.85rem; color: #10b981; font-weight: 600; margin-top: 0.75rem; line-height: 1.2;">
                        {label}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif i == current_step:
                # Active step
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="width: 48px; height: 48px; border-radius: 50%; 
                                background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%); color: white; 
                                display: flex; align-items: center; justify-content: center; margin: 0 auto; 
                                font-weight: 700; font-size: 1.2rem; box-shadow: 0 0 25px rgba(59, 130, 246, 0.5); 
                                border: 3px solid rgba(255,255,255,0.3); animation: pulse 2s infinite;">
                        {num}
                    </div>
                    <div style="font-size: 0.85rem; color: #3b82f6; font-weight: 600; margin-top: 0.75rem; line-height: 1.2;">
                        {label}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Pending step
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="width: 48px; height: 48px; border-radius: 50%; 
                                background: rgba(255,255,255,0.08); color: #64748b; 
                                border: 2px solid rgba(255,255,255,0.15);
                                display: flex; align-items: center; justify-content: center; margin: 0 auto; 
                                font-weight: 600; font-size: 1.1rem;">
                        {num}
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; font-weight: 500; margin-top: 0.75rem; line-height: 1.2;">
                        {label}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Add separator with enhanced styling
    st.markdown("""
    <hr style='margin: 2.5rem 0; border: none; height: 2px; background: linear-gradient(90deg, 
                rgba(59, 130, 246, 0.3) 0%, rgba(6, 182, 212, 0.3) 50%, rgba(16, 185, 129, 0.3) 100%); 
                border-radius: 1px;'>
    """, unsafe_allow_html=True)
