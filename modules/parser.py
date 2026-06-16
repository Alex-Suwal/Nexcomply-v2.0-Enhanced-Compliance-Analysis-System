"""
Document parser module for Nexcomply application
Handles parsing of PDF, Excel, and image files
"""

import pdfplumber
import pytesseract
from PIL import Image
import pandas as pd
import os
import io


class DocumentParser:
    """Class to handle document parsing operations"""
    
    @staticmethod
    def extract_pdf_text(pdf_file):
        """
        Extract text from PDF file
        
        Args:
            pdf_file: File object or path to PDF
            
        Returns:
            str: Extracted text from PDF
        """
        try:
            with pdfplumber.open(pdf_file) as pdf:
                text = ''
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
            return text
        except Exception as e:
            return f"Error extracting PDF text: {str(e)}"
    
    @staticmethod
    def extract_image_text(image_file):
        """
        Extract text from image using OCR
        
        Args:
            image_file: File object or path to image
            
        Returns:
            str: Extracted text from image
        """
        try:
            img = Image.open(image_file)
            text = pytesseract.image_to_string(img)
            return text
        except Exception as e:
            return f"Error extracting image text: {str(e)}"
    
    @staticmethod
    def parse_excel(excel_file):
        """
        Parse Excel file
        
        Args:
            excel_file: File object or path to Excel file
            
        Returns:
            pd.DataFrame: Parsed Excel data
        """
        try:
            df = pd.read_excel(excel_file)
            return df
        except Exception as e:
            return f"Error parsing Excel file: {str(e)}"
    
    @staticmethod
    def parse_excel_all_sheets(excel_file):
        """
        Parse all sheets from Excel file
        
        Args:
            excel_file: File object or path to Excel file
            
        Returns:
            dict: Dictionary of DataFrames (sheet_name: DataFrame)
        """
        try:
            all_sheets = pd.read_excel(excel_file, sheet_name=None)
            return all_sheets
        except Exception as e:
            return {"error": f"Error parsing Excel file: {str(e)}"}
    
    @staticmethod
    def preprocess_text(text):
        """
        Preprocess extracted text
        
        Args:
            text: Raw text string
            
        Returns:
            str: Preprocessed text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Convert to lowercase (optional)
        # text = text.lower()
        
        return text
    
    @staticmethod
    def batch_parse_pdfs(folder_path):
        """
        Parse all PDF files in a folder
        
        Args:
            folder_path: Path to folder containing PDFs
            
        Returns:
            dict: Dictionary of {filename: extracted_text}
        """
        parsed_docs = {}
        
        if not os.path.exists(folder_path):
            return parsed_docs
        
        for filename in os.listdir(folder_path):
            if filename.endswith('.pdf'):
                filepath = os.path.join(folder_path, filename)
                try:
                    text = DocumentParser.extract_pdf_text(filepath)
                    parsed_docs[filename] = text
                except Exception as e:
                    parsed_docs[filename] = f"Error: {str(e)}"
        
        return parsed_docs
    
    @staticmethod
    def batch_parse_excel(folder_path):
        """
        Parse all Excel files in a folder
        
        Args:
            folder_path: Path to folder containing Excel files
            
        Returns:
            dict: Dictionary of {filename: DataFrame}
        """
        parsed_files = {}
        
        if not os.path.exists(folder_path):
            return parsed_files
        
        for filename in os.listdir(folder_path):
            if filename.endswith(('.xlsx', '.xls')):
                filepath = os.path.join(folder_path, filename)
                try:
                    df = DocumentParser.parse_excel(filepath)
                    parsed_files[filename] = df
                except Exception as e:
                    parsed_files[filename] = f"Error: {str(e)}"
        
        return parsed_files
    
    @staticmethod
    def extract_text_from_uploaded_file(uploaded_file):
        """
        Extract text from Streamlit uploaded file
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            
        Returns:
            str or pd.DataFrame: Extracted content
        """
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        try:
            if file_extension == 'pdf':
                return DocumentParser.extract_pdf_text(uploaded_file)
            elif file_extension in ['xlsx', 'xls']:
                return DocumentParser.parse_excel(uploaded_file)
            elif file_extension in ['png', 'jpg', 'jpeg', 'bmp', 'tiff']:
                return DocumentParser.extract_image_text(uploaded_file)
            else:
                return f"Unsupported file type: {file_extension}"
        except Exception as e:
            return f"Error processing file: {str(e)}"
    
    @staticmethod
    def get_file_metadata(uploaded_file):
        """
        Get metadata from uploaded file
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            
        Returns:
            dict: File metadata
        """
        return {
            'filename': uploaded_file.name,
            'file_type': uploaded_file.type,
            'file_size': uploaded_file.size,
            'file_extension': uploaded_file.name.split('.')[-1].lower()
        }


def load_frameworks(frameworks_folder):
    """
    Load compliance frameworks from folder
    
    Args:
        frameworks_folder: Path to frameworks folder
        
    Returns:
        dict: Dictionary of frameworks
    """
    parser = DocumentParser()
    frameworks = {}
    
    if not os.path.exists(frameworks_folder):
        return frameworks
    
    for filename in os.listdir(frameworks_folder):
        filepath = os.path.join(frameworks_folder, filename)
        
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            try:
                all_sheets = pd.read_excel(filepath, sheet_name=None)
                for sheet_name, sheet_df in all_sheets.items():
                    # Avoid overwriting if another file has the same sheet name
                    key = sheet_name if sheet_name not in frameworks else f"{sheet_name} ({filename})"
                    frameworks[key] = sheet_df
            except Exception as e:
                frameworks[filename] = f"Error: {str(e)}"
        elif filename.endswith('.pdf'):
            try:
                text = parser.extract_pdf_text(filepath)
                # Use filename without extension as the framework key
                base_key = os.path.splitext(filename)[0]
                key = base_key
                counter = 2
                while key in frameworks:
                    key = f"{base_key} ({counter})"
                    counter += 1
                frameworks[key] = text
            except Exception as e:
                frameworks[filename] = f"Error: {str(e)}"
    
    return frameworks


def load_policies(policies_folder):
    """
    Load internal policies from folder
    
    Args:
        policies_folder: Path to policies folder
        
    Returns:
        dict: Dictionary of policies
    """
    parser = DocumentParser()
    policies = {}
    
    if not os.path.exists(policies_folder):
        return policies
    
    for filename in os.listdir(policies_folder):
        if filename.endswith('.pdf'):
            filepath = os.path.join(policies_folder, filename)
            try:
                text = parser.extract_pdf_text(filepath)
                policies[filename] = text
            except Exception as e:
                policies[filename] = f"Error: {str(e)}"
    
    return policies


def load_knowledge_library(kl_folder):
    """
    Load knowledge library from folder
    
    Args:
        kl_folder: Path to knowledge library folder
        
    Returns:
        pd.DataFrame: Combined knowledge library data
    """
    parser = DocumentParser()
    combined_kl = pd.DataFrame()
    
    if not os.path.exists(kl_folder):
        return combined_kl
    
    for filename in os.listdir(kl_folder):
        if filename.endswith(('.xlsx', '.xls')):
            filepath = os.path.join(kl_folder, filename)
            try:
                df = parser.parse_excel(filepath)
                combined_kl = pd.concat([combined_kl, df], ignore_index=True)
            except Exception as e:
                print(f"Error loading {filename}: {str(e)}")
    
    return combined_kl
