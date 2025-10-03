import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class WHMCSService:
    """WHMCS API Service"""
    
    def __init__(self, url: str, identifier: str, secret: str):
        self.url = url.rstrip('/')
        self.api_url = f"{self.url}/includes/api.php"
        self.identifier = identifier
        self.secret = secret
        self.session = requests.Session()
    
    def _make_request(self, action: str, **kwargs) -> Dict[str, Any]:
        """Make API request to WHMCS"""
        data = {
            'identifier': self.identifier,
            'secret': self.secret,
            'action': action,
            'responsetype': 'json',
            **kwargs
        }
        
        try:
            logger.debug(f"WHMCS API request: {action}")
            response = self.session.post(self.api_url, data=data, timeout=30)
            response.raise_for_status()
            
            response_data = response.json()
            
            # Check for WHMCS API errors
            if response_data.get('result') == 'error':
                error_message = response_data.get('message', 'Unknown WHMCS API error')
                logger.error(f"WHMCS API error: {error_message}")
                raise Exception(f"WHMCS API Error: {error_message}")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"WHMCS API request failed: {str(e)}")
            raise Exception(f"WHMCS API request failed: {str(e)}")
    
    async def get_invoices(self, limit: int = 100, status: str = None) -> List[Dict[str, Any]]:
        """Get invoices from WHMCS"""
        try:
            params = {
                'limitnum': limit,
                'orderby': 'id',
                'order': 'desc'
            }
            
            if status:
                params['status'] = status
            
            response = self._make_request('GetInvoices', **params)
            
            invoices = []
            invoice_data = response.get('invoices', {}).get('invoice', [])
            
            # Handle single invoice response
            if isinstance(invoice_data, dict):
                invoice_data = [invoice_data]
            
            for invoice in invoice_data:
                invoices.append(invoice)
            
            logger.info(f"Retrieved {len(invoices)} invoices from WHMCS")
            return invoices
            
        except Exception as e:
            logger.error(f"Error getting invoices: {str(e)}")
            raise
    
    async def get_invoice(self, invoice_id: int) -> Dict[str, Any]:
        """Get detailed invoice information"""
        try:
            response = self._make_request('GetInvoice', invoiceid=invoice_id)
            
            # Parse items
            if 'items' in response and 'item' in response['items']:
                items_data = response['items']['item']
                if isinstance(items_data, dict):
                    items_data = [items_data]
                response['items'] = items_data
            else:
                response['items'] = []
            
            logger.info(f"Retrieved invoice {invoice_id} from WHMCS")
            return response
            
        except Exception as e:
            logger.error(f"Error getting invoice {invoice_id}: {str(e)}")
            raise
    
    async def get_client(self, client_id: int) -> Dict[str, Any]:
        """Get client details"""
        try:
            response = self._make_request('GetClientsDetails', clientid=client_id)
            logger.info(f"Retrieved client {client_id} from WHMCS")
            return response
            
        except Exception as e:
            logger.error(f"Error getting client {client_id}: {str(e)}")
            raise
    
    async def add_invoice_payment(self, invoice_id: int, amount: float, date: str, transaction_id: str = None, gateway: str = "banktransfer") -> Dict[str, Any]:
        """Add payment to WHMCS invoice"""
        try:
            params = {
                'invoiceid': invoice_id,
                'transid': transaction_id or f"FA-{invoice_id}",
                'gateway': gateway,
                'date': date,
                'amount': amount
            }
            
            response = self._make_request('AddInvoicePayment', **params)
            logger.info(f"Added payment to invoice {invoice_id}: {amount}")
            return response
            
        except Exception as e:
            logger.error(f"Error adding payment to invoice {invoice_id}: {str(e)}")
            raise