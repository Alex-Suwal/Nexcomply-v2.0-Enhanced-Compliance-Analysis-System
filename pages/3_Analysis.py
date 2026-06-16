"""
Analysis page - Gap analysis interface
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from modules.database import NexcomplyDB
from modules.parser import load_frameworks, load_policies, DocumentParser
from modules.summarizer import get_summarizer
from modules.embeddings import get_embedding_generator, SimilarityCalculator
from modules.gap_detector import GapDetector
from modules.auth import AuthManager, get_current_username
from modules.theme import apply_theme
from modules.visualizations import create_pie_chart, create_gap_analysis_bar_chart


def _chunk_policy_text(text, min_chunk_chars=80):
    """
    Split policy text into meaningful chunks for TF-IDF similarity.

    PDF-extracted text uses single newlines within paragraphs.  We group
    consecutive non-empty lines until we have at least *min_chunk_chars*
    characters, then start a new chunk.  This gives semantically coherent
    sections instead of comparing requirements against the whole document.
    """
    _fallback_max_chars = 2000  # max chars used when no chunks are found
    lines = text.split('\n')
    chunks = []
    current = []
    current_len = 0
    for line in lines:
        line = line.strip()
        if not line:
            if current_len >= min_chunk_chars:
                chunks.append(' '.join(current))
                current, current_len = [], 0
            continue
        current.append(line)
        current_len += len(line)
        if current_len >= min_chunk_chars:
            chunks.append(' '.join(current))
            current, current_len = [], 0
    # Flush any remaining lines even if they are smaller than min_chunk_chars
    if current and current_len >= min_chunk_chars // 3:
        chunks.append(' '.join(current))
    return chunks if chunks else [text[:_fallback_max_chars]]

# Page configuration
st.set_page_config(
    page_title="Analysis - Nexcomply",
    layout="wide"
)

# Initialize
auth = AuthManager()
db = NexcomplyDB()

# Authentication check
if not auth.is_authenticated():
    st.warning("Please login to perform analysis")
    auth.show_login_form()
    st.stop()

# Cache resource-intensive operations
@st.cache_resource
def load_models():
    """Load AI models"""
    summarizer = get_summarizer()
    embedding_gen = get_embedding_generator()
    return summarizer, embedding_gen

# Main content
st.title("Compliance Gap Analysis")
st.markdown("### Analyze compliance gaps between frameworks and policies")
st.markdown("---")

# Load models
with st.spinner("Loading AI models..."):
    summarizer, embedding_gen = load_models()

# Analysis workflow tabs
tab1, tab2, tab3 = st.tabs([
    "Select Documents",
    "Run Analysis",
    "View Results"
])

with tab1:
    st.subheader("Select Documents for Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Compliance Frameworks")
        
        # Load available frameworks
        frameworks_path = "Frameworks/"
        frameworks_dict = load_frameworks(frameworks_path)
        
        if frameworks_dict:
            selected_framework = st.selectbox(
                "Select Framework",
                list(frameworks_dict.keys()),
                help="Choose a compliance framework to analyze against"
            )
            
            if selected_framework:
                st.success(f"Selected: {selected_framework}")
                
                # Show framework preview
                with st.expander("Preview Framework"):
                    framework_data = frameworks_dict[selected_framework]
                    
                    if isinstance(framework_data, pd.DataFrame):
                        st.dataframe(framework_data.head(10), use_container_width=True)
                        st.info(f"Total rows: {len(framework_data)}")
                    elif isinstance(framework_data, str):
                        st.text_area(
                            "Framework Content",
                            framework_data[:1000],
                            height=200,
                            label_visibility="collapsed"
                        )
                        st.info(f"Total length: {len(framework_data)} characters")
                
                # Store in session state
                st.session_state.selected_framework = selected_framework
                st.session_state.framework_data = framework_data
        else:
            st.warning("No frameworks found in Frameworks folder")
    
    with col2:
        st.markdown("### Internal Policies")
        
        # Load available policies
        policies_path = "New Format Policy Docs/"
        policies_dict = load_policies(policies_path)
        
        if policies_dict:
            selected_policies = st.multiselect(
                "Select Policies to Compare",
                list(policies_dict.keys()),
                help="Choose one or more internal policies"
            )
            
            if selected_policies:
                st.success(f"Selected {len(selected_policies)} policy/policies")
                
                # Show policy preview
                for policy in selected_policies:
                    with st.expander(f"Preview: {policy}"):
                        policy_text = policies_dict[policy]
                        st.text_area(
                            f"Policy Content - {policy}",
                            policy_text[:500],
                            height=150,
                            label_visibility="collapsed",
                            key=f"preview_{policy}"
                        )
                        st.info(f"Total length: {len(policy_text)} characters")
                
                # Store in session state
                st.session_state.selected_policies = selected_policies
                st.session_state.policies_data = {p: policies_dict[p] for p in selected_policies}
        else:
            st.warning("No policies found in New Format Policy Docs folder")
    
    st.markdown("---")
    
    # Additional options
    st.subheader("Analysis Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        _default_threshold = 0.3
        _threshold_help = (
            "Cosine similarity threshold. Scores above this mean the policy covers "
            "the requirement (no gap). Typical range: 0.3–0.9 for neural embeddings, "
            "0.05–0.30 for TF-IDF offline mode."
        )
        # Use the previously saved threshold if available so the value persists
        _saved_threshold = st.session_state.get('similarity_threshold', _default_threshold)
        similarity_threshold = st.slider(
            "Similarity Threshold",
            0.0, 1.0, _saved_threshold,
            help=_threshold_help
        )
        if not embedding_gen.has_model:
            st.caption(
                "⚠️ Offline mode: neural model unavailable. "
                "Using TF-IDF keyword similarity (scores are lower than semantic embeddings)."
            )
        if st.button("Save Threshold", use_container_width=True):
            st.session_state.similarity_threshold = similarity_threshold
            st.success(f"Threshold saved: {similarity_threshold:.2f}")
        else:
            # Keep the last saved value active; only update when button is pressed
            if 'similarity_threshold' not in st.session_state:
                st.session_state.similarity_threshold = _default_threshold
    
    with col2:
        enable_summarization = st.checkbox(
            "Enable Summarization",
            value=True,
            help="Summarize documents before analysis"
        )
        st.session_state.enable_summarization = enable_summarization
    
    with col3:
        save_results = st.checkbox(
            "Save Results to Database",
            value=True,
            help="Store analysis results for future reference"
        )
        st.session_state.save_results = save_results

with tab2:
    st.subheader("Run Gap Analysis")
    
    # Check if documents are selected
    if 'selected_framework' not in st.session_state:
        st.warning("Please select a framework in the 'Select Documents' tab")
        st.stop()
    
    if 'selected_policies' not in st.session_state or not st.session_state.selected_policies:
        st.warning("Please select at least one policy in the 'Select Documents' tab")
        st.stop()
    
    # Display selected documents
    st.info(f"**Framework:** {st.session_state.selected_framework}")
    st.info(f"**Policies:** {', '.join(st.session_state.selected_policies)}")
    
    st.markdown("---")
    
    # Run analysis button
    if st.button("Start Analysis", type="primary", use_container_width=True):
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Extract framework requirements
            status_text.text("Step 1/5: Extracting framework requirements...")
            progress_bar.progress(0.2)
            
            framework_data = st.session_state.framework_data
            
            # Convert framework to text
            if isinstance(framework_data, pd.DataFrame):
                # Combine relevant columns
                if 'Control' in framework_data.columns and 'Description' in framework_data.columns:
                    framework_requirements = (
                        framework_data['Control'].astype(str) + ": " + 
                        framework_data['Description'].astype(str)
                    ).tolist()
                else:
                    # Use all columns
                    framework_requirements = framework_data.apply(
                        lambda row: ' '.join(row.astype(str)), axis=1
                    ).tolist()
            else:
                # Split text into paragraphs
                framework_requirements = [
                    para.strip() for para in framework_data.split('\n\n') 
                    if len(para.strip()) > 50
                ]
            
            # Step 2: Summarize if enabled
            if st.session_state.enable_summarization:
                status_text.text("Step 2/5: Summarizing documents...")
                progress_bar.progress(0.4)
                
                # Summarize framework requirements
                summarized_requirements = []
                for req in framework_requirements:
                    if len(req) > 500:
                        summary = summarizer.summarize(req, max_length=100)
                        summarized_requirements.append(summary)
                    else:
                        summarized_requirements.append(req)
                
                framework_requirements = summarized_requirements
                
                # Summarize policies
                policies_data = {}
                for policy_name, policy_text in st.session_state.policies_data.items():
                    if len(policy_text) > 2000:
                        summary = summarizer.summarize_long_text(policy_text, max_length=200)
                        policies_data[policy_name] = summary
                    else:
                        policies_data[policy_name] = policy_text
            else:
                policies_data = st.session_state.policies_data
            
            gap_results = []
            
            if embedding_gen.has_model:
                # ── Neural embedding path (SentenceTransformer available) ──────
                # Step 3: Generate embeddings
                status_text.text("Step 3/5: Generating embeddings...")
                progress_bar.progress(0.6)

                req_embeddings = embedding_gen.generate_embeddings(framework_requirements)
                policy_texts = list(policies_data.values())
                policy_embeddings = embedding_gen.generate_embeddings(policy_texts)
                policy_names = list(policies_data.keys())

                # Step 4: Detect gaps
                status_text.text("Step 4/5: Identifying compliance gaps...")
                progress_bar.progress(0.8)

                gap_detector = GapDetector()
                similarity_calc = SimilarityCalculator()

                for i, (requirement, req_embedding) in enumerate(
                    zip(framework_requirements, req_embeddings)
                ):
                    best_score = 0.0
                    best_policy = None

                    for policy_name, policy_embedding in zip(policy_names, policy_embeddings):
                        score = similarity_calc.calculate_cosine_similarity(
                            req_embedding, policy_embedding
                        )
                        if score > best_score:
                            best_score = score
                            best_policy = policy_name

                    severity = gap_detector.determine_gap_severity(best_score)
                    gap_exists = best_score < st.session_state.similarity_threshold

                    gap_results.append({
                        'requirement_index': i + 1,
                        'requirement': requirement if len(requirement) <= 10000 else requirement[:10000] + '... [truncated]',
                        'best_matching_policy': best_policy,
                        'similarity_score': best_score,
                        'gap_severity': severity,
                        'gap_exists': gap_exists,
                        'recommendations': gap_detector._generate_recommendations(best_score, severity)
                    })

            else:
                # ── TF-IDF offline fallback (no network / model unavailable) ──
                # Compare each requirement against fine-grained policy chunks so
                # that specific sections can be matched accurately.
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity as sk_cosine_similarity

                # Step 3: Build TF-IDF index
                status_text.text("Step 3/5: Building TF-IDF similarity index...")
                progress_bar.progress(0.6)

                # Severity thresholds calibrated for TF-IDF score range
                tfidf_gap_detector = GapDetector(thresholds={
                    'critical': 0.05,
                    'high':     0.10,
                    'medium':   0.15,
                    'low':      0.20,
                })

                # Chunk each policy into semantically focused paragraphs
                policy_chunks_map = {}
                for policy_name, policy_text in policies_data.items():
                    chunks = _chunk_policy_text(policy_text)
                    policy_chunks_map[policy_name] = chunks

                all_policy_chunks = [
                    chunk
                    for chunks in policy_chunks_map.values()
                    for chunk in chunks
                ]

                all_texts = framework_requirements + all_policy_chunks
                vectorizer = TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=1,
                    stop_words='english',
                    sublinear_tf=True,
                )
                vectorizer.fit(all_texts)
                req_vectors = vectorizer.transform(framework_requirements)

                # Step 4: Detect gaps
                status_text.text("Step 4/5: Identifying compliance gaps...")
                progress_bar.progress(0.8)

                for i, requirement in enumerate(framework_requirements):
                    best_score = 0.0
                    best_policy = None

                    req_vec = req_vectors[i]
                    for policy_name, chunks in policy_chunks_map.items():
                        chunk_vecs = vectorizer.transform(chunks)
                        scores = sk_cosine_similarity(req_vec, chunk_vecs)[0]
                        chunk_best = float(scores.max()) if len(scores) > 0 else 0.0
                        if chunk_best > best_score:
                            best_score = chunk_best
                            best_policy = policy_name

                    severity = tfidf_gap_detector.determine_gap_severity(best_score)
                    gap_exists = best_score < st.session_state.similarity_threshold

                    gap_results.append({
                        'requirement_index': i + 1,
                        'requirement': requirement if len(requirement) <= 10000 else requirement[:10000] + '... [truncated]',
                        'best_matching_policy': best_policy,
                        'similarity_score': best_score,
                        'gap_severity': severity,
                        'gap_exists': gap_exists,
                        'recommendations': tfidf_gap_detector._generate_recommendations(best_score, severity)
                    })
            
            # Step 5: Save results
            status_text.text("Step 5/5: Saving results...")
            progress_bar.progress(0.9)
            
            # Store in session state
            st.session_state.gap_results = gap_results
            st.session_state.analysis_complete = True
            st.session_state.analysis_timestamp = datetime.now()
            
            # Save to database if enabled
            if st.session_state.save_results:
                for result in gap_results:
                    db.save_analysis_result(
                        framework_name=st.session_state.selected_framework,
                        policy_name=result['best_matching_policy'],
                        similarity_score=result['similarity_score'],
                        gap_severity=result['gap_severity'],
                        gap_description=result['requirement'],
                        recommendations=result['recommendations'],
                        analyzed_by=get_current_username()
                    )
                
                # Log activity
                db.log_activity(
                    get_current_username(),
                    "Gap Analysis",
                    f"Analyzed {st.session_state.selected_framework} against {len(st.session_state.selected_policies)} policies"
                )
            
            progress_bar.progress(1.0)
            status_text.text("Analysis complete!")
            
            st.success(f"Analysis completed! Found {len(gap_results)} requirements analyzed.")
            st.info("Switch to 'View Results' tab to see detailed results")
            
        except Exception as e:
            st.error(f"Error during analysis: {str(e)}")
            st.exception(e)

with tab3:
    st.subheader("Analysis Results")
    
    if 'gap_results' not in st.session_state or not st.session_state.gap_results:
        st.info("No analysis results available. Run an analysis first.")
        st.stop()
    
    # Display timestamp
    if 'analysis_timestamp' in st.session_state:
        st.caption(f"Analysis performed: {st.session_state.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.markdown("---")
    
    # Summary metrics
    gap_results = st.session_state.gap_results
    gap_df = pd.DataFrame(gap_results)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_reqs = len(gap_results)
        st.metric("Total Requirements", total_reqs)
    
    with col2:
        avg_score = gap_df['similarity_score'].mean()
        st.metric("Avg Similarity", f"{avg_score:.2f}")
    
    with col3:
        gaps_found = gap_df['gap_exists'].sum()
        st.metric("Gaps Found", gaps_found)
    
    with col4:
        compliance_pct = ((total_reqs - gaps_found) / total_reqs * 100) if total_reqs > 0 else 0
        st.metric("Compliance %", f"{compliance_pct:.1f}%")
    
    st.markdown("---")
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Severity distribution
        severity_counts = gap_df['gap_severity'].value_counts().to_dict()
        fig_pie = create_pie_chart(severity_counts)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Gaps by policy
        policy_gaps = gap_df[gap_df['gap_exists']].groupby('best_matching_policy').size().to_dict()
        if policy_gaps:
            fig_bar = create_gap_analysis_bar_chart(policy_gaps)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No gaps found!")
    
    st.markdown("---")
    
    # Detailed results table
    st.subheader("Detailed Gap Analysis")
    
    # Filter options
    col1, col2 = st.columns(2)
    
    with col1:
        severity_filter = st.multiselect(
            "Filter by Severity",
            ['Critical', 'High', 'Medium', 'Low', 'None'],
            default=['Critical', 'High']
        )
    
    with col2:
        show_gaps_only = st.checkbox("Show Gaps Only", value=True)
    
    # Apply filters
    filtered_df = gap_df.copy()
    
    if severity_filter:
        filtered_df = filtered_df[filtered_df['gap_severity'].isin(severity_filter)]
    
    if show_gaps_only:
        filtered_df = filtered_df[filtered_df['gap_exists']]
    
    # Display table
    if not filtered_df.empty:
        # Format for display
        display_df = filtered_df[[
            'requirement_index',
            'requirement',
            'best_matching_policy',
            'similarity_score',
            'gap_severity'
        ]].copy()
        
        display_df['similarity_score'] = display_df['similarity_score'].round(2)
        
        # Color code by severity
        def highlight_severity(row):
            severity = row['gap_severity']
            if severity == 'Critical':
                return ['background-color: #ffcccc'] * len(row)
            elif severity == 'High':
                return ['background-color: #ffe6cc'] * len(row)
            elif severity == 'Medium':
                return ['background-color: #ffffcc'] * len(row)
            elif severity == 'Low':
                return ['background-color: #e6ffe6'] * len(row)
            return [''] * len(row)
        
        styled_df = display_df.style.apply(highlight_severity, axis=1)
        st.dataframe(styled_df, use_container_width=True)
        
        # Export options
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "gap_analysis.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            if st.button("Generate Report", use_container_width=True):
                st.info("Navigate to Reports tab to generate comprehensive report")
        
        with col3:
            if st.button("Run New Analysis", use_container_width=True):
                # Clear results
                del st.session_state.gap_results
                del st.session_state.analysis_complete
                st.rerun()
    else:
        st.info("No results match the selected filters")

# Sidebar
with st.sidebar:
    st.image("Nexcomplylogo.png", use_container_width=True)
    st.subheader("Analysis Info")
    
    if 'selected_framework' in st.session_state:
        st.info(f"**Framework:** {st.session_state.selected_framework}")
    
    if 'selected_policies' in st.session_state:
        st.info(f"**Policies:** {len(st.session_state.selected_policies)}")
    
    if 'gap_results' in st.session_state:
        st.success(f"**Results:** {len(st.session_state.gap_results)} analyzed")
    
    st.markdown("---")
    
    st.subheader("Settings")
    
    if 'similarity_threshold' in st.session_state:
        st.text(f"Threshold: {st.session_state.similarity_threshold}")
    
    if 'enable_summarization' in st.session_state:
        st.text(f"Summarization: {'ON' if st.session_state.enable_summarization else 'OFF'}")

# Footer
st.markdown("---")
st.markdown(f"*Page loaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
