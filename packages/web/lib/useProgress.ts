/**
 * React hook for real-time project progress via WebSocket.
 *
 * Usage:
 *   const { progress, isConnected } = useProgress(projectId);
 *
 * Progress shape:
 *   { progress_pct, total_tasks, completed, in_progress, failed, engines, is_complete }
 */
import { useEffect, useRef, useState, useCallback } from 'react';

export interface EngineProgress {
  engine: string;
  status: string;
  total: number;
  done: number;
  ok: number;
  fail: number;
}

export interface ProjectProgress {
  type: string;
  project_id: string;
  total_tasks: number;
  completed: number;
  in_progress: number;
  failed: number;
  progress_pct: number;
  engines: EngineProgress[];
  is_complete: boolean;
  timestamp?: string;
}

export function useProgress(projectId: string | null) {
  const [progress, setProgress] = useState<ProjectProgress | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!projectId) return;

    const token =
      typeof window !== 'undefined'
        ? localStorage.getItem('access_token') ||
          sessionStorage.getItem('access_token')
        : null;

    if (!token) return;

    // Build WS URL
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const wsBase = apiBase
      .replace(/^http/, 'ws')
      .replace(/\/$/, '');
    const wsUrl = `${wsBase}/ws/progress?token=${encodeURIComponent(token)}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        // Subscribe to project
        ws.send(
          JSON.stringify({ type: 'subscribe', project_id: projectId })
        );
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as ProjectProgress;
          if (data.type === 'progress') {
            setProgress(data);
          }
        } catch {
          // Ignore parse errors
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Reconnect after 5 seconds if not complete
        if (!progress?.is_complete) {
          reconnectRef.current = setTimeout(connect, 5000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // WebSocket not supported or connection failed
    }
  }, [projectId]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { progress, isConnected };
}
