"use client";
import { useEffect, useRef, useCallback } from "react";
import Cookies from "js-cookie";

export function useWebSocket(onMessage: (data: any) => void) {
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    const token = Cookies.get("token");
    if (!token) return;

    try {
      // In production, NEXT_PUBLIC_WS_URL points to the Render backend (e.g. wss://cybershield-backend.onrender.com/ws)
      // In development, falls back to localhost
      const wsBase = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
      ws.current = new WebSocket(`${wsBase}?token=${token}`);

      ws.current.onmessage = (e) => {
        try { onMessage(JSON.parse(e.data)); } catch {}
      };

      ws.current.onclose = () => {
        reconnectTimer.current = setTimeout(connect, 5000);
      };

      // Ping every 30s
      const ping = setInterval(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send("ping");
        }
      }, 30000);

      ws.current.onerror = () => clearInterval(ping);
    } catch {}
  }, [onMessage]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      ws.current?.close();
    };
  }, [connect]);
}
