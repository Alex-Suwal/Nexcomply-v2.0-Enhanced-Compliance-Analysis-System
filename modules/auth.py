"""
Authentication module for Nexcomply application
Handles user authentication and session management
"""

import streamlit as st
from modules.database import NexcomplyDB
from datetime import datetime, timedelta


class AuthManager:
    """Class to manage authentication"""
    
    def __init__(self):
        """Initialize authentication manager"""
        self.db = NexcomplyDB()
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state variables"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'username' not in st.session_state:
            st.session_state.username = None
        if 'role' not in st.session_state:
            st.session_state.role = None
        if 'login_time' not in st.session_state:
            st.session_state.login_time = None
    
    def login(self, username, password):
        """
        Authenticate user
        
        Args:
            username: Username
            password: Password
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not username or not password:
            return False, "Please enter username and password"
        
        # Authenticate with database
        authenticated, role = self.db.authenticate_user(username, password)
        
        if authenticated:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.role = role
            st.session_state.login_time = datetime.now()
            
            # Log activity
            self.db.log_activity(username, "Login", "User logged in successfully")
            
            return True, f"Welcome, {username}!"
        else:
            # Log failed attempt
            self.db.log_activity(username, "Failed Login", "Invalid credentials")
            return False, "Invalid username or password"
    
    def logout(self):
        """Logout user"""
        if st.session_state.username:
            self.db.log_activity(
                st.session_state.username, 
                "Logout", 
                "User logged out"
            )
        
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.role = None
        st.session_state.login_time = None
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        return st.session_state.get('authenticated', False)
    
    def get_current_user(self):
        """Get current username"""
        return st.session_state.get('username', None)
    
    def get_current_role(self):
        """Get current user role"""
        return st.session_state.get('role', None)
    
    def check_session_timeout(self, timeout_minutes=60):
        """
        Check if session has timed out
        
        Args:
            timeout_minutes: Timeout duration in minutes
            
        Returns:
            bool: True if session is valid, False if timed out
        """
        if not self.is_authenticated():
            return False
        
        login_time = st.session_state.get('login_time')
        if not login_time:
            return False
        
        time_elapsed = datetime.now() - login_time
        if time_elapsed > timedelta(minutes=timeout_minutes):
            self.logout()
            return False
        
        return True
    
    def require_authentication(self):
        """
        Decorator-style function to require authentication
        Returns True if authenticated, False otherwise
        """
        if not self.is_authenticated():
            st.warning("Please login to access this page")
            self.show_login_form()
            return False
        
        if not self.check_session_timeout():
            st.error("Session expired. Please login again.")
            self.show_login_form()
            return False
        
        return True
    
    def require_role(self, required_role):
        """
        Check if user has required role
        
        Args:
            required_role: Required role (Admin, Auditor, Analyst, Viewer)
            
        Returns:
            bool: True if user has required role
        """
        if not self.is_authenticated():
            return False
        
        current_role = self.get_current_role()
        
        # Admin has access to everything
        if current_role == "Admin":
            return True
        
        # Check specific role
        if current_role == required_role:
            return True
        
        return False
    
    def show_login_form(self):
        """Display login form"""
        st.subheader("Login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                success, message = self.login(username, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        st.info("Default admin credentials: username='admin', password='admin123'")


def require_auth(func):
    """
    Decorator to require authentication for a function
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        auth = AuthManager()
        if auth.require_authentication():
            return func(*args, **kwargs)
        else:
            st.stop()
    return wrapper


def require_admin(func):
    """
    Decorator to require admin role
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        auth = AuthManager()
        if not auth.require_authentication():
            st.stop()
        
        if not auth.require_role("Admin"):
            st.error("Access Denied: Admin role required")
            st.stop()
        
        return func(*args, **kwargs)
    return wrapper


def get_current_username():
    """
    Get current logged in username
    
    Returns:
        str: Username or None
    """
    return st.session_state.get('username', None)


def get_current_role():
    """
    Get current user role
    
    Returns:
        str: Role or None
    """
    return st.session_state.get('role', None)


def is_admin():
    """
    Check if current user is admin
    
    Returns:
        bool: True if admin
    """
    return get_current_role() == "Admin"
