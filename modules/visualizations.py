"""
Visualizations module for Nexcomply application
Creates interactive charts and graphs using Plotly
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


def create_compliance_score_dashboard(compliance_score, target_score=85):
    """
    Create compliance score gauge chart
    
    Args:
        compliance_score: Current compliance score (0-100)
        target_score: Target compliance score
        
    Returns:
        plotly.graph_objects.Figure: Gauge chart
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=compliance_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Overall Compliance Score", 'font': {'size': 24}},
        delta={'reference': target_score, 'increasing': {'color': "green"}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 50], 'color': '#ffcccc'},
                {'range': [50, 75], 'color': '#ffffcc'},
                {'range': [75, 100], 'color': '#ccffcc'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': target_score
            }
        }
    ))
    
    fig.update_layout(height=400, font={'color': "darkblue", 'family': "Arial"})
    return fig


def create_gap_analysis_bar_chart(gap_data):
    """
    Create bar chart for gap analysis
    
    Args:
        gap_data: Dictionary or DataFrame with gap information
        
    Returns:
        plotly.graph_objects.Figure: Bar chart
    """
    if isinstance(gap_data, dict):
        categories = list(gap_data.keys())
        values = list(gap_data.values())
    elif isinstance(gap_data, pd.DataFrame):
        categories = gap_data['category'].tolist() if 'category' in gap_data.columns else gap_data.index.tolist()
        values = gap_data['count'].tolist() if 'count' in gap_data.columns else gap_data['value'].tolist()
    else:
        return go.Figure()
    
    fig = go.Figure([go.Bar(
        x=categories,
        y=values,
        marker_color='indianred',
        text=values,
        textposition='auto',
    )])
    
    fig.update_layout(
        title="Compliance Gaps by Category",
        xaxis_title="Category",
        yaxis_title="Number of Gaps",
        height=400,
        showlegend=False
    )
    
    return fig


def create_heatmap(coverage_data, frameworks, controls):
    """
    Create heatmap for control coverage across frameworks
    
    Args:
        coverage_data: 2D array or DataFrame of coverage values
        frameworks: List of framework names
        controls: List of control names
        
    Returns:
        plotly.graph_objects.Figure: Heatmap
    """
    if isinstance(coverage_data, pd.DataFrame):
        z_data = coverage_data.values
    else:
        z_data = coverage_data
    
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=frameworks,
        y=controls,
        colorscale='RdYlGn',
        text=z_data,
        texttemplate='%{text:.2f}',
        textfont={"size": 10},
        colorbar=dict(title="Coverage Score")
    ))
    
    fig.update_layout(
        title="Control Coverage Heatmap",
        xaxis_title="Frameworks",
        yaxis_title="Controls",
        height=500
    )
    
    return fig


def create_radar_chart(framework_scores):
    """
    Create radar chart for multi-framework comparison
    
    Args:
        framework_scores: Dictionary of {framework_name: score}
        
    Returns:
        plotly.graph_objects.Figure: Radar chart
    """
    frameworks = list(framework_scores.keys())
    scores = list(framework_scores.values())
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=scores,
        theta=frameworks,
        fill='toself',
        name='Compliance Score',
        line_color='blue'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=False,
        title="Multi-Framework Compliance Comparison",
        height=500
    )
    
    return fig


def create_trend_chart(trend_data):
    """
    Create line chart for compliance trend over time
    
    Args:
        trend_data: DataFrame with 'date' and 'score' columns
        
    Returns:
        plotly.graph_objects.Figure: Line chart
    """
    fig = go.Figure()
    
    if isinstance(trend_data, pd.DataFrame):
        fig.add_trace(go.Scatter(
            x=trend_data['date'] if 'date' in trend_data.columns else trend_data.index,
            y=trend_data['score'] if 'score' in trend_data.columns else trend_data.values,
            mode='lines+markers',
            name='Compliance Score',
            line=dict(color='royalblue', width=3),
            marker=dict(size=8)
        ))
    
    fig.update_layout(
        title="Compliance Score Trend",
        xaxis_title="Date",
        yaxis_title="Compliance Score (%)",
        height=400,
        hovermode='x unified'
    )
    
    return fig


def create_pie_chart(gap_severity_data):
    """
    Create pie chart for gap distribution by severity
    
    Args:
        gap_severity_data: Dictionary of {severity: count}
        
    Returns:
        plotly.graph_objects.Figure: Pie chart
    """
    labels = list(gap_severity_data.keys())
    values = list(gap_severity_data.values())
    
    colors = {
        'Critical': '#ff0000',
        'High': '#ff6600',
        'Medium': '#ffcc00',
        'Low': '#99cc00',
        'None': '#00cc00'
    }
    
    pie_colors = [colors.get(label, '#cccccc') for label in labels]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.3,
        marker_colors=pie_colors,
        textinfo='label+percent',
        textposition='auto'
    )])
    
    fig.update_layout(
        title="Gap Distribution by Severity",
        height=400
    )
    
    return fig


def create_sankey_diagram(requirements, controls, flows):
    """
    Create Sankey diagram for requirement to control flow
    
    Args:
        requirements: List of requirement names
        controls: List of control names
        flows: List of (source_idx, target_idx, value) tuples
        
    Returns:
        plotly.graph_objects.Figure: Sankey diagram
    """
    all_nodes = requirements + controls
    
    # Adjust target indices to account for requirements
    adjusted_flows = []
    for source, target, value in flows:
        adjusted_target = target + len(requirements)
        adjusted_flows.append((source, adjusted_target, value))
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_nodes,
            color="blue"
        ),
        link=dict(
            source=[flow[0] for flow in adjusted_flows],
            target=[flow[1] for flow in adjusted_flows],
            value=[flow[2] for flow in adjusted_flows]
        )
    )])
    
    fig.update_layout(
        title="Requirements to Controls Flow",
        height=600,
        font_size=10
    )
    
    return fig


def create_progress_bars(controls_status):
    """
    Create horizontal progress bars for individual controls
    
    Args:
        controls_status: Dictionary of {control_name: completion_percentage}
        
    Returns:
        plotly.graph_objects.Figure: Bar chart with progress bars
    """
    controls = list(controls_status.keys())
    completion = list(controls_status.values())
    
    # Color based on completion
    colors = ['#00cc00' if c >= 80 else '#ffcc00' if c >= 50 else '#ff6600' for c in completion]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=controls,
        x=completion,
        orientation='h',
        marker=dict(color=colors),
        text=[f"{c}%" for c in completion],
        textposition='auto',
    ))
    
    fig.update_layout(
        title="Control Implementation Status",
        xaxis=dict(title="Completion (%)", range=[0, 100]),
        yaxis_title="Controls",
        height=max(400, len(controls) * 30),
        showlegend=False
    )
    
    return fig


def create_multi_metric_dashboard(metrics):
    """
    Create dashboard with multiple metrics
    
    Args:
        metrics: Dictionary of metric values
        
    Returns:
        plotly.graph_objects.Figure: Dashboard with multiple indicators
    """
    fig = make_subplots(
        rows=2, cols=2,
        specs=[[{"type": "indicator"}, {"type": "indicator"}],
               [{"type": "indicator"}, {"type": "indicator"}]],
        subplot_titles=("Total Documents", "Compliance Score", 
                       "Critical Gaps", "Last Analysis")
    )
    
    # Total Documents
    fig.add_trace(go.Indicator(
        mode="number",
        value=metrics.get('total_documents', 0),
        title={"text": "Documents"},
        number={'font': {'size': 40}}
    ), row=1, col=1)
    
    # Compliance Score
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=metrics.get('compliance_score', 0),
        gauge={'axis': {'range': [0, 100]},
               'bar': {'color': "darkblue"},
               'steps': [
                   {'range': [0, 50], 'color': "lightgray"},
                   {'range': [50, 75], 'color': "gray"}
               ]},
        title={"text": "Score"}
    ), row=1, col=2)
    
    # Critical Gaps
    fig.add_trace(go.Indicator(
        mode="number+delta",
        value=metrics.get('critical_gaps', 0),
        delta={'reference': metrics.get('previous_critical_gaps', 0)},
        title={"text": "Critical"},
        number={'font': {'size': 40}}
    ), row=2, col=1)
    
    # Last Analysis
    fig.add_trace(go.Indicator(
        mode="number",
        value=metrics.get('days_since_analysis', 0),
        title={"text": "Days Ago"},
        number={'suffix': " days", 'font': {'size': 30}}
    ), row=2, col=2)
    
    fig.update_layout(height=500, title_text="Compliance Overview Dashboard")
    
    return fig


def create_severity_distribution_chart(severity_counts):
    """
    Create stacked bar chart for severity distribution
    
    Args:
        severity_counts: DataFrame with severity counts
        
    Returns:
        plotly.graph_objects.Figure: Stacked bar chart
    """
    fig = go.Figure()
    
    severities = ['Critical', 'High', 'Medium', 'Low', 'None']
    colors = ['#ff0000', '#ff6600', '#ffcc00', '#99cc00', '#00cc00']
    
    for severity, color in zip(severities, colors):
        if severity in severity_counts:
            fig.add_trace(go.Bar(
                name=severity,
                x=['Gaps'],
                y=[severity_counts[severity]],
                marker_color=color,
                text=[severity_counts[severity]],
                textposition='inside'
            ))
    
    fig.update_layout(
        title="Gap Severity Distribution",
        barmode='stack',
        height=400,
        showlegend=True,
        yaxis_title="Count"
    )
    
    return fig
