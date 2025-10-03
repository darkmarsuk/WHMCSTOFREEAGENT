import React, { useState, useEffect } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Logs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 15000); // Refresh every 15 seconds
    return () => clearInterval(interval);
  }, []);
  
  const fetchLogs = async () => {
    try {
      const response = await axios.get(`${API}/sync/logs?limit=100`);
      setLogs(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching logs:", error);
      setLoading(false);
    }
  };
  
  const formatDate = (dateString) => {
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
          <h1 className="page-title">Sync Logs</h1>
          <p className="page-subtitle">Loading...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Sync Logs</h1>
        <p className="page-subtitle">View all synchronization history and details</p>
      </div>
      
      <div className="card">
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
          <h2 className="card-title" style={{marginBottom: 0}}>All Sync Logs</h2>
          <button
            className="btn btn-secondary"
            onClick={fetchLogs}
            data-testid="refresh-logs-btn"
          >
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
        
        {logs.length === 0 ? (
          <div className="empty-state">
            <svg className="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <div className="empty-title">No sync logs yet</div>
            <p className="empty-text">Sync logs will appear here once you run your first sync.</p>
          </div>
        ) : (
          <div>
            {logs.map((log) => (
              <div key={log.id} className="log-entry" data-testid="sync-log-entry">
                <div className="log-header">
                  <span className="log-type">{log.sync_type} SYNC</span>
                  <span className={`status-badge ${getStatusClass(log.status)}`}>
                    {log.status}
                  </span>
                </div>
                
                <div className="log-time">{formatDate(log.timestamp)}</div>
                
                <div className="log-message">{log.message}</div>
                
                {log.status === 'success' && (
                  <div className="log-stats">
                    <span className="log-stat">
                      <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      {log.invoices_processed} processed
                    </span>
                    <span className="log-stat">
                      <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {log.invoices_created} created
                    </span>
                    <span className="log-stat">
                      <svg style={{width: '16px', height: '16px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                      </svg>
                      {log.clients_created} new clients
                    </span>
                  </div>
                )}
                
                {log.errors && log.errors.length > 0 && (
                  <div style={{marginTop: '1rem'}}>
                    <div style={{fontSize: '0.875rem', fontWeight: '600', color: '#991b1b', marginBottom: '0.5rem'}}>
                      Errors:
                    </div>
                    <ul style={{paddingLeft: '1.5rem', color: '#dc2626', fontSize: '0.875rem'}}>
                      {log.errors.map((error, idx) => (
                        <li key={idx} style={{marginBottom: '0.25rem'}}>{error}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Logs;