from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Import our services
from services.whmcs_service import WHMCSService
from services.freeagent_service import FreeAgentService
from services.sync_service import SyncService
from services.freeagent_oauth import FreeAgentOAuth

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OAuth state storage (in production, use Redis or database)
oauth_states = {}


# Define Models
class Credentials(BaseModel):
    whmcs_url: Optional[str] = None
    whmcs_identifier: Optional[str] = None
    whmcs_secret: Optional[str] = None
    freeagent_client_id: Optional[str] = None
    freeagent_client_secret: Optional[str] = None
    freeagent_access_token: Optional[str] = None
    freeagent_refresh_token: Optional[str] = None
    freeagent_token_expires_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SyncLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sync_type: str  # 'manual' or 'automatic'
    status: str  # 'success', 'error', 'running'
    invoices_processed: int = 0
    invoices_created: int = 0
    clients_created: int = 0
    payments_synced: int = 0
    errors: List[str] = []
    message: Optional[str] = None


class SyncStatus(BaseModel):
    is_running: bool
    last_sync: Optional[datetime] = None
    next_sync: Optional[datetime] = None


class ClientMapping(BaseModel):
    whmcs_client_id: int
    whmcs_email: str
    freeagent_contact_url: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Background sync function
async def perform_sync():
    """Perform automatic sync"""
    logger.info("Starting automatic sync...")
    
    # Get credentials
    creds = await db.credentials.find_one({})
    if not creds:
        logger.error("No credentials found for automatic sync")
        return
    
    # Check if we have FreeAgent tokens
    if not creds.get('freeagent_access_token'):
        logger.error("No FreeAgent access token found")
        return
    
    # Create sync log
    sync_log = SyncLog(
        sync_type='automatic',
        status='running',
        message='Starting automatic sync...'
    )
    await db.sync_logs.insert_one(sync_log.dict())
    
    try:
        # Initialize services
        whmcs_service = WHMCSService(
            url=creds.get('whmcs_url'),
            identifier=creds.get('whmcs_identifier'),
            secret=creds.get('whmcs_secret')
        )
        
        freeagent_service = FreeAgentService(
            client_id=creds.get('freeagent_client_id'),
            client_secret=creds.get('freeagent_client_secret'),
            access_token=creds.get('freeagent_access_token'),
            refresh_token=creds.get('freeagent_refresh_token')
        )
        
        sync_service = SyncService(whmcs_service, freeagent_service, db)
        
        # Perform invoice sync
        result = await sync_service.sync_invoices()
        
        # Perform payment sync from FreeAgent to WHMCS
        try:
            payment_result = await sync_service.sync_payments_from_freeagent()
            result['payments_synced'] = payment_result.get('payments_synced', 0)
            if payment_result.get('message'):
                result['message'] += f" | {payment_result['message']}"
        except Exception as e:
            logger.warning(f"Payment sync failed during automatic sync: {str(e)}")
        
        # Update sync log
        sync_log.status = 'success'
        sync_log.invoices_processed = result.get('invoices_processed', 0)
        sync_log.invoices_created = result.get('invoices_created', 0)
        sync_log.clients_created = result.get('clients_created', 0)
        sync_log.payments_synced = result.get('payments_synced', 0)
        sync_log.message = result.get('message', 'Sync completed successfully')
        
        await db.sync_logs.update_one(
            {'id': sync_log.id},
            {'$set': sync_log.dict()}
        )
        
        logger.info(f"Automatic sync completed: {result}")
        
    except Exception as e:
        logger.error(f"Automatic sync failed: {str(e)}")
        sync_log.status = 'error'
        sync_log.errors = [str(e)]
        sync_log.message = f'Sync failed: {str(e)}'
        
        await db.sync_logs.update_one(
            {'id': sync_log.id},
            {'$set': sync_log.dict()}
        )


# Routes
@api_router.get("/")
async def root():
    return {"message": "WHMCS to FreeAgent Sync API"}


@api_router.post("/settings/credentials")
async def save_credentials(credentials: Credentials):
    """Save API credentials"""
    try:
        # Update or insert credentials
        credentials.updated_at = datetime.now(timezone.utc)
        await db.credentials.delete_many({})  # Only keep one set of credentials
        await db.credentials.insert_one(credentials.dict())
        
        logger.info("Credentials saved successfully")
        return {"status": "success", "message": "Credentials saved successfully"}
    except Exception as e:
        logger.error(f"Error saving credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/settings/credentials")
async def get_credentials():
    """Get API credentials (masked)"""
    try:
        creds = await db.credentials.find_one({})
        if not creds:
            return None
        
        # Mask sensitive data
        masked_creds = {
            'whmcs_url': creds.get('whmcs_url'),
            'whmcs_identifier': '***' + creds.get('whmcs_identifier', '')[-4:] if creds.get('whmcs_identifier') else None,
            'whmcs_secret': '***' if creds.get('whmcs_secret') else None,
            'freeagent_client_id': creds.get('freeagent_client_id'),
            'freeagent_client_secret': '***' if creds.get('freeagent_client_secret') else None,
            'has_access_token': bool(creds.get('freeagent_access_token')),
            'is_connected': bool(creds.get('freeagent_access_token')),
            'updated_at': creds.get('updated_at')
        }
        
        return masked_creds
    except Exception as e:
        logger.error(f"Error getting credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/oauth/freeagent/authorize")
async def freeagent_authorize():
    """Initiate FreeAgent OAuth flow"""
    try:
        # Get credentials
        creds = await db.credentials.find_one({})
        if not creds or not creds.get('freeagent_client_id'):
            raise HTTPException(status_code=400, detail="FreeAgent credentials not configured")
        
        # Get the frontend URL from environment
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        redirect_uri = f"{os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')}/api/oauth/freeagent/callback"
        
        # Create OAuth service
        oauth = FreeAgentOAuth(
            client_id=creds.get('freeagent_client_id'),
            client_secret=creds.get('freeagent_client_secret'),
            redirect_uri=redirect_uri
        )
        
        # Generate state for CSRF protection
        state = str(uuid.uuid4())
        oauth_states[state] = {'timestamp': datetime.now(timezone.utc)}
        
        # Get authorization URL
        auth_url = oauth.get_authorization_url(state=state)
        
        logger.info(f"Redirecting to FreeAgent authorization: {auth_url}")
        return {"authorization_url": auth_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth authorization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/oauth/freeagent/callback")
async def freeagent_callback(code: str = Query(...), state: str = Query(None)):
    """Handle FreeAgent OAuth callback"""
    try:
        # Verify state
        if state and state not in oauth_states:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        # Remove used state
        if state:
            oauth_states.pop(state, None)
        
        # Get credentials
        creds = await db.credentials.find_one({})
        if not creds:
            raise HTTPException(status_code=400, detail="Credentials not found")
        
        redirect_uri = f"{os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')}/api/oauth/freeagent/callback"
        
        # Create OAuth service
        oauth = FreeAgentOAuth(
            client_id=creds.get('freeagent_client_id'),
            client_secret=creds.get('freeagent_client_secret'),
            redirect_uri=redirect_uri
        )
        
        # Exchange code for tokens
        token_data = await oauth.exchange_code_for_token(code)
        
        # Store tokens
        await db.credentials.update_one(
            {},
            {
                '$set': {
                    'freeagent_access_token': token_data.get('access_token'),
                    'freeagent_refresh_token': token_data.get('refresh_token'),
                    'freeagent_token_expires_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info("FreeAgent OAuth successful, tokens stored")
        
        # Redirect to frontend settings page
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(url=f"{frontend_url}/settings?oauth=success")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed: {str(e)}")
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(url=f"{frontend_url}/settings?oauth=error&message={str(e)}")


@api_router.post("/oauth/freeagent/disconnect")
async def freeagent_disconnect():
    """Disconnect FreeAgent (remove tokens)"""
    try:
        await db.credentials.update_one(
            {},
            {
                '$set': {
                    'freeagent_access_token': None,
                    'freeagent_refresh_token': None,
                    'freeagent_token_expires_at': None,
                    'updated_at': datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info("FreeAgent disconnected")
        return {"status": "success", "message": "FreeAgent disconnected successfully"}
        
    except Exception as e:
        logger.error(f"Disconnect failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/sync/manual")
async def manual_sync(background_tasks: BackgroundTasks):
    """Trigger manual sync"""
    try:
        # Get credentials
        creds = await db.credentials.find_one({})
        if not creds:
            raise HTTPException(status_code=400, detail="No credentials configured. Please configure credentials first.")
        
        # Check if we have FreeAgent tokens
        if not creds.get('freeagent_access_token'):
            raise HTTPException(status_code=400, detail="FreeAgent not connected. Please connect to FreeAgent first.")
        
        # Check if sync is already running
        running_sync = await db.sync_logs.find_one({'status': 'running'})
        if running_sync:
            raise HTTPException(status_code=400, detail="Sync is already running")
        
        # Create sync log
        sync_log = SyncLog(
            sync_type='manual',
            status='running',
            message='Starting manual sync...'
        )
        await db.sync_logs.insert_one(sync_log.dict())
        
        # Initialize services
        whmcs_service = WHMCSService(
            url=creds.get('whmcs_url'),
            identifier=creds.get('whmcs_identifier'),
            secret=creds.get('whmcs_secret')
        )
        
        freeagent_service = FreeAgentService(
            client_id=creds.get('freeagent_client_id'),
            client_secret=creds.get('freeagent_client_secret'),
            access_token=creds.get('freeagent_access_token'),
            refresh_token=creds.get('freeagent_refresh_token')
        )
        
        sync_service = SyncService(whmcs_service, freeagent_service, db)
        
        # Perform sync
        result = await sync_service.sync_invoices()
        
        # Update sync log
        sync_log.status = 'success'
        sync_log.invoices_processed = result.get('invoices_processed', 0)
        sync_log.invoices_created = result.get('invoices_created', 0)
        sync_log.clients_created = result.get('clients_created', 0)
        sync_log.message = result.get('message', 'Sync completed successfully')
        
        await db.sync_logs.update_one(
            {'id': sync_log.id},
            {'$set': sync_log.dict()}
        )
        
        logger.info(f"Manual sync completed: {result}")
        return {"status": "success", "result": result}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual sync failed: {str(e)}")
        
        # Update sync log if it exists
        if 'sync_log' in locals():
            sync_log.status = 'error'
            sync_log.errors = [str(e)]
            sync_log.message = f'Sync failed: {str(e)}'
            
            await db.sync_logs.update_one(
                {'id': sync_log.id},
                {'$set': sync_log.dict()}
            )
        
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/sync/status")
async def get_sync_status():
    """Get current sync status"""
    try:
        # Check if sync is running
        running_sync = await db.sync_logs.find_one({'status': 'running'})
        
        # Get last sync
        last_sync = await db.sync_logs.find_one(
            {'status': {'$in': ['success', 'error']}},
            sort=[('timestamp', -1)]
        )
        
        return {
            'is_running': bool(running_sync),
            'last_sync': last_sync.get('timestamp') if last_sync else None,
            'last_sync_status': last_sync.get('status') if last_sync else None,
            'next_sync': 'Every hour at :00'  # Since we run hourly
        }
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/sync/logs")
async def get_sync_logs(limit: int = 50):
    """Get sync logs"""
    try:
        logs = await db.sync_logs.find().sort('timestamp', -1).limit(limit).to_list(limit)
        # Remove MongoDB _id field
        for log in logs:
            log.pop('_id', None)
        return logs
    except Exception as e:
        logger.error(f"Error getting sync logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Start scheduler on app startup"""
    logger.info("Starting scheduler...")
    
    # Add job to run every hour at :00
    scheduler.add_job(
        perform_sync,
        CronTrigger(hour='*', minute='0'),  # Run every hour at :00
        id='hourly_sync',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler and database connection"""
    logger.info("Shutting down...")
    scheduler.shutdown()
    client.close()