"""
RESTful API module for Nexcomply v2.0
Provides external API access to compliance data and analysis
"""

import json
import hashlib
import hmac
from datetime import datetime, timedelta
from functools import wraps


class NexcomplyAPI:
    """Nexcomply RESTful API handler"""
    
    def __init__(self, db):
        """Initialize API with database connection"""
        self.db = db
        self.version = "v1"
        self.base_path = f"/api/{self.version}"
    
    # ----- Authentication -----
    
    def generate_api_key(self, username):
        """Generate an API key for a user"""
        secret = f"{username}{datetime.now().isoformat()}"
        return hashlib.sha256(secret.encode()).hexdigest()
    
    def validate_api_key(self, api_key):
        """Validate an API key"""
        stored_key = self.db.get_config(f"api_key_{api_key[:8]}", None)
        if stored_key and stored_key == api_key:
            return True, self.db.get_config(f"api_key_user_{api_key[:8]}", None)
        return False, None
    
    def store_api_key(self, api_key, username):
        """Store an API key"""
        self.db.set_config(f"api_key_{api_key[:8]}", api_key, username)
        self.db.set_config(f"api_key_user_{api_key[:8]}", username, username)
    
    def revoke_api_key(self, api_key, username):
        """Revoke an API key"""
        self.db.set_config(f"api_key_{api_key[:8]}", "revoked", username)
    
    # ----- Webhook support -----
    
    def verify_webhook_signature(self, payload, signature, secret):
        """Verify webhook payload signature (HMAC-SHA256)"""
        expected = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)
    
    def dispatch_webhook(self, event_type, payload):
        """Dispatch webhook event to registered endpoints"""
        webhooks = self._get_registered_webhooks(event_type)
        results = []
        
        for webhook in webhooks:
            try:
                import urllib.request
                data = json.dumps({
                    'event': event_type,
                    'timestamp': datetime.now().isoformat(),
                    'payload': payload
                }).encode('utf-8')
                
                req = urllib.request.Request(
                    webhook['url'],
                    data=data,
                    headers={
                        'Content-Type': 'application/json',
                        'X-Nexcomply-Event': event_type,
                        'X-Nexcomply-Signature': f"sha256={hmac.new(webhook.get('secret', '').encode(), data, hashlib.sha256).hexdigest()}"
                    },
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    results.append({
                        'url': webhook['url'],
                        'status': response.status,
                        'success': True
                    })
            except Exception as e:
                results.append({
                    'url': webhook['url'],
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def _get_registered_webhooks(self, event_type=None):
        """Get registered webhook configurations"""
        webhooks_config = self.db.get_config('webhooks', '[]')
        try:
            webhooks = json.loads(webhooks_config)
            if event_type:
                return [w for w in webhooks if event_type in w.get('events', [])]
            return webhooks
        except Exception:
            return []
    
    def register_webhook(self, url, events, secret, registered_by):
        """Register a new webhook"""
        webhooks = self._get_registered_webhooks()
        webhook_id = hashlib.sha256(f"{url}{datetime.now()}".encode()).hexdigest()[:12]
        webhooks.append({
            'id': webhook_id,
            'url': url,
            'events': events,
            'secret': secret,
            'registered_by': registered_by,
            'registered_at': datetime.now().isoformat(),
            'active': True
        })
        self.db.set_config('webhooks', json.dumps(webhooks), registered_by)
        return webhook_id
    
    def unregister_webhook(self, webhook_id, username):
        """Unregister a webhook"""
        webhooks = self._get_registered_webhooks()
        webhooks = [w for w in webhooks if w['id'] != webhook_id]
        self.db.set_config('webhooks', json.dumps(webhooks), username)
    
    # ----- API Endpoint Handlers -----
    
    def get_statistics(self):
        """GET /api/v1/statistics"""
        stats = self.db.get_statistics()
        return {
            'status': 'success',
            'data': stats,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_documents(self, page=1, per_page=20):
        """GET /api/v1/documents"""
        docs_df = self.db.get_all_documents()
        total = len(docs_df)
        start = (page - 1) * per_page
        end = start + per_page
        page_data = docs_df.iloc[start:end]
        
        return {
            'status': 'success',
            'data': page_data.to_dict(orient='records'),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_analysis_history(self, page=1, per_page=20, framework=None):
        """GET /api/v1/analysis"""
        df = self.db.get_analysis_history(limit=1000)
        if framework:
            df = df[df['framework_name'].str.contains(framework, case=False, na=False)]
        
        total = len(df)
        start = (page - 1) * per_page
        end = start + per_page
        page_data = df.iloc[start:end]
        
        return {
            'status': 'success',
            'data': page_data.to_dict(orient='records'),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_reports(self, page=1, per_page=20):
        """GET /api/v1/reports"""
        df = self.db.get_all_reports()
        total = len(df)
        start = (page - 1) * per_page
        end = start + per_page
        page_data = df.iloc[start:end]
        
        return {
            'status': 'success',
            'data': page_data.to_dict(orient='records'),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_knowledge_library(self, page=1, per_page=20, category=None, framework=None, search=None):
        """GET /api/v1/knowledge-library"""
        df = self.db.get_kl_entries(category=category, framework=framework, search_term=search)
        total = len(df)
        start = (page - 1) * per_page
        end = start + per_page
        page_data = df.iloc[start:end]
        
        return {
            'status': 'success',
            'data': page_data.to_dict(orient='records'),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_batch_jobs(self, page=1, per_page=20):
        """GET /api/v1/batch-jobs"""
        df = self.db.get_batch_jobs()
        total = len(df)
        start = (page - 1) * per_page
        end = start + per_page
        page_data = df.iloc[start:end]
        
        return {
            'status': 'success',
            'data': page_data.to_dict(orient='records'),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_api_endpoints(self):
        """Return API endpoint documentation"""
        return {
            'status': 'success',
            'api_version': self.version,
            'base_url': f'http://localhost:8000{self.base_path}',
            'endpoints': [
                {
                    'method': 'GET',
                    'path': f'{self.base_path}/statistics',
                    'description': 'Get system statistics',
                    'auth': 'API Key required'
                },
                {
                    'method': 'GET',
                    'path': f'{self.base_path}/documents',
                    'description': 'List all documents',
                    'params': 'page, per_page',
                    'auth': 'API Key required'
                },
                {
                    'method': 'GET',
                    'path': f'{self.base_path}/analysis',
                    'description': 'Get analysis history',
                    'params': 'page, per_page, framework',
                    'auth': 'API Key required'
                },
                {
                    'method': 'GET',
                    'path': f'{self.base_path}/reports',
                    'description': 'List all reports',
                    'params': 'page, per_page',
                    'auth': 'API Key required'
                },
                {
                    'method': 'GET',
                    'path': f'{self.base_path}/knowledge-library',
                    'description': 'Get knowledge library entries',
                    'params': 'page, per_page, category, framework, search',
                    'auth': 'API Key required'
                },
                {
                    'method': 'GET',
                    'path': f'{self.base_path}/batch-jobs',
                    'description': 'List batch processing jobs',
                    'params': 'page, per_page',
                    'auth': 'API Key required'
                },
                {
                    'method': 'POST',
                    'path': f'{self.base_path}/webhooks',
                    'description': 'Register a webhook endpoint',
                    'body': 'url, events[], secret',
                    'auth': 'API Key required'
                },
                {
                    'method': 'DELETE',
                    'path': f'{self.base_path}/webhooks/{{webhook_id}}',
                    'description': 'Unregister a webhook',
                    'auth': 'API Key required'
                }
            ],
            'events': [
                'analysis.completed',
                'report.generated',
                'batch.completed',
                'document.uploaded',
                'user.login'
            ],
            'timestamp': datetime.now().isoformat()
        }
