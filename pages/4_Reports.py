"""
Reports page - Report generation and export
"""

import streamlit as st
import os
from datetime import datetime
from modules.database import NexcomplyDB
from modules.report_generator import ReportGenerator, create_sample_report_data
from modules.gap_detector import GapDetector
from modules.auth import AuthManager, get_current_username
from modules.theme import apply_theme

# Page configuration
st.set_page_config(
    page_title="Reports - Nexcomply",
    layout="wide"
)

# Initialize
auth = AuthManager()
db = NexcomplyDB()
report_gen = ReportGenerator()

# Authentication check
if not auth.is_authenticated():
    st.warning("Please login to generate reports")
    auth.show_login_form()
    st.stop()

# Main content
st.title("Compliance Reports")
st.markdown("### Generate and manage compliance reports")
st.markdown("---")

# Tabs
tab1, tab2, tab3 = st.tabs([
    "Generate New Report",
    "Historical Reports",
    "Report Settings"
])

with tab1:
    st.subheader("Generate New Compliance Report")
    
    # Check if analysis results exist
    if 'gap_results' in st.session_state and st.session_state.gap_results:
        st.success("Analysis results available for report generation")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Report configuration
            st.markdown("### Report Configuration")
            
            report_title = st.text_input(
                "Report Title",
                value=f"Compliance Gap Analysis Report - {datetime.now().strftime('%Y-%m-%d')}"
            )
            
            framework_name = st.text_input(
                "Framework Name",
                value=st.session_state.get('selected_framework', 'ISO 27001')
            )
            
            executive_summary = st.text_area(
                "Executive Summary (Optional)",
                value="This report provides a comprehensive analysis of compliance gaps identified during the assessment.",
                height=100
            )
            
            report_formats = st.multiselect(
                "Export Formats",
                ["PDF", "Excel", "HTML"],
                default=["PDF"]
            )
            
            include_charts = st.checkbox(
                "Include Charts and Visualizations",
                value=True
            )
        
        with col2:
            st.markdown("### Report Preview")
            
            # Calculate statistics
            gap_results = st.session_state.gap_results
            total_reqs = len(gap_results)
            
            severity_counts = {}
            for result in gap_results:
                severity = result['gap_severity']
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            gaps_found = sum(1 for r in gap_results if r['gap_exists'])
            compliance_pct = ((total_reqs - gaps_found) / total_reqs * 100) if total_reqs > 0 else 0
            
            st.metric("Requirements Analyzed", total_reqs)
            st.metric("Gaps Identified", gaps_found)
            st.metric("Compliance Score", f"{compliance_pct:.1f}%")
            
            st.markdown("**Gap Severity:**")
            for severity in ['Critical', 'High', 'Medium', 'Low', 'None']:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    st.text(f"{severity}: {count}")
        
        st.markdown("---")
        
        # Generate report button
        if st.button("Generate Report", type="primary", use_container_width=True):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("Preparing report data...")
                progress_bar.progress(0.2)
                
                # Prepare gap summary
                gap_summary = {
                    'total_gaps': total_reqs,
                    'critical_gaps': severity_counts.get('Critical', 0),
                    'high_gaps': severity_counts.get('High', 0),
                    'medium_gaps': severity_counts.get('Medium', 0),
                    'low_gaps': severity_counts.get('Low', 0),
                    'no_gaps': severity_counts.get('None', 0),
                    'compliance_percentage': compliance_pct
                }
                
                # Create report data
                report_data = create_sample_report_data(
                    gap_summary,
                    gap_results,
                    framework_name
                )
                
                # Update with custom values
                report_data['title'] = report_title
                report_data['executive_summary'] = executive_summary
                report_data['generated_by'] = get_current_username()
                
                progress_bar.progress(0.4)
                
                # Generate reports in selected formats
                generated_files = {}
                
                if "PDF" in report_formats:
                    status_text.text("Generating PDF report...")
                    progress_bar.progress(0.5)
                    
                    pdf_path = report_gen.generate_pdf_report(report_data)
                    generated_files['PDF'] = pdf_path
                
                if "Excel" in report_formats:
                    status_text.text("Generating Excel report...")
                    progress_bar.progress(0.7)
                    
                    excel_path = report_gen.generate_excel_report(gap_results)
                    generated_files['Excel'] = excel_path
                
                if "HTML" in report_formats:
                    status_text.text("Generating HTML report...")
                    progress_bar.progress(0.9)
                    
                    html_path = report_gen.generate_html_report(report_data)
                    generated_files['HTML'] = html_path
                
                # Save to database
                for format_type, file_path in generated_files.items():
                    db.save_report(
                        report_name=report_title,
                        report_type=format_type,
                        generated_by=get_current_username(),
                        file_path=file_path
                    )
                
                # Log activity
                db.log_activity(
                    get_current_username(),
                    "Report Generation",
                    f"Generated {len(generated_files)} report(s)"
                )
                
                progress_bar.progress(1.0)
                status_text.text("Report generation complete!")
                
                st.success(f"Successfully generated {len(generated_files)} report(s)!")
                
                # Download buttons
                st.markdown("### Download Reports")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if 'PDF' in generated_files:
                        with open(generated_files['PDF'], 'rb') as f:
                            st.download_button(
                                "Download PDF",
                                f,
                                file_name=os.path.basename(generated_files['PDF']),
                                mime="application/pdf",
                                use_container_width=True
                            )
                
                with col2:
                    if 'Excel' in generated_files:
                        with open(generated_files['Excel'], 'rb') as f:
                            st.download_button(
                                "Download Excel",
                                f,
                                file_name=os.path.basename(generated_files['Excel']),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                
                with col3:
                    if 'HTML' in generated_files:
                        with open(generated_files['HTML'], 'r') as f:
                            st.download_button(
                                "Download HTML",
                                f.read(),
                                file_name=os.path.basename(generated_files['HTML']),
                                mime="text/html",
                                use_container_width=True
                            )
                
            except Exception as e:
                st.error(f"Error generating report: {str(e)}")
                st.exception(e)
    
    else:
        st.warning("No analysis results available")
        st.info("Please run a gap analysis first in the Analysis page before generating reports.")
        
        if st.button("Go to Analysis Page"):
            st.switch_page("pages/3_Analysis.py")

with tab2:
    st.subheader("Historical Reports")
    
    try:
        reports_df = db.get_all_reports()
        
        if not reports_df.empty:
            # Display reports
            st.dataframe(reports_df, use_container_width=True)
            
            st.markdown("---")
            
            # Reports summary
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Reports", len(reports_df))
            
            with col2:
                pdf_count = len(reports_df[reports_df['report_type'] == 'PDF'])
                st.metric("PDF Reports", pdf_count)
            
            with col3:
                recent_reports = len(reports_df[
                    reports_df['generation_date'] >= datetime.now().strftime('%Y-%m-%d')
                ])
                st.metric("Today's Reports", recent_reports)
            
            # View/Download historical reports
            st.markdown("---")
            st.subheader("View Historical Reports")
            
            report_list = reports_df['report_name'].tolist()
            selected_report = st.selectbox("Select Report", report_list)
            
            if selected_report:
                report_row = reports_df[reports_df['report_name'] == selected_report].iloc[0]
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.info(f"**Report:** {report_row['report_name']}")
                    st.info(f"**Type:** {report_row['report_type']}")
                    st.info(f"**Generated:** {report_row['generation_date']}")
                    st.info(f"**By:** {report_row['generated_by']}")
                
                with col2:
                    file_path = report_row['file_path']
                    
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            st.download_button(
                                "Download",
                                f,
                                file_name=os.path.basename(file_path),
                                mime="application/pdf" if report_row['report_type'] == 'PDF' else "application/octet-stream",
                                use_container_width=True
                            )
                    else:
                        st.warning("File not found")
        
        else:
            st.info("No historical reports found")
    
    except Exception as e:
        st.error(f"Error loading historical reports: {str(e)}")

with tab3:
    st.subheader("Report Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Default Report Settings")
        
        default_format = st.selectbox(
            "Default Export Format",
            ["PDF", "Excel", "HTML", "All"]
        )
        
        default_include_charts = st.checkbox(
            "Include Charts by Default",
            value=True
        )
        
        company_name = st.text_input(
            "Company Name",
            value="Nexcomply"
        )
        
        company_logo = st.file_uploader(
            "Company Logo (Optional)",
            type=["png", "jpg", "jpeg"]
        )
        
        if st.button("Save Settings", use_container_width=True):
            # Save settings to database
            db.set_config('default_report_format', default_format, get_current_username())
            db.set_config('include_charts', str(default_include_charts), get_current_username())
            db.set_config('company_name', company_name, get_current_username())
            
            st.success("Settings saved successfully!")
    
    with col2:
        st.markdown("### Report Templates")
        
        st.info("""
        **Available Templates:**
        
        1. **Executive Summary**
           - High-level overview
           - Key metrics
           - Critical gaps only
        
        2. **Detailed Analysis**
           - Complete gap analysis
           - Recommendations
           - Action items
        
        3. **Technical Report**
           - Technical details
           - Implementation guide
           - Code references
        
        4. **Compliance Audit**
           - Audit findings
           - Evidence
           - Compliance status
        """)
        
        template_selection = st.selectbox(
            "Select Template",
            ["Standard Report", "Executive Summary", "Detailed Analysis", "Technical Report", "Compliance Audit"]
        )
        
        if st.button("Apply Template", use_container_width=True):
            st.info(f"Template '{template_selection}' will be applied to next report")
    


# Sidebar
with st.sidebar:
    st.image("Nexcomplylogo.png", use_container_width=True)
    st.subheader("Report Statistics")
    
    try:
        reports_df = db.get_all_reports()
        
        if not reports_df.empty:
            st.metric("Total Reports", len(reports_df))
            
            # Reports by type
            st.markdown("**By Type:**")
            type_counts = reports_df['report_type'].value_counts()
            for report_type, count in type_counts.items():
                st.text(f"{report_type}: {count}")
        else:
            st.info("No reports generated yet")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    st.subheader("Tips")
    
    st.info("""
    **Report Best Practices:**
    
    - Run analysis before generating reports
    - Include executive summary
    - Export multiple formats
    - Save reports regularly
    - Review before sharing
    """)

# Footer
st.markdown("---")
st.markdown(f"*Page loaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
