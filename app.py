"""
Nexcomply v2.0 - Enhanced Compliance Analysis System
Main application entry point
"""

import streamlit as st
import os
import yaml
from modules.database import NexcomplyDB
from modules.auth import AuthManager

# Page configuration
st.set_page_config(
    page_title="Nexcomply v2.0",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load configuration
def load_config():
    """Load application configuration"""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        st.error(f"Error loading configuration: {str(e)}")
        return None

# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'db' not in st.session_state:
        st.session_state.db = NexcomplyDB()
    
    if 'config' not in st.session_state:
        st.session_state.config = load_config()
    
    if 'page' not in st.session_state:
        st.session_state.page = 'Home'

# Initialize
init_session_state()
config = st.session_state.config

# Authentication check
auth = AuthManager()

# Main page content
def main():
    """Main application page"""
    
    with st.sidebar:
        st.image("Nexcomplylogo.png", use_container_width=True)
        st.markdown("---")

    # Header
    st.title("Nexcomply v2.0")
    st.markdown("### Enhanced Compliance Analysis System")
    st.markdown("---")
    
    # Welcome section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## Welcome to Nexcomply
        
        Nexcomply v2.0 is a comprehensive compliance analysis system that helps organizations:
        
        - **Parse and analyze** compliance frameworks and policy documents
        - **Summarize** complex compliance requirements
        - **Identify gaps** between requirements and current controls
        - **Visualize** compliance status with interactive dashboards
        - **Generate reports** in multiple formats (PDF, Excel, HTML)
        - **Manage** documents, users, and configurations
        
        ### Complete Compliance Workflow
        
        1. **Document Parsing**: Upload and parse PDF, Excel, and image documents
        2. **Summarization**: Generate concise summaries using AI
        3. **Embedding Generation**: Create vector representations for comparison
        4. **Gap Identification**: Detect compliance gaps using similarity analysis
        5. **Report Generation**: Create comprehensive compliance reports
        6. **Visualization**: View interactive charts and dashboards
        7. **Admin Management**: Manage users, documents, and settings
        """)
    
    with col2:
        st.markdown("### Quick Stats")
        
        # Get statistics from database
        try:
            stats = st.session_state.db.get_statistics()
            
            st.metric("Total Documents", stats.get('total_documents', 0))
            st.metric("Total Analyses", stats.get('total_analyses', 0))
            st.metric("Total Reports", stats.get('total_reports', 0))
            st.metric("Active Users", stats.get('total_users', 0))
            
        except Exception as e:
            st.error(f"Error loading statistics: {str(e)}")
        
        st.markdown("---")
        
        # Current user info
        if auth.is_authenticated():
            st.success(f"Logged in as: **{auth.get_current_user()}**")
            st.info(f"Role: **{auth.get_current_role()}**")
            
            if st.button("Logout", use_container_width=True):
                auth.logout()
                st.rerun()
        else:
            st.warning("Not logged in")
            if st.button("Login", use_container_width=True):
                st.session_state.page = 'Login'
                st.rerun()
    
    st.markdown("---")
    
    # Navigation guide
    st.markdown("""
    ### Navigation
    
    Use the sidebar to navigate between different sections:
    
    - **Dashboard**: View compliance overview and visualizations
    - **Documents**: Upload and manage documents
    - **Analysis**: Run gap analysis on frameworks and policies
    - **Reports**: Generate and download compliance reports
    - **Knowledge Library**: Search and manage compliance knowledge entries
    - **Admin**: Manage users, documents, and system settings (Admin only)
    
    ### Getting Started
    
    1. Navigate to **Documents** to upload your compliance frameworks and policy documents
    2. Go to **Analysis** to run gap analysis
    3. View results in **Dashboard**
    4. Generate reports in **Reports**
    
    ### Sample Data
    
    The system comes with sample frameworks and policies in:
    - `Frameworks/`: Compliance frameworks (e.g., ISO 27001, SOC 2)
    - `New Format Policy Docs/`: Internal policy documents
    - `Dummy KL/`: Knowledge library for security questionnaires
    """)
    
    st.markdown("---")
    
    # Footer
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p>Nexcomply v2.0 - Enhanced Compliance Analysis System</p>
        <p>© 2024 Nexcomply. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
