import React, { useState, useEffect } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [syncStatus, setSyncStatus] = useState(null);
  const [recentLogs, setRecentLogs] = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [alert, setAlert] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);
  
  const fetchData = async () => {
    try {
      const [statusRes, logsRes] = await Promise.all([
        axios.get(`${API}/sync/status`),
        axios.get(`${API}/sync/logs?limit=5`)
      ]);
      
      setSyncStatus(statusRes.data);
      setRecentLogs(logsRes.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching data:", error);
      setLoading(false);
    }
  };
  
  const handleManualSync = async () => {
    try {
      setSyncing(true);
      setAlert(null);
      
      const response = await axios.post(`${API}/sync/manual`);
      
      setAlert({
        type: "success",
        message: response.data.result.message || "Sync completed successfully!"
      });
      
      // Refresh data
      await fetchData();
      
    } catch (error) {
      console.error("Sync error:", error);
      setAlert({
        type: "error",
        message: error.response?.data?.detail || "Sync failed. Please check your settings and try again."
      });
    } finally {
      setSyncing(false);
    }
  };
  
  const formatDate = (dateString) => {
    if (!dateString) return "Never";
    const date = new Date(dateString);
    return date.toLocaleString();
  };
  
  const getStatusClass = (status) => {
    switch (status) {
      case "success": return "status-success";
      case "error": return "status-error";
      case "running": return "status-running";
      default: return "status-warning";
    }
  };
  
  if (loading) {
    return (
      <div className="page-container">
        <div className="page-header">
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Loading...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Sync invoices from WHMCS to FreeAgent</p>
      </div>
      
      {alert && (
        <div className={`alert alert-${alert.type}`}>
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <div>{alert.message}</div>
        </div>
      )}
      
      <div className="stats-grid">
        <div className="stat-card">
          <svg className="stat-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="stat-label">Last Sync</div>
          <div className="stat-value" style={{fontSize: '1.25rem'}}>
            {formatDate(syncStatus?.last_sync)}
          </div>
          <div className="stat-label" style={{marginTop: '0.5rem'}}>
            Status: <span className={`status-badge ${getStatusClass(syncStatus?.last_sync_status)}`}>
              {syncStatus?.last_sync_status || "Never"}
            </span>
          </div>
        </div>
        
        <div className="stat-card">
          <svg className="stat-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <div className="stat-label">Next Automatic Sync</div>
          <div className="stat-value" style={{fontSize: '1.25rem'}}>
            {syncStatus?.next_sync || "Not scheduled"}
          </div>
        </div>
        
        <div className="stat-card">
          <svg className="stat-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="stat-label">Sync Status</div>
          <div className="stat-value" style={{fontSize: '1.25rem'}}>
            {syncStatus?.is_running ? (
              <span className="status-badge status-running">Running</span>
            ) : (
              <span className="status-badge status-success">Ready</span>
            )}
          </div>
        </div>
      </div>
      
      <div className="card">
        <h2 className="card-title">Manual Sync</h2>
        <p style={{color: '#64748b', marginBottom: '1.5rem'}}>
          Trigger a manual sync to import invoices from WHMCS to FreeAgent immediately.
        </p>
        
        <button
          className="btn btn-primary"
          onClick={handleManualSync}
          disabled={syncing || syncStatus?.is_running}
          data-testid="manual-sync-btn"
        >
          {syncing || syncStatus?.is_running ? (
            <>
              <span className="spinner"></span>
              Syncing...
            </>
          ) : (
            <>
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Start Manual Sync
            </>
          )}
        </button>
      </div>
      
      <div className="card">
        <h2 className="card-title">Recent Sync Logs</h2>
        
        {recentLogs.length === 0 ? (
          <div className="empty-state">
            <svg className="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <div className="empty-title">No sync logs yet</div>
            <p className="empty-text">Sync logs will appear here once you run your first sync.</p>
          </div>
        ) : (
          recentLogs.map((log) => (
            <div key={log.id} className="log-entry">
              <div className="log-header">
                <span className="log-type">{log.sync_type}</span>
                <span className={`status-badge ${getStatusClass(log.status)}`}>
                  {log.status}
                </span>
              </div>
              <div className="log-time">{formatDate(log.timestamp)}</div>
              <div className="log-message">{log.message}</div>
              {log.status === 'success' && (
                <div className="log-stats">
                  <span className="log-stat">
                    📄 {log.invoices_processed} processed
                  </span>
                  <span className="log-stat">
                    ✅ {log.invoices_created} created
                  </span>
                  <span className="log-stat">
                    👥 {log.clients_created} new clients
                  </span>
                  {log.payments_synced > 0 && (
                    <span className="log-stat">
                      💰 {log.payments_synced} payments synced
                    </span>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Dashboard;