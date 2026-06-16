# Nexcomply v2.0 - Enhanced Compliance Analysis System

A comprehensive compliance analysis system that helps organizations identify and address compliance gaps through automated analysis, AI-powered summarization, and intelligent gap detection.

## Features

### Complete Compliance Workflow

1. **Document Parsing**
   - Parse PDF documents (compliance frameworks, policies)
   - Parse Excel files (questionnaires, knowledge library)
   - Extract text from images using OCR
   - Support multiple document formats
   - Handle batch document uploads

2. **Summarization**
   - Summarize extracted documents using T5 model
   - Generate concise summaries for frameworks
   - Create policy summaries
   - Provide multi-level summarization (detailed, brief, executive)

3. **Embedding Generator**
   - Generate embeddings using Sentence-BERT
   - Create vector representations for compliance requirements and policies
   - Store embeddings for comparison

4. **Gap Identification**
   - Compare embeddings using cosine similarity
   - Identify compliance gaps between framework requirements and internal policies
   - Assign gap severity levels (Critical, High, Medium, Low)
   - Provide gap scores with thresholds

5. **Report Generation**
   - Generate comprehensive compliance reports in PDF format
   - Include executive summary, detailed gap analysis, and recommendations
   - Export reports in multiple formats (PDF, Excel, HTML)

6. **Graphs and Charts Visualization**
   - Compliance Score Dashboard
   - Gap Analysis Bar Chart
   - Heatmap for control coverage
   - Radar Chart for multi-framework comparison
   - Trend Line Chart
   - Pie Chart for gap distribution
   - Progress Bars for control implementation

7. **Admin Panel**
   - User management with role-based access control
   - Document management
   - Configuration settings
   - Analytics dashboard
   - Activity logs

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Tesseract OCR (for image text extraction)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/Alex-Suwal/Nexcomply-v2.0-Enhanced-Compliance-Analysis-System.git
   cd Nexcomply-v2.0-Enhanced-Compliance-Analysis-System
