"""
Documents page - Document upload and management
"""

import streamlit as st
import os
from datetime import datetime
from modules.database import NexcomplyDB
from modules.parser import DocumentParser, load_frameworks, load_policies
from modules.auth import AuthManager, get_current_username
from modules.theme import apply_theme

# Page configuration
st.set_page_config(
    page_title="Documents - Nexcomply",
    layout="wide"
)

# Initialize
auth = AuthManager()
db = NexcomplyDB()
parser = DocumentParser()

# Authentication check
if not auth.is_authenticated():
    st.warning("Please login to access documents")
    auth.show_login_form()
    st.stop()

# Main content
st.title("Document Management")
st.markdown("### Upload and manage compliance documents")
st.markdown("---")

# Tabs for different document types
tab1, tab2, tab3, tab4 = st.tabs([
    "Existing Documents",
    "Upload Documents", 
    "Document Preview",
    "Document Statistics"
])

with tab1:
    st.subheader("Existing Documents")
    
    # Document categories
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Frameworks")
        frameworks_path = "Frameworks/"
        
        if os.path.exists(frameworks_path):
            framework_files = os.listdir(frameworks_path)
            if framework_files:
                for file in framework_files:
                    with st.expander(f"{file}"):
                        filepath = os.path.join(frameworks_path, file)
                        file_size = os.path.getsize(filepath) / 1024  # KB
                        st.write(f"**Size:** {file_size:.2f} KB")
                        st.write(f"**Type:** {file.split('.')[-1].upper()}")
                        
                        if st.button(f"View {file}", key=f"view_fw_{file}"):
                            st.session_state.preview_file = filepath
                            st.session_state.preview_name = file
            else:
                st.info("No framework documents found")
        else:
            st.warning("Frameworks folder not found")
    
    with col2:
        st.markdown("### Policies")
        policies_path = "New Format Policy Docs/"
        
        if os.path.exists(policies_path):
            policy_files = os.listdir(policies_path)
            if policy_files:
                for file in policy_files[:10]:  # Show first 10
                    with st.expander(f"{file}"):
                        filepath = os.path.join(policies_path, file)
                        file_size = os.path.getsize(filepath) / 1024  # KB
                        st.write(f"**Size:** {file_size:.2f} KB")
                        st.write(f"**Type:** {file.split('.')[-1].upper()}")
                        
                        if st.button(f"View {file}", key=f"view_pol_{file}"):
                            st.session_state.preview_file = filepath
                            st.session_state.preview_name = file
                
                if len(policy_files) > 10:
                    st.info(f"+ {len(policy_files) - 10} more policies")
            else:
                st.info("No policy documents found")
        else:
            st.warning("Policies folder not found")
    
    with col3:
        st.markdown("### Knowledge Library")
        kl_path = "Dummy KL/"
        
        if os.path.exists(kl_path):
            kl_files = os.listdir(kl_path)
            if kl_files:
                for file in kl_files:
                    with st.expander(f"{file}"):
                        filepath = os.path.join(kl_path, file)
                        file_size = os.path.getsize(filepath) / 1024  # KB
                        st.write(f"**Size:** {file_size:.2f} KB")
                        st.write(f"**Type:** {file.split('.')[-1].upper()}")
                        
                        if st.button(f"View {file}", key=f"view_kl_{file}"):
                            st.session_state.preview_file = filepath
                            st.session_state.preview_name = file
            else:
                st.info("No knowledge library files found")
        else:
            st.warning("Knowledge library folder not found")

with tab2:
    st.subheader("Upload New Documents")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # File uploader
        st.markdown("### Upload Files")
        
        document_category = st.selectbox(
            "Document Category",
            ["Framework", "Policy", "Knowledge Library", "Questionnaire"]
        )
        
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            type=["pdf", "xlsx", "xls", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            help="Supported formats: PDF, Excel, Images (PNG, JPG)"
        )
        
        if uploaded_files:
            st.markdown("---")
            st.write(f"**{len(uploaded_files)} file(s) selected**")
            
            for uploaded_file in uploaded_files:
                with st.expander(f"{uploaded_file.name}"):
                    metadata = parser.get_file_metadata(uploaded_file)
                    st.write(f"**Type:** {metadata['file_type']}")
                    st.write(f"**Size:** {metadata['file_size'] / 1024:.2f} KB")
                    st.write(f"**Extension:** {metadata['file_extension']}")
            
            if st.button("Process and Upload", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Map category to destination folder (selectbox controls allowed values)
                default_folder = "Frameworks/"
                category_folder_map = {
                    "Framework": "Frameworks/",
                    "Policy": "New Format Policy Docs/",
                    "Knowledge Library": "Dummy KL/",
                    "Questionnaire": "Questionnaires/",
                }
                dest_folder = category_folder_map.get(document_category, default_folder)
                os.makedirs(dest_folder, exist_ok=True)
                
                for i, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Processing {uploaded_file.name}...")
                    
                    # Use basename to prevent path traversal attacks
                    safe_filename = os.path.basename(uploaded_file.name)
                    dest_path = os.path.join(dest_folder, safe_filename)
                    
                    # Avoid silently overwriting an existing file
                    if os.path.exists(dest_path):
                        base, ext = os.path.splitext(safe_filename)
                        counter = 1
                        while os.path.exists(dest_path):
                            dest_path = os.path.join(dest_folder, f"{base}_{counter}{ext}")
                            counter += 1
                        safe_filename = os.path.basename(dest_path)
                    
                    try:
                        # Save file to the appropriate folder on disk first
                        with open(dest_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        try:
                            # Extract content
                            content = parser.extract_text_from_uploaded_file(uploaded_file)
                            
                            # Save to database
                            doc_id = db.add_document(
                                filename=safe_filename,
                                file_type=uploaded_file.type,
                                category=document_category,
                                uploaded_by=get_current_username(),
                                file_size=uploaded_file.size
                            )
                            
                            # Log activity
                            db.log_activity(
                                get_current_username(),
                                "Document Upload",
                                f"Uploaded {safe_filename}"
                            )
                        except Exception as db_err:
                            # Remove the file from disk if DB/processing step fails
                            try:
                                os.remove(dest_path)
                            except OSError:
                                pass
                            raise db_err
                        
                        progress_bar.progress((i + 1) / len(uploaded_files))
                    
                    except Exception as e:
                        st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                
                status_text.text("All files processed!")
                st.success(f"Successfully uploaded {len(uploaded_files)} file(s)")
                
                # Clear uploader
                st.rerun()
    
    with col2:
        st.markdown("### Upload Guidelines")
        
        st.info("""
        **Supported File Types:**
        - PDF documents
        - Excel files (.xlsx, .xls)
        - Images (.png, .jpg, .jpeg)
        
        **Maximum File Size:**
        - 50 MB per file
        
        **Best Practices:**
        - Use clear, descriptive filenames
        - Ensure documents are readable
        - Verify content before upload
        - Organize by category
        """)
        
        st.markdown("---")
        
        st.warning("""
        **Important Notes:**
        - Large files may take time to process
        - OCR accuracy depends on image quality
        - Ensure compliance with data policies
        """)

with tab3:
    st.subheader("Document Preview")
    
    if 'preview_file' in st.session_state and 'preview_name' in st.session_state:
        st.markdown(f"### {st.session_state.preview_name}")
        
        file_ext = st.session_state.preview_name.split('.')[-1].lower()
        
        try:
            if file_ext == 'pdf':
                text_content = parser.extract_pdf_text(st.session_state.preview_file)
                
                st.markdown("**Extracted Text (First 2000 characters):**")
                st.text_area(
                    "Content",
                    text_content[:2000],
                    height=400,
                    label_visibility="collapsed"
                )
                
                st.info(f"Total length: {len(text_content)} characters")
            
            elif file_ext in ['xlsx', 'xls']:
                df = parser.parse_excel(st.session_state.preview_file)
                
                if isinstance(df, str):
                    st.error(df)
                else:
                    st.markdown("**Excel Data Preview:**")
                    st.dataframe(df.head(20), use_container_width=True)
                    st.info(f"Total rows: {len(df)}, Total columns: {len(df.columns)}")
            
            else:
                st.warning(f"Preview not available for {file_ext} files")
        
        except Exception as e:
            st.error(f"Error previewing file: {str(e)}")
        
        if st.button("Close Preview"):
            del st.session_state.preview_file
            del st.session_state.preview_name
            st.rerun()
    else:
        st.info("Select a document from the 'Existing Documents' tab to preview")

with tab4:
    st.subheader("Document Statistics")
    
    # Count documents in each folder
    col1, col2, col3 = st.columns(3)
    
    frameworks_count = len(os.listdir("Frameworks/")) if os.path.exists("Frameworks/") else 0
    policies_count = len(os.listdir("New Format Policy Docs/")) if os.path.exists("New Format Policy Docs/") else 0
    kl_count = len(os.listdir("Dummy KL/")) if os.path.exists("Dummy KL/") else 0
    
    with col1:
        st.metric("Frameworks", frameworks_count)
    
    with col2:
        st.metric("Policies", policies_count)
    
    with col3:
        st.metric("Knowledge Library", kl_count)
    
    st.markdown("---")
    
    # Document database statistics
    st.subheader("Database Records")
    
    try:
        docs_df = db.get_all_documents()
        
        if not docs_df.empty:
            st.dataframe(docs_df, use_container_width=True)
            
            # Summary by category
            st.markdown("### Documents by Category")
            category_counts = docs_df['category'].value_counts()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.bar_chart(category_counts)
            
            with col2:
                for category, count in category_counts.items():
                    st.metric(category, count)
        else:
            st.info("No documents in database yet")
    
    except Exception as e:
        st.error(f"Error loading document statistics: {str(e)}")

# Sidebar
with st.sidebar:
    st.image("Nexcomplylogo.png", use_container_width=True)
    st.subheader("Quick Actions")
    
    if st.button("Refresh Documents", use_container_width=True):
        st.rerun()
    
    if st.button("Clear Preview", use_container_width=True):
        if 'preview_file' in st.session_state:
            del st.session_state.preview_file
            del st.session_state.preview_name
            st.rerun()
    
    st.markdown("---")
    
    st.subheader("Document Info")
    st.info("""
    **Total Documents:**
    - Frameworks: {}
    - Policies: {}
    - Knowledge Library: {}
    
    **Total Size:** Calculating...
    """.format(frameworks_count, policies_count, kl_count))

# Footer
st.markdown("---")
st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
