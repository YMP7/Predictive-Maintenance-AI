import { useState, useEffect } from 'react';
import { apiFetch } from '../lib/api';

export interface MachineInfo {
  name: string;
  type: string;
  location: string;
}

export interface MachineStatus {
  machine_id: string;
  status: string;
  fault_type: string;
  detected_issues: string[];
  rul_days: number | null;
  rul_confidence: number;
  recommendation: string;
  machine_info: MachineInfo;
}

export interface DashboardSummary {
  timestamp: string;
  total_machines: number;
  machine_status_counts: {
    Normal: number;
    Warning: number;
    Critical: number;
  };
  alert_severity_counts: {
    Critical: number;
    High: number;
    Medium: number;
    Low: number;
  };
  average_rul_days: number;
  total_alerts: number;
  machines: MachineStatus[];
}

export function useDashboardData(refreshInterval: number = 2000) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const fetchData = async () => {
      try {
        const data = await apiFetch<DashboardSummary>('/api/dashboard/summary');
        if (active) {
          setSummary(data);
          setError(null);
        }
      } catch (err: any) {
        if (active) {
          setError(err.message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    fetchData();
    const interval = setInterval(fetchData, refreshInterval);
    
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [refreshInterval]);

  return { summary, loading, error };
}

export function useMachineDetails(machineId: string | null, refreshInterval: number = 2000) {
  const [telemetry, setTelemetry] = useState<any[]>([]);
  const [trends, setTrends] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!machineId) return;
    
    let active = true;
    const fetchDetails = async () => {
      try {
        setLoading(true);
        // Telemetry
        const telData = await apiFetch<any[]>(`/api/machines/${machineId}/telemetry?limit=50`);
        
        // Trends
        const trendData = await apiFetch<any>(`/api/machines/${machineId}/trends`);
        
        if (active) {
          setTelemetry(telData);
          setTrends(trendData);
          setError(null);
        }
      } catch (err: any) {
        if (active) {
          setError(err.message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    fetchDetails();
    const interval = setInterval(fetchDetails, refreshInterval);
    
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [machineId, refreshInterval]);

  return { telemetry, trends, loading, error };
}
