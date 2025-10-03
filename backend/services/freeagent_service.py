import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FreeAgentService:
    """FreeAgent API Service"""
    
    def __init__(self, client_id: str, client_secret: str, access_token: str = None, refresh_token: str = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.base_url = "https://api.freeagent.com/v2"
        self.session = requests.Session()
        
        if self.access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request to FreeAgent"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"FreeAgent API request: {method} {endpoint}")
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FreeAgent API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"FreeAgent API request failed: {str(e)}")
    
    async def get_contacts(self) -> List[Dict[str, Any]]:
        """Get all contacts from FreeAgent"""
        try:
            response = self._make_request('GET', '/contacts')
            contacts = response.get('contacts', [])
            logger.info(f"Retrieved {len(contacts)} contacts from FreeAgent")
            return contacts
            
        except Exception as e:
            logger.error(f"Error getting contacts: {str(e)}")
            raise
    
    async def find_contact_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find contact by email address"""
        try:
            contacts = await self.get_contacts()
            
            for contact in contacts:
                if contact.get('email', '').lower() == email.lower():
                    logger.info(f"Found contact with email {email}")
                    return contact
            
            logger.info(f"No contact found with email {email}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding contact by email: {str(e)}")
            raise
    
    async def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contact in FreeAgent"""
        try:
            payload = {'contact': contact_data}
            response = self._make_request('POST', '/contacts', json=payload)
            
            contact = response.get('contact', {})
            logger.info(f"Created contact in FreeAgent: {contact.get('url')}")
            return contact
            
        except Exception as e:
            logger.error(f"Error creating contact: {str(e)}")
            raise
    
    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an invoice in FreeAgent"""
        try:
            payload = {'invoice': invoice_data}
            response = self._make_request('POST', '/invoices', json=payload)
            
            invoice = response.get('invoice', {})
            logger.info(f"Created invoice in FreeAgent: {invoice.get('url')}")
            return invoice
            
        except Exception as e:
            logger.error(f"Error creating invoice: {str(e)}")
            raise
    
    async def get_invoice(self, invoice_url: str) -> Dict[str, Any]:
        """Get invoice details"""
        try:
            # Extract endpoint from full URL
            endpoint = invoice_url.replace(self.base_url, '')
            response = self._make_request('GET', endpoint)
            return response.get('invoice', {})
            
        except Exception as e:
            logger.error(f"Error getting invoice: {str(e)}")
            raise