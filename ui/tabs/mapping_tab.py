"""
mapping_tab.py - Mapping tab - EXACT from vnew.py
"""
import streamlit as st
import pandas as pd
import time
from core.models import ColumnRule, ColumnMapping
from features.mapping.engine import MappingEngine

def render_mapping_tab():
    """Render Column Mapping Tab with Left-Right UI"""
    template_cols = st.session_state.template_file.columns.get(
        st.session_state.template_file.selected_sheet, []
    )
    source_cols = st.session_state.source_file.columns.get(
        st.session_state.source_file.selected_sheet, []
    )
    
    if not template_cols or not source_cols:
        st.error("Error No columns available for mapping")
        return
    
    st.markdown('<div class="section-title"> Step 4: Column Mapping</div>', 
                unsafe_allow_html=True)
    
    # Clean Filter Section with Stats on Right
    filter_col1, filter_col2, filter_col3, filter_col4, stats_col = st.columns([1.5, 1.5, 1.5, 1.5, 3])
    
    with filter_col1:
        show_mapped = st.checkbox("Show Mapped", value=True, key="filter_mapped")
        
    with filter_col2:
        show_unmapped = st.checkbox("Show Unmapped", value=True, key="filter_unmapped")
        
    with filter_col3:
        show_mandatory = st.checkbox("Show Mandatory", value=True, key="filter_mandatory")
        
    with filter_col4:
        show_ruled = st.checkbox("Show With Rules", value=True, key="filter_ruled")
    
    with stats_col:
        # Quick Stats on the right side
        st.markdown(f"""
        <div style="display: flex; gap: 0.5rem; align-items: center; justify-content: flex-end; margin-top: 0.5rem;">
            <span style="font-size: 0.85rem; color: #64748b; font-weight: 500;">Quick Stats:</span>
            <span style="background: #10b981; color: white; padding: 0.3rem 0.7rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600;">
                {len([m for m in st.session_state.mappings if m.is_active])}/{len(template_cols)} Mapped
            </span>
            <span style="background: #f59e0b; color: white; padding: 0.3rem 0.7rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600;">
                {sum(1 for col in template_cols if st.session_state.column_rules.get(col, ColumnRule(column_name=col)).is_mandatory)} Mandatory
            </span>
        </div>
        """, unsafe_allow_html=True)

    # Quick Actions
    st.markdown("---")
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    
    with action_col1:
        if st.button(" Auto-Map Columns", use_container_width=True, type="secondary"):
            with st.spinner("Analyzing column similarities..."):
                auto_mappings = MappingEngine.auto_map_columns(source_cols, template_cols)
                
                # Clear existing and add new auto-mappings
                st.session_state.mappings = []
                for mapping in auto_mappings:
                    mapping.source_sheet = st.session_state.source_file.selected_sheet
                    mapping.target_sheet = st.session_state.template_file.selected_sheet
                    st.session_state.mappings.append(mapping)
                
                # Force UI refresh by updating a timestamp
                st.session_state.auto_map_timestamp = time.time()
                
                st.success(f"🤖 Auto-mapped {len(auto_mappings)} columns!")
                # Don't call st.rerun() to avoid page refresh
    
    with action_col2:
        if st.button("Clear All Mappings", use_container_width=True, type="secondary"):
            st.session_state.mappings = []
            st.session_state.auto_map_triggered = False
            st.success(" All mappings cleared!")
            st.rerun()
    
    with action_col3:
        if st.button("Reset Filters", use_container_width=True, type="secondary", key="btn_reset_filters"):
            # Delete the filter keys so they can be recreated with default values
            for key in ['filter_mapped', 'filter_unmapped', 'filter_mandatory', 'filter_ruled']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    with action_col4:
        # Export mapping summary
        if st.button("Export Mapping", use_container_width=True, type="secondary"):
            mapping_data = []
            for target in template_cols:
                rule = st.session_state.column_rules.get(target, ColumnRule(column_name=target))
                source = next((m.source_column for m in st.session_state.mappings if m.target_column == target), "")
                mapping_data.append({
                    "Target Column": target,
                    "Source Column": source,
                    "Mapped": "Yes" if source else "No",
                    "Mandatory": "Yes" if rule.is_mandatory else "No",
                    "Has Rules": "Yes" if rule.get_active_rules() else "No"
                })
            
            df_export = pd.DataFrame(mapping_data)
            csv_data = df_export.to_csv(index=False)
            st.download_button(
                "Download Mapping CSV",
                csv_data,
                "mapping_summary.csv",
                "text/csv",
                use_container_width=True
            )
    
    st.markdown("---")
    
    current_mappings = {}
    for m in st.session_state.mappings:
        current_mappings[m.target_column] = m.source_column
    
    # Create reverse mapping for easy lookup
    reverse_mappings = {}
    for target, source in current_mappings.items():
        if source:
            reverse_mappings[source] = target
    
    # Filter columns based on user selections
    filtered_template_cols = []
    for target in template_cols:
        rule = st.session_state.column_rules.get(target, ColumnRule(column_name=target))
        is_mapped = target in current_mappings and current_mappings[target]
        is_mandatory = rule.is_mandatory
        has_rules = bool(rule.get_active_rules())
        
        # Apply filters
        show_this_column = (
            (show_mapped and is_mapped) or
            (show_unmapped and not is_mapped) or
            (show_mandatory and is_mandatory) or
            (show_ruled and has_rules)
        )
        
        # If no filters are active, show all columns
        if not any([show_mapped, show_unmapped, show_mandatory, show_ruled]):
            show_this_column = True
            
        if show_this_column:
            filtered_template_cols.append(target)

    # Show filtered results count
    if len(filtered_template_cols) != len(template_cols):
        st.info(f"Showing {len(filtered_template_cols)} of {len(template_cols)} columns (filtered)")

    # Display simple arrow-based mapping pairs
    for i, target in enumerate(filtered_template_cols):
        rule = st.session_state.column_rules.get(target, ColumnRule(column_name=target))
        current_source = current_mappings.get(target, "")
        is_mapped = bool(current_source)
        is_mandatory = rule.is_mandatory
        has_rules = bool(rule.get_active_rules())

        # Simple arrow layout: Source → Target
        col1, arrow_col, col2 = st.columns([2, 1, 2])
        
        with col1:
            # Source column selection
            available_sources = ["-- Select Source --"]
            for s in source_cols:
                if s not in reverse_mappings:
                    available_sources.append(s)
                elif reverse_mappings.get(s) == target:
                    available_sources.append(s)
            
            options = available_sources
            current_value = current_source if current_source in options else ""

            try:
                current_index = options.index(current_value) if current_value else 0
            except:
                current_index = 0

            selected = st.selectbox(
                "📊 Source Column",
                options,
                index=current_index,
                key=f"map_{target}_{i}_{st.session_state.get('auto_map_timestamp', 0)}",
                help=f"Choose source column for '{target}'",
                label_visibility="visible"
            )

            # Update mapping if changed - WITH IMMEDIATE RERUN
            selected_clean = selected if selected != "-- Select Source --" else ""
            if selected_clean != current_source:
                # Remove old mapping for this target
                st.session_state.mappings = [m for m in st.session_state.mappings if m.target_column != target]
                # Remove old mapping for this source (if it was mapped to another target)
                if selected_clean:
                    st.session_state.mappings = [m for m in st.session_state.mappings if m.source_column != selected_clean]
                # Add new mapping if selected
                if selected_clean:
                    new_mapping = ColumnMapping(
                        target_column=target,
                        source_column=selected_clean,
                        target_sheet=st.session_state.template_file.selected_sheet,
                        source_sheet=st.session_state.source_file.selected_sheet
                    )
                    st.session_state.mappings.append(new_mapping)
                
                # IMMEDIATE UPDATE - Force rerun to show changes immediately
                st.rerun()

        with arrow_col:
            # Arrow indicating direction
            arrow_color = "#10b981" if is_mapped else "#6b7280"
            st.markdown(f"<div style='text-align: center; color: {arrow_color}; font-size: 1.5rem; margin-top: 25px;'>→</div>", unsafe_allow_html=True)

        with col2:
            # Target column display
            target_bg = "#10b981" if is_mapped else "#6b7280"
            st.markdown(f"""
            <div style="background: rgba({144 if is_mapped else 107}, {163 if is_mapped else 114}, {138 if is_mapped else 128}, 0.1); 
                        border: 2px solid {target_bg}; border-radius: 8px; padding: 12px; margin-top: 8px;">
                <div style="font-weight: 600; color: {target_bg};"> {target}</div>
            """, unsafe_allow_html=True)
            
            # Status badges
            badges = []
            if is_mapped:
                badges.append("Mapped ✅")
            if is_mandatory:
                badges.append("⚠️ Required")
            if has_rules:
                badges.append("📋 Has Rules")

            if badges:
                st.markdown(" ".join(badges))

            # Show validation rules preview
            if has_rules:
                active_rules = rule.get_active_rules()[:2]  # Show first 2 rules
                if active_rules:
                    rules_text = ", ".join(active_rules)
                    if len(rule.get_active_rules()) > 2:
                        rules_text += f" +{len(rule.get_active_rules()) - 2} more"
                    st.caption(f"📋 Rules: {rules_text}")

            # Show mapping confidence
            if selected_clean:
                confidence_score = next((m.confidence_score for m in st.session_state.mappings
                                       if m.target_column == target and m.source_column == selected_clean), 0)
                if confidence_score > 0:
                    confidence_pct = int(confidence_score * 100)
                    st.progress(confidence_score, text=f"{confidence_pct}% confidence")

            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

    # Validation check for mandatory columns
    unmapped_mandatory = []
    for target in template_cols:
        rule = st.session_state.column_rules.get(target, ColumnRule(column_name=target))
        # ... (rest of the code remains the same)
        if rule.is_mandatory:
            if not any(m.target_column == target for m in st.session_state.mappings):
                unmapped_mandatory.append(target)

    if unmapped_mandatory:
        st.warning(f"⚠️ Mandatory columns not mapped: {', '.join(unmapped_mandatory)}")

    # Show current mappings summary
    with st.expander("📋 Current Mappings", expanded=False):
        if st.session_state.mappings:
            mapping_summary = []
            for m in st.session_state.mappings:
                mapping_summary.append({
                    "Source Column": m.source_column,
                    "Target Column": m.target_column,
                    "Status": "Active" if m.is_active else "Inactive"
                })
            st.dataframe(pd.DataFrame(mapping_summary), use_container_width=True, hide_index=True)
        else:
            st.info("No mappings configured yet")

    # Navigation
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back to Rules", use_container_width=True, key='btn_mapping_to_rules'):
            st.session_state.active_tab = 3  # Apply Validation Rules tab (index 3, not 2!)
            st.session_state.tab_change_requested = True
            st.rerun()
    with col2:
        if st.button("✅ Validate & Export", type="primary", use_container_width=True, key='btn_mapping_to_validate'):
            if len(st.session_state.mappings) == 0:
                st.error("Please create at least one mapping")
            else:
                st.session_state.active_tab = 5  # Validate & Export tab (index 5, not 4!)
                st.session_state.tab_change_requested = True
                st.rerun()

# =============================================================================
# TAB 5: VALIDATION & EXPORT
# =============================================================================

