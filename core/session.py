"""
Session state management
Handles initialization, save/load, and auto-save functionality
"""
import streamlit as st
import pickle
import os
import json
import hashlib
import pandas as pd
from datetime import datetime
from dataclasses import asdict
from core.models import FileData, ColumnRule, ColumnMapping
from config.settings import AUTO_SAVE_FILE

def init_session_state():
    """Initialize session state with all required keys"""
    defaults = {
        # Workflow State
        'active_tab': 0,
        'completed_steps': set(),
        
        # File Data
        'template_file': FileData(),
        'source_file': FileData(),
        
        # Configuration
        'column_rules': {},  # column_name -> ColumnRule
        'mappings': [],  # List[ColumnMapping]
        
        # Processing Results
        'validation_results': {},
        'transformed_data': None,
        'processing_log': [],
        
        # UI State
        'show_mapping_panel': False,
        'auto_map_triggered': False,
        'selected_mapping_id': None,
        
        # Session
        'session_id': hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8],
        
        # Auto-save flag
        '_state_loaded': False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Auto-load saved state on first run
    if not st.session_state._state_loaded:
        auto_load_state()
        st.session_state._state_loaded = True

def save_session_state():
    """Export session state to JSON"""
    state_dict = {
        'column_rules': {k: asdict(v) for k, v in st.session_state.column_rules.items()},
        'mappings': [asdict(m) for m in st.session_state.mappings],
        'template_file': {
            'name': st.session_state.template_file.name,
            'selected_sheet': st.session_state.template_file.selected_sheet,
            'header_row': st.session_state.template_file.header_row,
        },
        'source_file': {
            'name': st.session_state.source_file.name,
            'selected_sheet': st.session_state.source_file.selected_sheet,
            'header_row': st.session_state.source_file.header_row,
        },
        'session_id': st.session_state.session_id
    }
    return json.dumps(state_dict, indent=2, default=str)

def load_session_state(json_data: str):
    """Import session state from JSON"""
    try:
        data = json.loads(json_data)
        
        # Restore column rules
        st.session_state.column_rules = {
            k: ColumnRule(**v) for k, v in data.get('column_rules', {}).items()
        }
        
        # Restore mappings
        st.session_state.mappings = [ColumnMapping(**m) for m in data.get('mappings', [])]
        
        # Restore file metadata (files themselves need to be re-uploaded)
        if 'template_file' in data:
            st.session_state.template_file.name = data['template_file'].get('name', '')
            st.session_state.template_file.selected_sheet = data['template_file'].get('selected_sheet')
            st.session_state.template_file.header_row = data['template_file'].get('header_row', 0)
        
        if 'source_file' in data:
            st.session_state.source_file.name = data['source_file'].get('name', '')
            st.session_state.source_file.selected_sheet = data['source_file'].get('selected_sheet')
            st.session_state.source_file.header_row = data['source_file'].get('header_row', 0)
        
        return True
    except Exception as e:
        st.error(f"Error loading session: {e}")
        return False

def auto_save_state():
    """Automatically save complete session state to file (including uploaded files)"""
    try:
        state_to_save = {
            'column_rules': {k: asdict(v) for k, v in st.session_state.column_rules.items()},
            'mappings': [asdict(m) for m in st.session_state.mappings],
            'active_tab': st.session_state.active_tab,
            'session_id': st.session_state.session_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save template file if loaded
        if st.session_state.template_file.name:
            state_to_save['template_file'] = {
                'name': st.session_state.template_file.name,
                'selected_sheet': st.session_state.template_file.selected_sheet,
                'header_row': st.session_state.template_file.header_row,
                'raw_data': st.session_state.template_file.raw_data,
                'data': {k: v.to_dict() for k, v in st.session_state.template_file.data.items()},
                'sheets': st.session_state.template_file.sheets,
                'columns': st.session_state.template_file.columns,
                'all_sheets': st.session_state.template_file.all_sheets,
            }
        
        # Save source file if loaded
        if st.session_state.source_file.name:
            state_to_save['source_file'] = {
                'name': st.session_state.source_file.name,
                'selected_sheet': st.session_state.source_file.selected_sheet,
                'header_row': st.session_state.source_file.header_row,
                'raw_data': st.session_state.source_file.raw_data,
                'data': {k: v.to_dict() for k, v in st.session_state.source_file.data.items()},
                'sheets': st.session_state.source_file.sheets,
                'columns': st.session_state.source_file.columns,
                'all_sheets': getattr(st.session_state.source_file, 'all_sheets', []),
            }
        
        # Save to file using pickle (handles binary data)
        with open(AUTO_SAVE_FILE, 'wb') as f:
            pickle.dump(state_to_save, f)
        
        return True
    except Exception as e:
        # Silent fail - don't interrupt user experience
        print(f"Auto-save failed: {e}")
        return False

def auto_load_state():
    """Automatically load saved state on startup"""
    try:
        if os.path.exists(AUTO_SAVE_FILE):
            with open(AUTO_SAVE_FILE, 'rb') as f:
                saved_state = pickle.load(f)
            
            # Restore column rules
            st.session_state.column_rules = {
                k: ColumnRule(**v) for k, v in saved_state.get('column_rules', {}).items()
            }
            
            # Restore mappings
            st.session_state.mappings = [ColumnMapping(**m) for m in saved_state.get('mappings', [])]
            
            # Restore template file
            if 'template_file' in saved_state:
                tf = saved_state['template_file']
                st.session_state.template_file.name = tf.get('name', '')
                st.session_state.template_file.selected_sheet = tf.get('selected_sheet')
                st.session_state.template_file.header_row = tf.get('header_row', 0)
                st.session_state.template_file.raw_data = tf.get('raw_data')
                st.session_state.template_file.sheets = tf.get('sheets', [])
                st.session_state.template_file.columns = tf.get('columns', {})
                st.session_state.template_file.all_sheets = tf.get('all_sheets', [])
                
                # Restore dataframes
                if 'data' in tf:
                    st.session_state.template_file.data = {
                        k: pd.DataFrame.from_dict(v) for k, v in tf['data'].items()
                    }
            
            # Restore source file
            if 'source_file' in saved_state:
                sf = saved_state['source_file']
                st.session_state.source_file.name = sf.get('name', '')
                st.session_state.source_file.selected_sheet = sf.get('selected_sheet')
                st.session_state.source_file.header_row = sf.get('header_row', 0)
                st.session_state.source_file.raw_data = sf.get('raw_data')
                st.session_state.source_file.sheets = sf.get('sheets', [])
                st.session_state.source_file.columns = sf.get('columns', {})
                st.session_state.source_file.all_sheets = sf.get('all_sheets', [])
                
                # Restore dataframes
                if 'data' in sf:
                    st.session_state.source_file.data = {
                        k: pd.DataFrame.from_dict(v) for k, v in sf['data'].items()
                    }
            
            # Restore active tab
            if 'active_tab' in saved_state:
                st.session_state.active_tab = saved_state['active_tab']
            
            return True
    except Exception as e:
        # Silent fail - start fresh if load fails
        print(f"Auto-load failed: {e}")
        return False

def reset_application():
    """Reset application state and delete auto-save file"""
    # Delete auto-save file
    if os.path.exists(AUTO_SAVE_FILE):
        try:
            os.remove(AUTO_SAVE_FILE)
        except:
            pass
    
    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # Reinitialize
    init_session_state()
