"""
AWS Cognito Authentication Module

Handles user authentication using AWS Cognito User Pools with JWT token validation.
Provides decorators for protecting admin routes and managing user sessions.

Built with AI assistance to demonstrate secure authentication patterns.
"""

import os
import json
import base64
import hashlib
import hmac
from functools import wraps
from flask import session, request, redirect, url_for, flash
import boto3
from botocore.exceptions import ClientError
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import requests

class CognitoAuth:
    """
    AWS Cognito authentication handler with JWT token validation.
    Supports both username/password and token-based authentication.
    """
    
    def __init__(self):
        self.enabled = False
        self.cognito_client = None
        self.user_pool_id = None
        self.client_id = None
        self.client_secret = None
        self.region = None
        self.jwks = None
        
    def init_app(self, app):
        """Initialize Cognito authentication with Flask app configuration"""
        # Load configuration from environment variables
        self.user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
        self.client_id = os.environ.get('COGNITO_CLIENT_ID')
        self.client_secret = os.environ.get('COGNITO_CLIENT_SECRET')
        self.region = os.environ.get('COGNITO_REGION', 'us-east-1')
        
        # Enable authentication if all required config is present
        if all([self.user_pool_id, self.client_id, self.region]):
            try:
                self.cognito_client = boto3.client('cognito-idp', region_name=self.region)
                self.enabled = True
                self._load_jwks()
                print(f"✅ Cognito authentication enabled for pool: {self.user_pool_id}")
            except Exception as e:
                print(f"⚠️ Cognito authentication disabled: {e}")
                self.enabled = False
        else:
            print("⚠️ Cognito authentication disabled: Missing configuration")
    
    def _load_jwks(self):
        """Load JSON Web Key Set for token validation"""
        try:
            jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
            response = requests.get(jwks_url)
            self.jwks = response.json()
        except Exception as e:
            print(f"Warning: Could not load JWKS: {e}")
    
    def calculate_secret_hash(self, username):
        """Calculate secret hash for Cognito client authentication"""
        if not self.client_secret:
            return None
            
        message = username + self.client_id
        dig = hmac.new(
            self.client_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()
    
    def authenticate_user(self, username, password):
        """
        Authenticate user with username/password using Cognito.
        Returns authentication tokens on success, error dict on failure.
        """
        if not self.enabled:
            return None
        
        try:
            # Prepare authentication parameters
            auth_params = {
                'USERNAME': username,
                'PASSWORD': password
            }
            
            # Add secret hash if client secret is configured
            if self.client_secret:
                auth_params['SECRET_HASH'] = self.calculate_secret_hash(username)
            
            # Authenticate with Cognito
            response = self.cognito_client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_NO_SRP_AUTH',  # Direct username/password auth
                AuthParameters=auth_params
            )
            
            return response['AuthenticationResult']
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NotAuthorizedException':
                return {'error': 'Invalid username or password'}
            elif error_code == 'UserNotFoundException':
                return {'error': 'User not found'}
            elif error_code == 'UserNotConfirmedException':
                return {'error': 'User account not confirmed'}
            else:
                return {'error': f'Authentication failed: {error_code}'}
        except Exception as e:
            return {'error': f'Authentication error: {str(e)}'}
    
    def verify_token(self, token):
        """
        Verify JWT token and extract user information.
        Returns user info dict on success, None on failure.
        """
        if not self.enabled or not token:
            return None
        
        try:
            # Decode token header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get('kid')
            
            if not kid or not self.jwks:
                return None
            
            # Find the correct key
            key = None
            for jwk in self.jwks.get('keys', []):
                if jwk.get('kid') == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
                    break
            
            if not key:
                return None
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f'https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}'
            )
            
            return payload
            
        except ExpiredSignatureError:
            return None
        except InvalidTokenError:
            return None
        except Exception as e:
            print(f"Token verification error: {e}")
            return None
    
    def is_admin(self, user_info):
        """
        Check if user has admin privileges.
        Currently checks for 'admin' group membership.
        """
        if not user_info:
            return False
        
        # Check for admin group in token
        groups = user_info.get('cognito:groups', [])
        return 'admin' in groups or user_info.get('username') == 'admin'

# Global authentication instance
cognito_auth = CognitoAuth()

def require_admin(f):
    """
    Decorator to require admin authentication for routes.
    Redirects to login page if not authenticated or not admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not cognito_auth.enabled:
            # If auth is disabled, allow access (development mode)
            return f(*args, **kwargs)
        
        # Check for token in session
        token = session.get('id_token')
        
        if not token:
            flash('Admin access required. Please log in.', 'warning')
            return redirect(url_for('admin_login'))
        
        # Verify token and check admin status
        user_info = cognito_auth.verify_token(token)
        if not user_info:
            flash('Invalid or expired token. Please log in again.', 'warning')
            session.pop('id_token', None)
            return redirect(url_for('admin_login'))
        
        if not cognito_auth.is_admin(user_info):
            flash('Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        # Store user info in request context for use in templates
        request.current_user = user_info
        return f(*args, **kwargs)
    
    return decorated_function

def admin_optional(f):
    """
    Decorator to optionally check for admin status.
    Sets request.is_admin flag but doesn't require authentication.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        request.is_admin = False
        request.current_user = None
        
        if cognito_auth.enabled:
            token = session.get('id_token')
            if token:
                user_info = cognito_auth.verify_token(token)
                if user_info and cognito_auth.is_admin(user_info):
                    request.is_admin = True
                    request.current_user = user_info
        
        return f(*args, **kwargs)
    
    return decorated_function
