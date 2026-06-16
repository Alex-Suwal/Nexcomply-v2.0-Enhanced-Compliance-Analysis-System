"""
Admin page - Admin panel with authentication
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from modules.database import NexcomplyDB
from modules.auth import AuthManager, get_current_username, is_admin
from modules.theme import apply_theme

# Page configuration
st.set_page_config(
    page_title="Admin - Nexcomply",
    layout="wide"
)

# Initialize
auth = AuthManager()
db = NexcomplyDB()

# Authentication check
if not auth.is_authenticated():
    st.warning("Please login to access admin panel")
    auth.show_login_form()
    st.stop()

# Admin role check
if not is_admin():
    st.error("Access Denied: Admin role required")
    st.warning("You must be an administrator to access this page.")
    st.stop()

# Main content
st.title("Admin Panel")
st.markdown("### System administration and management")
st.markdown("---")

# Admin tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "User Management",
    "Document Management",
    "Configuration",
    "Analytics",
    "Activity Logs"
])

with tab1:
    st.subheader("User Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Existing Users")
        
        try:
            users_df = db.get_all_users()
            
            if not users_df.empty:
                # Display users
                display_df = users_df[[
                    'id', 'username', 'role', 'email', 
                    'created_at', 'last_login', 'is_active'
                ]].copy()
                
                # Format dates
                display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d')
                display_df['last_login'] = pd.to_datetime(display_df['last_login']).dt.strftime('%Y-%m-%d %H:%M')
                
                st.dataframe(display_df, use_container_width=True)
                
                # User statistics
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Users", len(users_df))
                
                with col2:
                    active_users = len(users_df[users_df['is_active'] == True])
                    st.metric("Active Users", active_users)
                
                with col3:
                    admin_count = len(users_df[users_df['role'] == 'Admin'])
                    st.metric("Administrators", admin_count)
            else:
                st.info("No users found")
        
        except Exception as e:
            st.error(f"Error loading users: {str(e)}")
    
    with col2:
        st.markdown("### Add New User")
        
        with st.form("add_user_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["Admin", "Auditor", "Analyst", "Viewer"])
            new_email = st.text_input("Email (Optional)")
            
            submit_user = st.form_submit_button("Add User", use_container_width=True)
            
            if submit_user:
                if new_username and new_password:
                    success = db.add_user(new_username, new_password, new_role, new_email)
                    
                    if success:
                        st.success(f"User '{new_username}' added successfully!")
                        
                        # Log activity
                        db.log_activity(
                            get_current_username(),
                            "User Management",
                            f"Added new user: {new_username}"
                        )
                        
                        st.rerun()
                    else:
                        st.error("Failed to add user. Username may already exist.")
                else:
                    st.error("Please provide username and password")
        
        st.markdown("---")
        
        st.markdown("### Manage User")
        
        if 'users_df' in locals() and not users_df.empty:
            selected_user_id = st.selectbox(
                "Select User",
                users_df['id'].tolist(),
                format_func=lambda x: users_df[users_df['id'] == x]['username'].iloc[0]
            )
            
            if selected_user_id:
                user_row = users_df[users_df['id'] == selected_user_id].iloc[0]
                
                st.info(f"**Username:** {user_row['username']}")
                st.info(f"**Current Role:** {user_row['role']}")
                
                # Update role
                new_role = st.selectbox(
                    "Update Role",
                    ["Admin", "Auditor", "Analyst", "Viewer"],
                    index=["Admin", "Auditor", "Analyst", "Viewer"].index(user_row['role'])
                    if user_row['role'] in ["Admin", "Auditor", "Analyst", "Viewer"] else 0,
                    key="update_role"
                )
                
                if st.button("Update Role", use_container_width=True):
                    db.update_user(selected_user_id, role=new_role)
                    st.success("Role updated successfully!")
                    
                    db.log_activity(
                        get_current_username(),
                        "User Management",
                        f"Updated role for {user_row['username']}"
                    )
                    
                    st.rerun()
                
                # Deactivate user
                if user_row['is_active']:
                    if st.button("Deactivate User", use_container_width=True):
                        db.delete_user(selected_user_id)
                        st.success("User deactivated!")
                        
                        db.log_activity(
                            get_current_username(),
                            "User Management",
                            f"Deactivated user: {user_row['username']}"
                        )
                        
                        st.rerun()

with tab2:
    st.subheader("Document Management")
    
    try:
        docs_df = db.get_all_documents()
        
        if not docs_df.empty:
            # Display documents
            st.dataframe(docs_df, use_container_width=True)
            
            # Document statistics
            st.markdown("---")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Documents", len(docs_df))
            
            with col2:
                frameworks = len(docs_df[docs_df['category'] == 'Framework'])
                st.metric("Frameworks", frameworks)
            
            with col3:
                policies = len(docs_df[docs_df['category'] == 'Policy'])
                st.metric("Policies", policies)
            
            with col4:
                total_size = docs_df['file_size'].sum() / (1024 * 1024)  # MB
                st.metric("Total Size", f"{total_size:.2f} MB")
            
            st.markdown("---")
            
            # Document management actions
            st.subheader("Manage Documents")
            
            selected_doc_id = st.selectbox(
                "Select Document",
                docs_df['id'].tolist(),
                format_func=lambda x: docs_df[docs_df['id'] == x]['filename'].iloc[0]
            )
            
            if selected_doc_id:
                doc_row = docs_df[docs_df['id'] == selected_doc_id].iloc[0]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"**Filename:** {doc_row['filename']}")
                    st.info(f"**Type:** {doc_row['file_type']}")
                    st.info(f"**Category:** {doc_row['category']}")
                
                with col2:
                    st.info(f"**Upload Date:** {doc_row['upload_date']}")
                    st.info(f"**Uploaded By:** {doc_row['uploaded_by']}")
                    st.info(f"**Size:** {doc_row['file_size'] / 1024:.2f} KB")
                
                if st.button("Delete Document", type="primary", use_container_width=True):
                    st.session_state['confirm_delete_id'] = selected_doc_id

                if st.session_state.get('confirm_delete_id') == selected_doc_id:
                    st.warning(f"Are you sure you want to delete **{doc_row['filename']}**?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Yes, Delete", key="confirm_delete", type="primary", use_container_width=True):
                            db.delete_document(selected_doc_id)
                            st.session_state.pop('confirm_delete_id', None)
                            st.success("Document deleted!")

                            db.log_activity(
                                get_current_username(),
                                "Document Management",
                                f"Deleted document: {doc_row['filename']}"
                            )

                            st.rerun()
                    with col_no:
                        if st.button("Cancel", key="cancel_delete", use_container_width=True):
                            st.session_state.pop('confirm_delete_id', None)
                            st.rerun()
        else:
            st.info("No documents in database")
    
    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")

with tab3:
    st.subheader("System Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Gap Detection Settings")
        
        critical_threshold = st.slider(
            "Critical Threshold",
            0.0, 1.0, 
            float(db.get_config('critical_threshold', 0.3)),
            help="Similarity score below this is Critical"
        )
        
        high_threshold = st.slider(
            "High Threshold",
            0.0, 1.0,
            float(db.get_config('high_threshold', 0.5)),
            help="Similarity score below this is High"
        )
        
        medium_threshold = st.slider(
            "Medium Threshold",
            0.0, 1.0,
            float(db.get_config('medium_threshold', 0.7)),
            help="Similarity score below this is Medium"
        )
        
        low_threshold = st.slider(
            "Low Threshold",
            0.0, 1.0,
            float(db.get_config('low_threshold', 0.85)),
            help="Similarity score below this is Low"
        )
        
        if st.button("Save Gap Detection Settings", use_container_width=True):
            db.set_config('critical_threshold', str(critical_threshold), get_current_username())
            db.set_config('high_threshold', str(high_threshold), get_current_username())
            db.set_config('medium_threshold', str(medium_threshold), get_current_username())
            db.set_config('low_threshold', str(low_threshold), get_current_username())
            
            st.success("Gap detection settings saved!")
            
            db.log_activity(
                get_current_username(),
                "Configuration",
                "Updated gap detection thresholds"
            )
    
    with col2:
        st.markdown("### Model Settings")
        
        t5_model = st.selectbox(
            "T5 Model",
            ["t5-small", "t5-base", "t5-large"],
            index=0
        )
        
        sbert_model = st.selectbox(
            "Sentence-BERT Model",
            ["all-MiniLM-L6-v2", "all-mpnet-base-v2", "paraphrase-MiniLM-L6-v2"],
            index=0
        )
        
        enable_caching = st.checkbox(
            "Enable Model Caching",
            value=True
        )
        
        cache_ttl = st.number_input(
            "Cache TTL (seconds)",
            min_value=60,
            max_value=86400,
            value=3600
        )
        
        if st.button("Save Model Settings", use_container_width=True):
            db.set_config('t5_model', t5_model, get_current_username())
            db.set_config('sbert_model', sbert_model, get_current_username())
            db.set_config('enable_caching', str(enable_caching), get_current_username())
            db.set_config('cache_ttl', str(cache_ttl), get_current_username())
            
            st.success("Model settings saved!")
            
            db.log_activity(
                get_current_username(),
                "Configuration",
                "Updated model settings"
            )
    
    st.markdown("---")
    
    # Database management
    st.subheader("Database Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Backup Database", use_container_width=True):
            st.info("Database backup feature coming soon!")
    
    with col2:
        if st.button("Optimize Database", use_container_width=True):
            st.info("Database optimization feature coming soon!")
    
    with col3:
        if st.button("Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("Cache cleared!")

with tab4:
    st.subheader("System Analytics")
    
    try:
        stats = db.get_statistics()
        
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Users", stats.get('total_users', 0))
        
        with col2:
            st.metric("Total Documents", stats.get('total_documents', 0))
        
        with col3:
            st.metric("Total Analyses", stats.get('total_analyses', 0))
        
        with col4:
            st.metric("Total Reports", stats.get('total_reports', 0))
        
        st.markdown("---")
        
        # Analysis history
        st.subheader("Analysis History")
        
        analysis_history = db.get_analysis_history(limit=20)
        
        if not analysis_history.empty:
            st.dataframe(analysis_history, use_container_width=True)
            
            # Gap severity distribution
            st.markdown("---")
            st.subheader("Gap Severity Distribution")
            
            severity_counts = analysis_history['gap_severity'].value_counts()
            st.bar_chart(severity_counts)
        else:
            st.info("No analysis history available")
    
    except Exception as e:
        st.error(f"Error loading analytics: {str(e)}")

with tab5:
    st.subheader("Activity Logs")
    
    try:
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            log_limit = st.selectbox("Show Entries", [50, 100, 200, 500], index=0)
        
        with col2:
            action_filter = st.selectbox(
                "Filter by Action",
                ["All", "Login", "Logout", "Document Upload", "Gap Analysis", "Report Generation", "User Management", "Configuration"]
            )
        
        with col3:
            if st.button("Refresh Logs"):
                st.rerun()
        
        # Load logs
        logs_df = db.get_activity_logs(limit=log_limit)
        
        if not logs_df.empty:
            # Apply filter
            if action_filter != "All":
                logs_df = logs_df[logs_df['action'] == action_filter]
            
            # Display logs
            st.dataframe(logs_df, use_container_width=True)
            
            # Log statistics
            st.markdown("---")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Logs", len(logs_df))
            
            with col2:
                unique_users = logs_df['username'].nunique()
                st.metric("Unique Users", unique_users)
            
            with col3:
                recent_activities = len(logs_df[
                    logs_df['timestamp'] >= datetime.now().strftime('%Y-%m-%d')
                ])
                st.metric("Today's Activities", recent_activities)
        else:
            st.info("No activity logs available")
    
    except Exception as e:
        st.error(f"Error loading activity logs: {str(e)}")

# Sidebar
with st.sidebar:
    st.image("Nexcomplylogo.png", use_container_width=True)
    st.subheader("Admin Info")
    
    st.success(f"**Logged in as:** {get_current_username()}")
    st.info(f"**Role:** Admin")
    
    st.markdown("---")
    
    st.subheader("Quick Stats")
    
    try:
        stats = db.get_statistics()
        
        st.metric("System Users", stats.get('total_users', 0))
        st.metric("Documents", stats.get('total_documents', 0))
        st.metric("Recent Activity", stats.get('recent_activities', 0))
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    st.subheader("Admin Actions")
    
    if st.button("Refresh All", use_container_width=True):
        st.rerun()
    
    if st.button("Export System Data", use_container_width=True):
        st.info("Export feature coming soon!")
    
    st.markdown("---")
    
    st.warning("""
    **Admin Responsibilities:**
    
    - Manage users carefully
    - Review activity logs regularly
    - Maintain system configuration
    - Monitor system performance
    - Backup data periodically
    """)

# Footer
st.markdown("---")
st.markdown(f"*Admin panel accessed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
