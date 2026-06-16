"""
Dashboard page - Main dashboard with visualizations
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from modules.database import NexcomplyDB
from modules.visualizations import (
    create_compliance_score_dashboard,
    create_gap_analysis_bar_chart,
    create_pie_chart,
    create_trend_chart,
    create_multi_metric_dashboard
)
from modules.auth import AuthManager
from modules.theme import apply_theme

# Page configuration
st.set_page_config(
    page_title="Dashboard - Nexcomply",
    layout="wide"
)

# Initialize
auth = AuthManager()
db = NexcomplyDB()

# Authentication check
if not auth.is_authenticated():
    st.warning("Please login to access the dashboard")
    auth.show_login_form()
    st.stop()

# Main content
st.title("Compliance Dashboard")
st.markdown("### Comprehensive compliance overview and visualizations")
st.markdown("---")

# Quick metrics
col1, col2, col3, col4 = st.columns(4)

stats = {}
try:
    stats = db.get_statistics()
    
    with col1:
        st.metric(
            "Total Documents",
            stats.get('total_documents', 0),
            delta=None
        )
    
    with col2:
        st.metric(
            "Total Analyses",
            stats.get('total_analyses', 0),
            delta=None
        )
    
    with col3:
        st.metric(
            "Total Reports",
            stats.get('total_reports', 0),
            delta=None
        )
    
    with col4:
        st.metric(
            "Active Users",
            stats.get('total_users', 0),
            delta=None
        )

except Exception as e:
    st.error(f"Error loading statistics: {str(e)}")

st.markdown("---")

# Main dashboard content
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview", 
    "Gap Analysis", 
    "Trends", 
    "Controls"
])

with tab1:
    st.subheader("Compliance Score Overview")
    
    # Compute real compliance score from analysis history
    try:
        _history = db.get_analysis_history(limit=500)
        if not _history.empty and 'gap_severity' in _history.columns:
            _total = len(_history)
            _compliant = _history['gap_severity'].isin(['None', 'Low']).sum()
            compliance_score = round((_compliant / _total * 100), 1) if _total > 0 else 0.0
        else:
            compliance_score = 0.0
    except Exception:
        compliance_score = 0.0
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        fig_gauge = create_compliance_score_dashboard(compliance_score)
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col2:
        # Multi-metric dashboard — compute critical gaps from the most recent
        # 50 records (current) vs the 50 records before that (previous).
        try:
            _history_all = db.get_analysis_history(limit=100)
            if not _history_all.empty and 'gap_severity' in _history_all.columns:
                _recent = _history_all.head(50)
                _previous = _history_all.tail(50)
                _critical_gaps = int((_recent['gap_severity'] == 'Critical').sum())
                _prev_critical_gaps = int((_previous['gap_severity'] == 'Critical').sum())
            else:
                _critical_gaps = 0
                _prev_critical_gaps = 0
        except Exception:
            _critical_gaps = 0
            _prev_critical_gaps = 0

        metrics = {
            'total_documents': stats.get('total_documents', 0),
            'compliance_score': compliance_score,
            'critical_gaps': _critical_gaps,
            'previous_critical_gaps': _prev_critical_gaps,
            'days_since_analysis': 7
        }
        
        fig_metrics = create_multi_metric_dashboard(metrics)
        st.plotly_chart(fig_metrics, use_container_width=True)
    
    st.markdown("---")
    
    # Recent analysis results
    st.subheader("Recent Analysis Results")
    
    try:
        analysis_history = db.get_analysis_history(limit=10)
        
        if not analysis_history.empty:
            # Display as table
            display_df = analysis_history[[
                'framework_name', 
                'similarity_score', 
                'gap_severity',
                'analysis_date'
            ]].copy()
            display_df['similarity_score'] = display_df['similarity_score'].round(2)
            display_df['analysis_date'] = pd.to_datetime(display_df['analysis_date']).dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No analysis results available yet. Run an analysis to see results here.")
    
    except Exception as e:
        st.error(f"Error loading analysis history: {str(e)}")

with tab2:
    st.subheader("Gap Analysis Breakdown")
    
    # Sample gap data
    gap_severity_data = {
        'Critical': 3,
        'High': 8,
        'Medium': 15,
        'Low': 10,
        'None': 25
    }
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Pie chart
        fig_pie = create_pie_chart(gap_severity_data)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Bar chart
        gap_data_bar = {
            'Access Control': 5,
            'Data Privacy': 8,
            'Network Security': 3,
            'Incident Response': 7,
            'Risk Management': 4
        }
        
        fig_bar = create_gap_analysis_bar_chart(gap_data_bar)
        st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown("---")
    
    # Gap details table
    st.subheader("Gap Details")
    
    gap_details_data = {
        'Severity': ['Critical', 'Critical', 'High', 'High', 'Medium'],
        'Category': ['Access Control', 'Encryption', 'Data Privacy', 'Logging', 'Training'],
        'Description': [
            'Multi-factor authentication not implemented',
            'Data at rest encryption missing',
            'Privacy policy needs updates',
            'Log retention period insufficient',
            'Annual security training not documented'
        ],
        'Similarity Score': [0.25, 0.28, 0.45, 0.48, 0.65]
    }
    
    gap_df = pd.DataFrame(gap_details_data)
    
    # Color code by severity
    def highlight_severity(row):
        if row['Severity'] == 'Critical':
            return ['background-color: #ffcccc'] * len(row)
        elif row['Severity'] == 'High':
            return ['background-color: #ffe6cc'] * len(row)
        elif row['Severity'] == 'Medium':
            return ['background-color: #ffffcc'] * len(row)
        else:
            return [''] * len(row)
    
    styled_df = gap_df.style.apply(highlight_severity, axis=1)
    st.dataframe(styled_df, use_container_width=True)

with tab3:
    st.subheader("Compliance Trend Analysis")
    
    # Sample trend data
    dates = pd.date_range(end=datetime.now(), periods=12, freq='M')
    scores = [65, 67, 70, 68, 72, 74, 73, 75, 76, 78, 76, 75.5]
    
    trend_data = pd.DataFrame({
        'date': dates,
        'score': scores
    })
    
    fig_trend = create_trend_chart(trend_data)
    st.plotly_chart(fig_trend, use_container_width=True)
    
    st.markdown("---")
    
    # Improvement recommendations
    st.subheader("Improvement Recommendations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Quick Wins (30 days):**
        - Implement MFA for all users
        - Update privacy policy documentation
        - Enable comprehensive logging
        """)
    
    with col2:
        st.markdown("""
        **Medium Term (90 days):**
        - Deploy data encryption at rest
        - Complete security awareness training
        - Update incident response procedures
        """)

with tab4:
    st.subheader("Control Implementation Status")
    
    # Sample control data
    from modules.visualizations import create_progress_bars
    
    controls_status = {
        'Access Control': 85,
        'Data Encryption': 65,
        'Network Security': 90,
        'Logging & Monitoring': 70,
        'Incident Response': 60,
        'Data Privacy': 75,
        'Physical Security': 95,
        'Business Continuity': 55
    }
    
    fig_progress = create_progress_bars(controls_status)
    st.plotly_chart(fig_progress, use_container_width=True)
    
    st.markdown("---")
    
    # Control details
    st.subheader("Control Details")
    
    control_details = {
        'Control': list(controls_status.keys()),
        'Status': [f"{v}%" for v in controls_status.values()],
        'Status_Label': ['Compliant' if v >= 80 else 'Partial' if v >= 50 else 'Non-Compliant' 
                        for v in controls_status.values()],
        'Last Review': ['2024-01-15'] * len(controls_status)
    }
    
    control_df = pd.DataFrame(control_details)
    st.dataframe(control_df, use_container_width=True)

# Filters sidebar
with st.sidebar:
    st.image("Nexcomplylogo.png", use_container_width=True)
    st.subheader("Filters")
    
    framework_filter = st.selectbox(
        "Framework",
        ["All Frameworks", "ISO 27001", "SOC 2", "NIST", "GDPR", "NRB"]
    )
    
    date_range = st.date_input(
        "Date Range",
        value=(datetime.now() - timedelta(days=30), datetime.now())
    )
    
    severity_filter = st.multiselect(
        "Gap Severity",
        ["Critical", "High", "Medium", "Low", "None"],
        default=["Critical", "High", "Medium"]
    )
    
    if st.button("Refresh Dashboard", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    
    # Export options
    st.subheader("Export")
    
    if st.button("Export Dashboard PDF", use_container_width=True):
        st.info("Dashboard export feature coming soon!")
    
    if st.button("Export Raw Data", use_container_width=True):
        st.info("Data export feature coming soon!")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>Last updated: {}</p>
</div>
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')), unsafe_allow_html=True)
