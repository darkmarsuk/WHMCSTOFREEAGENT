import logging
from typing import Dict, Any
from datetime import datetime, timezone
from decimal import Decimal

logger = logging.getLogger(__name__)


class SyncService:
    """Service to sync invoices from WHMCS to FreeAgent"""
    
    def __init__(self, whmcs_service, freeagent_service, db):
        self.whmcs = whmcs_service
        self.freeagent = freeagent_service
        self.db = db
    
    async def sync_invoices(self) -> Dict[str, Any]:
        """Sync invoices from WHMCS to FreeAgent"""
        result = {
            'invoices_processed': 0,
            'invoices_created': 0,
            'clients_created': 0,
            'errors': [],
            'message': ''
        }
        
        try:
            # Get invoices from WHMCS (last 30 days of unpaid/paid invoices)
            logger.info("Fetching invoices from WHMCS...")
            whmcs_invoices = await self.whmcs.get_invoices(limit=50)
            
            if not whmcs_invoices:
                result['message'] = 'No invoices found in WHMCS'
                return result
            
            logger.info(f"Processing {len(whmcs_invoices)} invoices...")
            
            for whmcs_invoice in whmcs_invoices:
                try:
                    result['invoices_processed'] += 1
                    
                    # Get detailed invoice data
                    invoice_id = int(whmcs_invoice.get('id'))
                    detailed_invoice = await self.whmcs.get_invoice(invoice_id)
                    
                    # Get or create FreeAgent contact
                    client_id = int(detailed_invoice.get('userid'))
                    whmcs_client = await self.whmcs.get_client(client_id)
                    
                    email = whmcs_client.get('email')
                    if not email:
                        logger.warning(f"Invoice {invoice_id}: No email for client {client_id}, skipping")
                        result['errors'].append(f"Invoice {invoice_id}: No email for client")
                        continue
                    
                    # Check if we already have a mapping
                    mapping = await self.db.client_mappings.find_one({'whmcs_client_id': client_id})
                    
                    if mapping:
                        freeagent_contact_url = mapping['freeagent_contact_url']
                        logger.info(f"Using existing mapping for client {client_id}")
                    else:
                        # Find or create contact in FreeAgent
                        freeagent_contact = await self.freeagent.find_contact_by_email(email)
                        
                        if not freeagent_contact:
                            # Create new contact
                            logger.info(f"Creating new contact in FreeAgent for {email}")
                            
                            contact_data = {
                                'first_name': whmcs_client.get('firstname', 'Unknown'),
                                'last_name': whmcs_client.get('lastname', 'Client'),
                                'email': email,
                                'organisation_name': whmcs_client.get('companyname', ''),
                                'address1': whmcs_client.get('address1', ''),
                                'address2': whmcs_client.get('address2', ''),
                                'town': whmcs_client.get('city', ''),
                                'region': whmcs_client.get('state', ''),
                                'postcode': whmcs_client.get('postcode', ''),
                                'country': whmcs_client.get('country', 'GB'),
                                'phone_number': whmcs_client.get('phonenumber', '')
                            }
                            
                            freeagent_contact = await self.freeagent.create_contact(contact_data)
                            result['clients_created'] += 1
                        
                        freeagent_contact_url = freeagent_contact.get('url')
                        
                        # Save mapping
                        await self.db.client_mappings.insert_one({
                            'whmcs_client_id': client_id,
                            'whmcs_email': email,
                            'freeagent_contact_url': freeagent_contact_url,
                            'created_at': datetime.now(timezone.utc)
                        })
                        
                        logger.info(f"Saved mapping for client {client_id}")
                    
                    # Check if invoice already synced
                    existing_invoice = await self.db.synced_invoices.find_one({
                        'whmcs_invoice_id': invoice_id
                    })
                    
                    if existing_invoice:
                        logger.info(f"Invoice {invoice_id} already synced, skipping")
                        continue
                    
                    # Create invoice in FreeAgent
                    logger.info(f"Creating invoice {invoice_id} in FreeAgent...")
                    
                    # Parse invoice items
                    items = detailed_invoice.get('items', [])
                    invoice_items = []
                    
                    for item in items:
                        invoice_items.append({
                            'item_type': 'Services',  # Can be 'Hours', 'Days', 'Weeks', 'Months', 'Products', 'Services'
                            'description': item.get('description', 'Service'),
                            'quantity': 1.0,
                            'price': float(item.get('amount', 0))
                        })
                    
                    # If no items, create a single item with total
                    if not invoice_items:
                        invoice_items.append({
                            'item_type': 'Services',
                            'description': f"Invoice #{detailed_invoice.get('invoicenum', invoice_id)}",
                            'quantity': 1.0,
                            'price': float(detailed_invoice.get('subtotal', 0))
                        })
                    
                    # Parse dates
                    date_str = detailed_invoice.get('date', '')
                    due_date_str = detailed_invoice.get('duedate', '')
                    
                    # Convert date format from YYYY-MM-DD to YYYY-MM-DD
                    invoice_date = date_str if date_str else datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    due_date = due_date_str if due_date_str else invoice_date
                    
                    freeagent_invoice_data = {
                        'contact': freeagent_contact_url,
                        'dated_on': invoice_date,
                        'due_on': due_date,
                        'reference': f"wh-{invoice_id}",
                        'currency': detailed_invoice.get('currencycode', 'GBP'),
                        'payment_terms_in_days': 30,  # Default payment terms
                        'invoice_items': invoice_items,
                        'comments': f"Synced from WHMCS Invoice #{invoice_id}"
                    }
                    
                    freeagent_invoice = await self.freeagent.create_invoice(freeagent_invoice_data)
                    
                    # Mark invoice as sent (not draft)
                    try:
                        await self.freeagent.mark_invoice_as_sent(freeagent_invoice.get('url'))
                        logger.info(f"Invoice {invoice_id} marked as sent in FreeAgent")
                    except Exception as e:
                        logger.warning(f"Could not mark invoice as sent: {str(e)}")
                    
                    result['invoices_created'] += 1
                    
                    # Save sync record
                    await self.db.synced_invoices.insert_one({
                        'whmcs_invoice_id': invoice_id,
                        'freeagent_invoice_url': freeagent_invoice.get('url'),
                        'synced_at': datetime.now(timezone.utc)
                    })
                    
                    logger.info(f"Successfully synced invoice {invoice_id}")
                    
                except Exception as e:
                    error_msg = f"Error processing invoice {whmcs_invoice.get('id')}: {str(e)}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
                    continue
            
            # Build result message
            if result['invoices_created'] > 0:
                result['message'] = f"Successfully synced {result['invoices_created']} invoices and created {result['clients_created']} new contacts"
            else:
                result['message'] = f"Processed {result['invoices_processed']} invoices, but no new invoices to sync"
            
            if result['errors']:
                result['message'] += f" (with {len(result['errors'])} errors)"
            
            return result
            
        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            raise
    
    async def sync_payments_from_freeagent(self) -> Dict[str, Any]:
        """Sync payments from FreeAgent back to WHMCS"""
        result = {
            'invoices_checked': 0,
            'payments_synced': 0,
            'errors': [],
            'message': ''
        }
        
        try:
            logger.info("Fetching synced invoices for payment sync...")
            
            # Get all synced invoices from database
            synced_invoices = await self.db.synced_invoices.find().to_list(1000)
            
            if not synced_invoices:
                result['message'] = 'No synced invoices found'
                return result
            
            logger.info(f"Checking {len(synced_invoices)} synced invoices for payments...")
            
            for synced in synced_invoices:
                try:
                    result['invoices_checked'] += 1
                    whmcs_invoice_id = synced.get('whmcs_invoice_id')
                    freeagent_invoice_url = synced.get('freeagent_invoice_url')
                    
                    # Skip if already marked as paid in our database
                    if synced.get('payment_synced'):
                        continue
                    
                    # First, check WHMCS invoice status BEFORE checking FreeAgent
                    try:
                        whmcs_invoice = await self.whmcs.get_invoice(whmcs_invoice_id)
                        current_status = whmcs_invoice.get('status', '')
                        
                        # Skip if Draft - not ready for payments yet
                        if current_status == 'Draft':
                            logger.info(f"Invoice {whmcs_invoice_id} is Draft in WHMCS, skipping payment sync")
                            continue
                        
                        # Skip if already paid, cancelled, or refunded in WHMCS
                        if current_status in ['Paid', 'Cancelled', 'Refunded']:
                            logger.info(f"Invoice {whmcs_invoice_id} is already {current_status} in WHMCS, skipping payment sync")
                            # Mark as synced in database to prevent future checks
                            await self.db.synced_invoices.update_one(
                                {'whmcs_invoice_id': whmcs_invoice_id},
                                {
                                    '$set': {
                                        'payment_synced': True,
                                        'payment_synced_at': datetime.now(timezone.utc),
                                        'already_paid_in_whmcs': True
                                    }
                                }
                            )
                            continue
                    except Exception as e:
                        logger.warning(f"Could not check WHMCS invoice status: {str(e)}")
                        continue
                    
                    # Now check FreeAgent invoice for payment
                    fa_invoice = await self.freeagent.get_invoice(freeagent_invoice_url)
                    
                    # Check if invoice is paid in FreeAgent
                    if fa_invoice.get('status') != 'Paid':
                        continue
                    
                    # Get payment amount and date
                    total_paid = Decimal(str(fa_invoice.get('total_value', 0)))
                    dated_on = fa_invoice.get('dated_on')
                    
                    # Format date for WHMCS (YYYY-MM-DD)
                    if isinstance(dated_on, str):
                        payment_date = dated_on  # Already in correct format
                    else:
                        payment_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    
                    if total_paid <= 0:
                        continue
                    
                    logger.info(f"Invoice {whmcs_invoice_id} is paid in FreeAgent, syncing payment to WHMCS...")
                    
                    # Add payment to WHMCS
                    await self.whmcs.add_invoice_payment(
                        invoice_id=whmcs_invoice_id,
                        amount=float(total_paid),
                        date=payment_date,
                        transaction_id=f"FA-{whmcs_invoice_id}",
                        gateway="banktransfer"
                    )
                    
                    # Mark as synced in database
                    await self.db.synced_invoices.update_one(
                        {'whmcs_invoice_id': whmcs_invoice_id},
                        {
                            '$set': {
                                'payment_synced': True,
                                'payment_synced_at': datetime.now(timezone.utc),
                                'payment_amount': float(total_paid)
                            }
                        }
                    )
                    
                    result['payments_synced'] += 1
                    logger.info(f"Payment synced for invoice {whmcs_invoice_id}")
                    
                except Exception as e:
                    error_msg = f"Error syncing payment for invoice {synced.get('whmcs_invoice_id')}: {str(e)}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
                    continue
            
            # Build result message
            if result['payments_synced'] > 0:
                result['message'] = f"Synced {result['payments_synced']} payments from FreeAgent to WHMCS"
            else:
                result['message'] = f"Checked {result['invoices_checked']} invoices, no new payments to sync"
            
            if result['errors']:
                result['message'] += f" (with {len(result['errors'])} errors)"
            
            return result
            
        except Exception as e:
            logger.error(f"Payment sync failed: {str(e)}")
            raise