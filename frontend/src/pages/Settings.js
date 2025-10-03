import React, { useState, useEffect } from "react";
import axios from "axios";
import { useSearchParams } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Settings = () => {
  const [searchParams] = useSearchParams();
  const [credentials, setCredentials] = useState({
    whmcs_url: "",
    whmcs_identifier: "",
    whmcs_secret: "",
    freeagent_client_id: "",
    freeagent_client_secret: "",
  });
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [alert, setAlert] = useState(null);
  
  useEffect(() => {
    fetchCredentials();
    
    // Check for OAuth callback
    const oauthStatus = searchParams.get('oauth');
    if (oauthStatus === 'success') {
      setAlert({
        type: "success",
        message: "Successfully connected to FreeAgent!"
      });
      // Remove query params
      window.history.replaceState({}, '', '/settings');
    } else if (oauthStatus === 'error') {
      const errorMsg = searchParams.get('message') || 'Failed to connect to FreeAgent';
      setAlert({
        type: "error",
        message: errorMsg
      });
      // Remove query params
      window.history.replaceState({}, '', '/settings');
    }
  }, [searchParams]);
  
  const fetchCredentials = async () => {
    try {
      const response = await axios.get(`${API}/settings/credentials`);
      if (response.data) {
        setCredentials({
          whmcs_url: response.data.whmcs_url || "",
          whmcs_identifier: "",
          whmcs_secret: "",
          freeagent_client_id: response.data.freeagent_client_id || "",
          freeagent_client_secret: "",
        });
        setIsConnected(response.data.is_connected || false);
      }
      setLoading(false);
    } catch (error) {
      console.error("Error fetching credentials:", error);
      setLoading(false);
    }
  };
  
  const handleChange = (e) => {
    const { name, value } = e.target;
    setCredentials(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      setSaving(true);
      setAlert(null);
      
      await axios.post(`${API}/settings/credentials`, credentials);
      
      setAlert({
        type: "success",
        message: "Credentials saved successfully!"
      });
      
      // Refresh to get connection status
      await fetchCredentials();
      
    } catch (error) {
      console.error("Error saving credentials:", error);
      setAlert({
        type: "error",
        message: error.response?.data?.detail || "Failed to save credentials"
      });
    } finally {
      setSaving(false);
    }
  };
  
  const handleConnectFreeAgent = async () => {
    try {
      setConnecting(true);
      setAlert(null);
      
      const response = await axios.get(`${API}/oauth/freeagent/authorize`);
      
      // Redirect to FreeAgent authorization page
      window.location.href = response.data.authorization_url;
      
    } catch (error) {
      console.error("Error connecting to FreeAgent:", error);
      setAlert({
        type: "error",
        message: error.response?.data?.detail || "Failed to initiate FreeAgent connection"
      });
      setConnecting(false);
    }
  };
  
  const handleDisconnectFreeAgent = async () => {
    if (!window.confirm('Are you sure you want to disconnect from FreeAgent?')) {
      return;
    }
    
    try {
      setDisconnecting(true);
      setAlert(null);
      
      await axios.post(`${API}/oauth/freeagent/disconnect`);
      
      setAlert({
        type: "success",
        message: "Disconnected from FreeAgent successfully"
      });
      
      setIsConnected(false);
      
    } catch (error) {
      console.error("Error disconnecting:", error);
      setAlert({
        type: "error",
        message: error.response?.data?.detail || "Failed to disconnect"
      });
    } finally {
      setDisconnecting(false);
    }
  };
  
  if (loading) {
    return (
      <div className="page-container">
        <div className="page-header">
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Loading...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Configure your WHMCS and FreeAgent API credentials</p>
      </div>
      
      {alert && (
        <div className={`alert alert-${alert.type}`}>
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          <div>{alert.message}</div>
        </div>
      )}
      
      <div className="card">
        <h2 className="card-title">WHMCS Credentials</h2>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">WHMCS URL</label>
            <input
              type="url"
              name="whmcs_url"
              className="form-input"
              placeholder="https://your-domain.com/whmcs"
              value={credentials.whmcs_url}
              onChange={handleChange}
              required
              data-testid="whmcs-url-input"
            />
            <p style={{fontSize: '0.875rem', color: '#64748b', marginTop: '0.5rem'}}>
              Your WHMCS installation URL
            </p>
          </div>
          
          <div className="form-group">
            <label className="form-label">API Identifier</label>
            <input
              type="text"
              name="whmcs_identifier"
              className="form-input"
              placeholder="Enter your WHMCS API Identifier"
              value={credentials.whmcs_identifier}
              onChange={handleChange}
              required
              data-testid="whmcs-identifier-input"
            />
          </div>
          
          <div className="form-group">
            <label className="form-label">API Secret</label>
            <input
              type="password"
              name="whmcs_secret"
              className="form-input"
              placeholder="Enter your WHMCS API Secret"
              value={credentials.whmcs_secret}
              onChange={handleChange}
              required
              data-testid="whmcs-secret-input"
            />
          </div>
          
          <hr style={{margin: '2rem 0', border: 'none', borderTop: '1px solid #e2e8f0'}} />
          
          <h2 className="card-title">FreeAgent Credentials</h2>
          
          <div className="form-group">
            <label className="form-label">OAuth Client ID</label>
            <input
              type="text"
              name="freeagent_client_id"
              className="form-input"
              placeholder="1KPjokVRmomFNRVgQgqgEw"
              value={credentials.freeagent_client_id}
              onChange={handleChange}
              required
              data-testid="freeagent-client-id-input"
            />
          </div>
          
          <div className="form-group">
            <label className="form-label">OAuth Client Secret</label>
            <input
              type="password"
              name="freeagent_client_secret"
              className="form-input"
              placeholder="wzFQffiI6AkmY3zf9bHhJA"
              value={credentials.freeagent_client_secret}
              onChange={handleChange}
              required
              data-testid="freeagent-client-secret-input"
            />
          </div>
          
          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
            style={{marginTop: '1rem'}}
            data-testid="save-credentials-btn"
          >
            {saving ? (
              <>
                <span className="spinner"></span>
                Saving...
              </>
            ) : (
              <>
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Save Credentials
              </>
            )}
          </button>
          
          <hr style={{margin: '2rem 0', border: 'none', borderTop: '1px solid #e2e8f0'}} />
          
          <h3 className="card-title" style={{fontSize: '1.1rem'}}>FreeAgent Connection</h3>
          
          {isConnected ? (
            <div>
              <div className={`alert alert-success`} style={{marginBottom: '1rem'}}>
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <div>
                  <strong>Connected to FreeAgent</strong><br/>
                  You can now sync invoices from WHMCS to FreeAgent.
                </div>
              </div>
              
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleDisconnectFreeAgent}
                disabled={disconnecting}
                data-testid="disconnect-freeagent-btn"
              >
                {disconnecting ? (
                  <>
                    <span className="spinner" style={{borderTopColor: '#667eea'}}></span>
                    Disconnecting...
                  </>
                ) : (
                  <>
                    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    Disconnect from FreeAgent
                  </>
                )}
              </button>
            </div>
          ) : (
            <div>
              <div className={`alert alert-warning`} style={{marginBottom: '1rem'}}>
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div>
                  <strong>Not Connected</strong><br/>
                  Save your credentials above, then connect to FreeAgent to enable syncing.
                </div>
              </div>
              
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleConnectFreeAgent}
                disabled={connecting || !credentials.freeagent_client_id}
                data-testid="connect-freeagent-btn"
              >
                {connecting ? (
                  <>
                    <span className="spinner"></span>
                    Connecting...
                  </>
                ) : (
                  <>
                    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    Connect to FreeAgent
                  </>
                )}
              </button>
            </div>
          )}
          
          <div className={`alert alert-info`} style={{marginTop: '1.5rem'}}>
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <div>
              <strong>How it works:</strong> After saving your credentials, click "Connect to FreeAgent" to authorize this app. 
              You'll be redirected to FreeAgent to approve access, then back here with full sync capabilities.
            </div>
          </div>
        </form>
      </div>
      
      <div className="card">
        <h2 className="card-title">How to Get API Credentials</h2>
        
        <div style={{color: '#475569', lineHeight: '1.7'}}>
          <h3 style={{fontSize: '1.1rem', fontWeight: '600', marginTop: '1.5rem', marginBottom: '0.75rem'}}>
            WHMCS API Credentials
          </h3>
          <ol style={{paddingLeft: '1.5rem'}}>
            <li style={{marginBottom: '0.5rem'}}>Log in to your WHMCS admin area</li>
            <li style={{marginBottom: '0.5rem'}}>Go to Setup → Staff Management → Manage API Credentials</li>
            <li style={{marginBottom: '0.5rem'}}>Click "Generate New API Credential"</li>
            <li style={{marginBottom: '0.5rem'}}>Copy the Identifier and Secret</li>
          </ol>
          
          <h3 style={{fontSize: '1.1rem', fontWeight: '600', marginTop: '1.5rem', marginBottom: '0.75rem'}}>
            FreeAgent OAuth Credentials
          </h3>
          <ol style={{paddingLeft: '1.5rem'}}>
            <li style={{marginBottom: '0.5rem'}}>Log in to your FreeAgent account</li>
            <li style={{marginBottom: '0.5rem'}}>Go to Settings → Developer → OAuth Applications</li>
            <li style={{marginBottom: '0.5rem'}}>Create a new OAuth application</li>
            <li style={{marginBottom: '0.5rem'}}>Set the redirect URL to: <code style={{background: '#f1f5f9', padding: '0.25rem 0.5rem', borderRadius: '4px'}}>{BACKEND_URL}/api/oauth/freeagent/callback</code></li>
            <li style={{marginBottom: '0.5rem'}}>Copy the Client ID and Client Secret</li>
          </ol>
        </div>
      </div>
    </div>
  );
};

export default Settings;