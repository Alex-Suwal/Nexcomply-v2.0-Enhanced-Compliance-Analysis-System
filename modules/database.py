"""
Database module for Nexcomply application
Handles all database operations using SQLite
"""

import sqlite3
import os
from datetime import datetime
import pandas as pd
import bcrypt


class NexcomplyDB:
    def __init__(self, db_path="data/nexcomply.db"):
        """Initialize database connection"""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                category TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploaded_by TEXT,
                file_size INTEGER,
                status TEXT DEFAULT 'active',
                version INTEGER DEFAULT 1
            )
        ''')
        
        # Analysis results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                framework_name TEXT NOT NULL,
                policy_name TEXT,
                similarity_score REAL,
                gap_severity TEXT,
                gap_description TEXT,
                recommendations TEXT,
                analyzed_by TEXT
            )
        ''')
        
        # Reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_name TEXT NOT NULL,
                report_type TEXT NOT NULL,
                generation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                generated_by TEXT,
                file_path TEXT,
                status TEXT DEFAULT 'completed'
            )
        ''')
        
        # Configuration table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT
            )
        ''')
        
        # Activity logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                username TEXT,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT
            )
        ''')
        
        # Knowledge Library table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_library (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                framework TEXT,
                control_id TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Batch jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batch_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_name TEXT NOT NULL,
                job_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                documents TEXT,
                framework TEXT,
                schedule_type TEXT,
                schedule_time TEXT,
                notify_email TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                result_summary TEXT,
                error_message TEXT
            )
        ''')
        
        conn.commit()
        
        # Create default admin user if not exists
        self.create_default_admin()
        
        conn.close()
    
    def create_default_admin(self):
        """Create default admin user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, email) VALUES (?, ?, ?, ?)",
                ("admin", password_hash, "Admin", "admin@nexcomply.com")
            )
            conn.commit()
        
        conn.close()
    
    # User Management
    def authenticate_user(self, username, password):
        """Authenticate user credentials"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT password_hash, role, is_active FROM users WHERE username = ?",
            (username,)
        )
        result = cursor.fetchone()
        
        if result and result[2]:  # Check if user is active
            password_hash = result[0]
            if bcrypt.checkpw(password.encode('utf-8'), password_hash):
                # Update last login
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE username = ?",
                    (datetime.now(), username)
                )
                conn.commit()
                conn.close()
                return True, result[1]  # Return authentication status and role
        
        conn.close()
        return False, None
    
    def add_user(self, username, password, role, email=None):
        """Add new user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, email) VALUES (?, ?, ?, ?)",
                (username, password_hash, role, email)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def get_all_users(self):
        """Get all users"""
        conn = self.get_connection()
        df = pd.read_sql_query(
            "SELECT id, username, role, email, created_at, last_login, is_active FROM users",
            conn
        )
        conn.close()
        return df
    
    def update_user(self, user_id, **kwargs):
        """Update user information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        allowed_fields = ['role', 'email', 'is_active']
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if updates:
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        conn.close()
    
    def delete_user(self, user_id):
        """Delete user (soft delete)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
    
    # Document Management
    def add_document(self, filename, file_type, category, uploaded_by, file_size):
        """Add document record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO documents (filename, file_type, category, uploaded_by, file_size) VALUES (?, ?, ?, ?, ?)",
            (filename, file_type, category, uploaded_by, file_size)
        )
        conn.commit()
        doc_id = cursor.lastrowid
        conn.close()
        return doc_id
    
    def get_all_documents(self):
        """Get all documents"""
        conn = self.get_connection()
        df = pd.read_sql_query(
            "SELECT * FROM documents WHERE status = 'active' ORDER BY upload_date DESC",
            conn
        )
        conn.close()
        return df
    
    def delete_document(self, doc_id):
        """Delete document (soft delete)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE documents SET status = 'deleted' WHERE id = ?", (doc_id,))
        conn.commit()
        conn.close()
    
    # Analysis Results
    def save_analysis_result(self, framework_name, policy_name, similarity_score, 
                            gap_severity, gap_description, recommendations, analyzed_by):
        """Save analysis result"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO analysis_results 
               (framework_name, policy_name, similarity_score, gap_severity, 
                gap_description, recommendations, analyzed_by) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (framework_name, policy_name, similarity_score, gap_severity, 
             gap_description, recommendations, analyzed_by)
        )
        conn.commit()
        result_id = cursor.lastrowid
        conn.close()
        return result_id
    
    def get_analysis_history(self, limit=50):
        """Get analysis history"""
        conn = self.get_connection()
        df = pd.read_sql_query(
            f"SELECT * FROM analysis_results ORDER BY analysis_date DESC LIMIT {limit}",
            conn
        )
        conn.close()
        return df
    
    # Reports Management
    def save_report(self, report_name, report_type, generated_by, file_path):
        """Save report record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO reports (report_name, report_type, generated_by, file_path) VALUES (?, ?, ?, ?)",
            (report_name, report_type, generated_by, file_path)
        )
        conn.commit()
        report_id = cursor.lastrowid
        conn.close()
        return report_id
    
    def get_all_reports(self):
        """Get all reports"""
        conn = self.get_connection()
        df = pd.read_sql_query(
            "SELECT * FROM reports ORDER BY generation_date DESC",
            conn
        )
        conn.close()
        return df
    
    # Activity Logging
    def log_activity(self, username, action, details=None, ip_address=None):
        """Log user activity"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO activity_logs (username, action, details, ip_address) VALUES (?, ?, ?, ?)",
            (username, action, details, ip_address)
        )
        conn.commit()
        conn.close()
    
    def get_activity_logs(self, limit=100):
        """Get activity logs"""
        conn = self.get_connection()
        df = pd.read_sql_query(
            f"SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT {limit}",
            conn
        )
        conn.close()
        return df
    
    # Configuration Management
    def set_config(self, config_key, config_value, updated_by):
        """Set configuration value"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT OR REPLACE INTO configuration (config_key, config_value, updated_by, updated_at) 
               VALUES (?, ?, ?, ?)""",
            (config_key, config_value, updated_by, datetime.now())
        )
        conn.commit()
        conn.close()
    
    def get_config(self, config_key, default=None):
        """Get configuration value"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT config_value FROM configuration WHERE config_key = ?", (config_key,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else default
    
    # Analytics
    def get_statistics(self):
        """Get system statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total users
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        stats['total_users'] = cursor.fetchone()[0]
        
        # Total documents
        cursor.execute("SELECT COUNT(*) FROM documents WHERE status = 'active'")
        stats['total_documents'] = cursor.fetchone()[0]
        
        # Total analyses
        cursor.execute("SELECT COUNT(*) FROM analysis_results")
        stats['total_analyses'] = cursor.fetchone()[0]
        
        # Total reports
        cursor.execute("SELECT COUNT(*) FROM reports")
        stats['total_reports'] = cursor.fetchone()[0]
        
        # Recent activity count (last 24 hours)
        cursor.execute(
            "SELECT COUNT(*) FROM activity_logs WHERE timestamp > datetime('now', '-1 day')"
        )
        stats['recent_activities'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    # Knowledge Library Management
    def add_kl_entry(self, title, category, content, tags, framework, control_id, created_by):
        """Add knowledge library entry"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO knowledge_library 
               (title, category, content, tags, framework, control_id, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, category, content, tags, framework, control_id, created_by)
        )
        conn.commit()
        entry_id = cursor.lastrowid
        conn.close()
        return entry_id
    
    def get_kl_entries(self, category=None, framework=None, search_term=None):
        """Get knowledge library entries with optional filters"""
        conn = self.get_connection()
        
        query = "SELECT * FROM knowledge_library WHERE is_active = 1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        if framework:
            query += " AND framework = ?"
            params.append(framework)
        if search_term:
            query += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
            params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
        
        query += " ORDER BY created_at DESC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    
    def update_kl_entry(self, entry_id, title, category, content, tags, framework, control_id):
        """Update knowledge library entry"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """UPDATE knowledge_library 
               SET title=?, category=?, content=?, tags=?, framework=?, control_id=?, updated_at=?
               WHERE id=?""",
            (title, category, content, tags, framework, control_id, datetime.now(), entry_id)
        )
        conn.commit()
        conn.close()
    
    def delete_kl_entry(self, entry_id):
        """Soft delete knowledge library entry"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE knowledge_library SET is_active = 0 WHERE id = ?", (entry_id,))
        conn.commit()
        conn.close()
    
    # Batch Jobs Management
    def create_batch_job(self, job_name, job_type, documents, framework, 
                         schedule_type, schedule_time, notify_email, created_by):
        """Create a batch job"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO batch_jobs 
               (job_name, job_type, documents, framework, schedule_type, schedule_time, 
                notify_email, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_name, job_type, documents, framework, schedule_type, schedule_time,
             notify_email, created_by)
        )
        conn.commit()
        job_id = cursor.lastrowid
        conn.close()
        return job_id
    
    def update_batch_job_status(self, job_id, status, result_summary=None, error_message=None):
        """Update batch job status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status == 'running':
            cursor.execute(
                "UPDATE batch_jobs SET status=?, started_at=? WHERE id=?",
                (status, datetime.now(), job_id)
            )
        elif status in ('completed', 'failed'):
            cursor.execute(
                """UPDATE batch_jobs SET status=?, completed_at=?, 
                   result_summary=?, error_message=? WHERE id=?""",
                (status, datetime.now(), result_summary, error_message, job_id)
            )
        else:
            cursor.execute("UPDATE batch_jobs SET status=? WHERE id=?", (status, job_id))
        
        conn.commit()
        conn.close()
    
    def get_batch_jobs(self, created_by=None):
        """Get batch jobs"""
        conn = self.get_connection()
        query = "SELECT * FROM batch_jobs"
        params = []
        if created_by:
            query += " WHERE created_by = ?"
            params.append(created_by)
        query += " ORDER BY created_at DESC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
