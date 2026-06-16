"""
Theme utilities for Nexcomply application
"""

import streamlit as st


def apply_theme():
    """Apply light mode theme styling"""
    st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
