import requests
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class FreeAgentOAuth:
    """FreeAgent OAuth2 Service"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorize_url = "https://api.freeagent.com/v2/approve_app"
        self.token_url = "https://api.freeagent.com/v2/token_endpoint"
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate OAuth authorization URL"""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri
        }
        
        if state:
            params['state'] = state
        
        url = f"{self.authorize_url}?{urlencode(params)}"
        logger.info(f"Generated authorization URL")
        return url
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        try:
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect_uri,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            logger.info("Exchanging authorization code for tokens...")
            response = requests.post(
                self.token_url,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Successfully obtained access token")
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Failed to exchange code for token: {str(e)}")
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            logger.info("Refreshing access token...")
            response = requests.post(
                self.token_url,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Successfully refreshed access token")
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Token refresh failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Failed to refresh token: {str(e)}")