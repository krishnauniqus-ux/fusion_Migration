"""
rules_tab.py - Rules tab - EXACT from vnew.py
"""
import streamlit as st
import pandas as pd
from core.models import ColumnRule

def render_rules_tab():
    """Render Validation Rules Configuration Tab"""
    st.markdown('<div class="section-title"> Step 3: Configure Validation Rules</div>', 
                unsafe_allow_html=True)
    
    if not st.session_state.template_file.selected_sheet:
        st.warning(" Please upload Template file first")
        return
    
    template_cols = st.session_state.template_file.columns.get(
        st.session_state.template_file.selected_sheet, []
    )
    
    if not template_cols:
        st.error(" No columns found in template")
        return
    
    st.markdown("""
    <div class="alert alert-info">
        Define validation rules for each <strong>Template Column</strong>. 
        These rules will be applied when mapping data from the source.
    </div>
    """, unsafe_allow_html=True)
    
    # Summary stats
    total_rules = sum(
        1 for rule in st.session_state.column_rules.values() 
        if rule.get_active_rules()
    )
    st.metric("Active Rules", f"{total_rules}/{len(template_cols)}")
    
    # Column selection for rule editing
    selected_col = st.selectbox(
        "Select Column to Configure",
        template_cols,
        key='rule_column_select'
    )
    
    if selected_col:
        rule = st.session_state.column_rules.get(
            selected_col, 
            ColumnRule(column_name=selected_col)
        )
        
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        
        # Three column layout for better organization
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("** Basic Validation**")
            
            rule.is_mandatory = st.toggle(
                "Mandatory Field",
                value=rule.is_mandatory,
                help="Column must be mapped from source and cannot be empty",
                key=f"mand_{selected_col}"
            )
            
            rule.no_special_chars = st.toggle(
                "No Special Characters",
                value=rule.no_special_chars,
                help="Removes special chars, keeps alphanumeric and spaces",
                key=f"spec_{selected_col}"
            )
            
            rule.fix_accented_chars = st.toggle(
                "Fix Accented Characters",
                value=rule.fix_accented_chars,
                help="Converts accented/unicode chars to ASCII (e.g. GARCÍA → GARCIA, MÜLLER → MULLER)",
                key=f"accent_{selected_col}"
            )
            
            rule.only_characters = st.toggle(
                "Characters Only (No Numbers)",
                value=rule.only_characters,
                help="No numeric characters allowed",
                key=f"char_{selected_col}"
            )
            
            rule.only_numbers = st.toggle(
                "Numbers Only",
                value=rule.only_numbers,
                help="Must be numeric value (int or float)",
                key=f"num_{selected_col}"
            )
            
            rule.email_format = st.toggle(
                "Email Format",
                value=rule.email_format,
                help="Must be valid email address",
                key=f"email_{selected_col}"
            )
            
            # New format validations
            rule.phone_format = st.toggle(
                "Phone Format",
                value=rule.phone_format,
                help="UAE (+971) and India (+91) formats only",
                key=f"phone_{selected_col}"
            )
            
            rule.url_format = st.toggle(
                "URL Format",
                value=rule.url_format,
                help="Must be valid URL format",
                key=f"url_{selected_col}"
            )
            
            rule.postal_code = st.toggle(
                "Postal Code (US ZIP)",
                value=rule.postal_code,
                help="Must be valid US ZIP code format",
                key=f"postal_{selected_col}"
            )
            
            rule.ssn_format = st.toggle(
                "SSN Format",
                value=rule.ssn_format,
                help="Must be valid SSN format (123-45-6789)",
                key=f"ssn_{selected_col}"
            )

            # Regex and transforms
            st.markdown("**Patterns & Transforms**")
            
            # Azure OpenAI Chat Box
            with st.expander("🤖 AI Regex Generator (Azure OpenAI)", expanded=False):
                st.markdown("""
                <div style="background: rgba(59, 130, 246, 0.15); padding: 1rem; border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.3);">
                    <p style="margin: 0; color: #cbd5e1; font-size: 0.9rem;">
                        Ask AI to generate regex patterns for your data transformations.
                        <br><small style="color: #94a3b8;">Example: "Create a regex for 10-digit phone numbers with country code"</small>
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Chat input
                user_prompt = st.text_input(
                    "Describe the pattern you need:",
                    placeholder="e.g., Extract email domains from text or validate 10-digit phone numbers",
                    key=f"ai_prompt_{selected_col}"
                )
                
                # Generate button
                if st.button("Generate Regex Pattern", key=f"ai_gen_{selected_col}", use_container_width=True):
                    if user_prompt.strip():
                        with st.spinner("Generating regex pattern with Azure OpenAI..."):
                            try:
                                from openai import AzureOpenAI
                                
                                # Check if secrets exist
                                if not hasattr(st.secrets, 'endpoint') or not st.secrets.endpoint:
                                    st.error("Azure OpenAI credentials not configured in .streamlit/secrets.toml")
                                    st.info("Please add: endpoint, api_key, deployment_name, api_version")
                                    st.stop()
                                
                                client = AzureOpenAI(
                                    azure_endpoint=st.secrets.endpoint,
                                    api_key=st.secrets.api_key,
                                    api_version=st.secrets.api_version
                                )
                                
                                response = client.chat.completions.create(
                                    model=st.secrets.deployment_name,
                                    messages=[
                                        {
                                            "role": "system",
                                            "content": """You are an expert regex pattern generator. 
                                            Return ONLY the regex pattern in a code block format.
                                            If a transform is needed, return the transform regex.
                                            Keep patterns simple and practical for data validation."""
                                        },
                                        {
                                            "role": "user",
                                            "content": user_prompt
                                        }
                                    ],
                                    max_tokens=1000,
                                    temperature=0.1
                                )
                                
                                generated_pattern = response.choices[0].message.content.strip()
                                # Extract pattern from code block if present
                                if generated_pattern.startswith('```'):
                                    generated_pattern = generated_pattern.split('```')[1]
                                    if generated_pattern.startswith('regex') or generated_pattern.startswith('python'):
                                        generated_pattern = generated_pattern.split('\n', 1)[1]
                                    generated_pattern = generated_pattern.strip('`').strip()
                                
                                st.success("Pattern generated successfully!")
                                st.code(generated_pattern, language="regex")
                                
                                # Auto-fill option
                                if st.button("Use This Pattern", key=f"use_pattern_{selected_col}"):
                                    rule.regex_pattern = generated_pattern
                                    st.rerun()
                                    
                            except Exception as e:
                                st.error(f"Error generating pattern: {str(e)}")
                                st.info("Please check your Azure OpenAI credentials in .streamlit/secrets.toml")
                    else:
                        st.warning("Please describe the pattern you need first")
            
            rule.regex_pattern = st.text_input(
                "Regex Pattern",
                value=rule.regex_pattern or "",
                help="Single regex for validation, extraction, transformation, and more. AI-powered generation available.",
                key=f"regex_{selected_col}"
            )
            if rule.regex_pattern == "":
                rule.regex_pattern = None
            
            
        with col2:
            st.markdown("** Advanced Formats**")
            
            rule.credit_card = st.toggle(
                "Credit Card",
                value=rule.credit_card,
                help="Validates credit card number with Luhn algorithm",
                key=f"cc_{selected_col}"
            )
            
            rule.ip_address = st.toggle(
                "IP Address",
                value=rule.ip_address,
                help="Must be valid IPv4 address format",
                key=f"ip_{selected_col}"
            )
            
            rule.currency_format = st.toggle(
                "Currency Format",
                value=rule.currency_format,
                help="Must be valid currency format ($1,234.56)",
                key=f"currency_{selected_col}"
            )
            
            rule.percentage = st.toggle(
                "Percentage",
                value=rule.percentage,
                help="Must be valid percentage format",
                key=f"percent_{selected_col}"
            )
            
            rule.boolean_format = st.toggle(
                "Boolean Format",
                value=rule.boolean_format,
                help="Must be true/false, yes/no, 1/0, y/n, t/f",
                key=f"bool_{selected_col}"
            )
            
            # Case validation
            st.markdown("**Case Validation**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                rule.uppercase_only = st.toggle(
                    "UPPERCASE",
                    value=rule.uppercase_only,
                    help="All letters are capitalized (e.g., THE CAT SAT)",
                    key=f"upper_{selected_col}"
                )
                
                rule.lowercase_only = st.toggle(
                    "lowercase",
                    value=rule.lowercase_only,
                    help="All letters are lowercase (e.g., the cat sat)",
                    key=f"lower_{selected_col}"
                )
                
                rule.title_case = st.toggle(
                    "Title Case",
                    value=rule.title_case,
                    help="Capitalize first/last words and major words (e.g., Lord of the Flies)",
                    key=f"title_{selected_col}"
                )
                
                rule.sentence_case = st.toggle(
                    "Sentence case",
                    value=rule.sentence_case,
                    help="Capitalize only the first word (e.g., The cat sat)",
                    key=f"sentence_{selected_col}"
                )
            
            with col2:
                rule.camel_case = st.toggle(
                    "CamelCase",
                    value=rule.camel_case,
                    help="No spaces, capitalize first letter of each word (e.g., CamelCase)",
                    key=f"camel_{selected_col}"
                )
                
                rule.lower_camel_case = st.toggle(
                    "lowerCamelCase",
                    value=rule.lower_camel_case,
                    help="First word lowercase, subsequent words capitalized (e.g., iPhone)",
                    key=f"lower_camel_{selected_col}"
                )
                
                rule.snake_case = st.toggle(
                    "snake_case",
                    value=rule.snake_case,
                    help="Lowercase with underscores (e.g., snake_case_example)",
                    key=f"snake_{selected_col}"
                )
                
                rule.title_case_strict = st.toggle(
                    "Title Case (Strict)",
                    value=rule.title_case_strict,
                    help="Similar to Title Case but stricter on keeping short words lowercase",
                    key=f"title_strict_{selected_col}"
                )
            
             # Special validations
            st.markdown("**Special Validations**")
            
            rule.not_null = st.toggle(
                "Check Null",
                value=rule.not_null,
                help="Rejects NULL, null, N/A, NA, #N/A, -, -- values",
                key=f"notnull_{selected_col}"
            )
            
            rule.unique_value = st.toggle(
                "Unique Values",
                value=rule.unique_value,
                help="All values in this column must be unique",
                key=f"unique_{selected_col}"
            )
            
            rule.check_duplicates = st.toggle(
                "Check Duplicates",
                value=rule.check_duplicates,
                help="Flag duplicate values in validation errors (shows only duplicates)",
                key=f"check_dup_{selected_col}"
            )
            
            rule.similar_match = st.toggle(
                "Similar Match (>=85%)",
                value=rule.similar_match,
                help="Flag near-duplicate text values using RapidFuzz similarity >= 85%",
                key=f"similar_match_{selected_col}"
            )
            
            rule.checksum_validation = st.toggle(
                "Checksum Validation",
                value=rule.checksum_validation,
                help="Mod 10 checksum validation for numeric strings",
                key=f"checksum_{selected_col}"
            )
           
            # String matching
            st.markdown("**String Matching**")
            rule.starts_with = st.text_input(
                "Starts With",
                value=rule.starts_with or "",
                help="Must start with this text",
                key=f"starts_{selected_col}"
            )
            if rule.starts_with == "":
                rule.starts_with = None
            
            rule.ends_with = st.text_input(
                "Ends With",
                value=rule.ends_with or "",
                help="Must end with this text",
                key=f"ends_{selected_col}"
            )
            if rule.ends_with == "":
                rule.ends_with = None
            
            rule.contains = st.text_input(
                "Contains",
                value=rule.contains or "",
                help="Must contain this text",
                key=f"contains_{selected_col}"
            )
            if rule.contains == "":
                rule.contains = None
            
            
        with col3:
            st.markdown("** Constraints & Ranges**")
            
            # Length constraints
            length_cols = st.columns(2)
            with length_cols[0]:
                rule.min_length = st.number_input(
                    "Min Length",
                    min_value=0,
                    max_value=1000,
                    value=rule.min_length or 0,
                    key=f"minlen_{selected_col}"
                )
                if rule.min_length == 0:
                    rule.min_length = None
            
            with length_cols[1]:
                rule.max_length = st.number_input(
                    "Max Length",
                    min_value=0,
                    max_value=1000,
                    value=rule.max_length or 0,
                    key=f"maxlen_{selected_col}"
                )
                if rule.max_length == 0:
                    rule.max_length = None
            
            # Numeric range
            st.markdown("**Numeric Range**")
            range_cols = st.columns(2)
            with range_cols[0]:
                rule.numeric_range_min = st.number_input(
                    "Min Value",
                    value=rule.numeric_range_min,
                    key=f"range_min_{selected_col}",
                    help="Minimum numeric value"
                )
            
            with range_cols[1]:
                rule.numeric_range_max = st.number_input(
                    "Max Value", 
                    value=rule.numeric_range_max,
                    key=f"range_max_{selected_col}",
                    help="Maximum numeric value"
                )
            
            # Date and age validation
            st.markdown("**Date & Age**")
            
            # Predefined date formats
            date_format_options = {
                "None": None,
                "YYYY-MM-DD": "%Y-%m-%d",
                "YYYY-MM-DD HH:MM:SS": "%Y-%m-%d %H:%M:%S",
                "YYYY-MM-DDTHH:MM:SS": "%Y-%m-%dT%H:%M:%S",
                "YYYY-MM-DDTHH:MM:SSZ": "%Y-%m-%dT%H:%M:%SZ",
                "DD-MM-YYYY": "%d-%m-%Y",
                "DD/MM/YYYY": "%d/%m/%Y",
                "MM/DD/YYYY": "%m/%d/%Y",
                "DD-MON-YYYY": "%d-%b-%Y",
                "YYYYMMDD": "%Y%m%d",
                "DD MMM YYYY": "%d %b %Y"
            }
            
            # Find current selection
            current_format_display = "None"
            if rule.date_format:
                for display, fmt in date_format_options.items():
                    if fmt == rule.date_format:
                        current_format_display = display
                        break
            
            selected_format_display = st.selectbox(
                "Date Format",
                options=list(date_format_options.keys()),
                index=list(date_format_options.keys()).index(current_format_display),
                help="Select output date format",
                key=f"date_{selected_col}"
            )
            
            rule.date_format = date_format_options[selected_format_display]
            
            age_cols = st.columns(2)
            with age_cols[0]:
                rule.age_validation_min = st.number_input(
                    "Min Age",
                    min_value=0,
                    max_value=150,
                    value=rule.age_validation_min or 0,
                    key=f"age_min_{selected_col}"
                )
                if rule.age_validation_min == 0:
                    rule.age_validation_min = None
            
            with age_cols[1]:
                rule.age_validation_max = st.number_input(
                    "Max Age",
                    min_value=0,
                    max_value=150,
                    value=rule.age_validation_max or 0,
                    key=f"age_max_{selected_col}"
                )
                if rule.age_validation_max == 0:
                    rule.age_validation_max = None
            
            
            
            # Default value and description
            rule.default_value = st.text_input(
                "Default Value",
                value=rule.default_value or "",
                help="Value to use when field is empty",
                key=f"default_{selected_col}"
            )
            if rule.default_value == "":
                rule.default_value = None
            
            rule.description = st.text_area(
                "Description",
                value=rule.description,
                height=60,
                help="Optional description of this validation rule",
                key=f"desc_{selected_col}"
            )
        
        # Save rule
        st.session_state.column_rules[selected_col] = rule
        
        # Show active rules as badges
        active_rules = rule.get_active_rules()
        if active_rules:
            st.markdown("**Active Rules:**")
            badges_html = "".join([
                f'<span class="badge badge-rule">{r}</span>' 
                for r in active_rules
            ])
            st.markdown(badges_html, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Rules overview table
        with st.expander(" View All Column Rules", expanded=False):
            rules_data = []
            for col in template_cols:
                r = st.session_state.column_rules.get(col, ColumnRule(column_name=col))
                rules_data.append({
                    "Column": col,
                    "Mandatory": "✓" if r.is_mandatory else "",
                    "Rules": ", ".join(r.get_active_rules())
                })
            
            st.dataframe(
                pd.DataFrame(rules_data),
                use_container_width=True,
                hide_index=True
            )
        
        # Navigation
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back to Data Profiling", use_container_width=True, key='btn_rules_to_profile'):
                st.session_state.active_tab = 2  # Data Profiling
                st.session_state.tab_change_requested = True
                st.rerun()
        with col2:
            if st.button("➡️ Next: Mapping", type="primary", use_container_width=True, key='btn_rules_to_mapping'):
                st.session_state.active_tab = 4  # Mapping tab
                st.session_state.tab_change_requested = True
                st.rerun()

# =============================================================================
# TAB 4: COLUMN MAPPING
# =============================================================================

