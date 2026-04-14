import { useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import { frontendApi } from '../api/frontend';
import { resolveApiBaseUrl, resolveApiOrigin } from '../api/resolveApiUrl';
import { useAppStore } from '../store/useAppStore';

const DELTA_EVENT_NAMES = [
  'lab.updated',
  'visit.updated',
  'specialist.updated',
  'dashboard.metrics.updated',
] as const;

export function useRealTimeUpdates() {
  const initializeData = useAppStore((state) => state.initializeData);
  const mergeDelta = useAppStore((state) => state.mergeDelta);
  const updateLabQueue = useAppStore((state) => state.updateLabQueue);
  const lastDeltaAt = useAppStore((state) => state.lastDeltaAt);
  const lastDeltaAtRef = useRef<Date | null>(lastDeltaAt);
  const socketConnectedRef = useRef(false);
  const pollTimerRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    lastDeltaAtRef.current = lastDeltaAt;
  }, [lastDeltaAt]);

  useEffect(() => {
    const apiBaseUrl = resolveApiOrigin();
    const healthUrl = `${resolveApiBaseUrl().replace(/\/$/, '')}/health`;
    let socket: ReturnType<typeof io> | null = null;
    let retryTimer: number | undefined;
    let cancelled = false;

    const clearPoll = () => {
      if (pollTimerRef.current) {
        window.clearTimeout(pollTimerRef.current);
        pollTimerRef.current = undefined;
      }
    };

    const syncDelta = async (fallbackToBootstrap = false) => {
      try {
        const payload = await frontendApi.delta(lastDeltaAtRef.current);
        mergeDelta(payload);
        lastDeltaAtRef.current = payload.now ? new Date(payload.now) : lastDeltaAtRef.current;
      } catch (error) {
        console.error('Delta sync failed', error);
        if (fallbackToBootstrap) {
          await initializeData();
          lastDeltaAtRef.current = new Date();
        }
      }
    };

    const schedulePoll = () => {
      if (cancelled || socketConnectedRef.current) {
        return;
      }
      clearPoll();
      pollTimerRef.current = window.setTimeout(() => {
        void syncDelta();
        schedulePoll();
      }, 5000);
    };

    const connectRealtime = async () => {
      try {
        const response = await fetch(healthUrl);
        if (!response.ok || cancelled) {
          throw new Error('Backend health check failed');
        }
      } catch {
        if (!cancelled) {
          retryTimer = window.setTimeout(connectRealtime, 5000);
        }
        schedulePoll();
        return;
      }

      if (cancelled) {
        return;
      }

      socket = io(apiBaseUrl, {
        transports: ['websocket'],
        autoConnect: true,
        reconnectionAttempts: 3,
        reconnectionDelay: 2000,
      });

      socket.on('connect', () => {
        socketConnectedRef.current = true;
        clearPoll();
        void syncDelta(true);
      });

      socket.on('disconnect', () => {
        socketConnectedRef.current = false;
        schedulePoll();
      });

      socket.on('connect_error', () => {
        socket?.disconnect();
        socket = null;
        socketConnectedRef.current = false;
        schedulePoll();
        if (!cancelled) {
          if (retryTimer) window.clearTimeout(retryTimer);
          retryTimer = window.setTimeout(connectRealtime, 5000);
        }
      });

      socket.on('queue.updated', (payload: { labId: string; snapshot: { current?: { visit_id: string } | null; next?: { visit_id: string } | null; pending?: Array<{ visit_id: string }> } }) => {
        updateLabQueue(payload.labId, payload.snapshot ?? {});
      });

      DELTA_EVENT_NAMES.forEach((eventName) => {
        socket?.on(eventName, () => {
          void syncDelta();
        });
      });
    };

    void connectRealtime();
    schedulePoll();

    return () => {
      cancelled = true;
      socketConnectedRef.current = false;
      clearPoll();
      if (retryTimer) {
        window.clearTimeout(retryTimer);
      }
      socket?.disconnect();
    };
  }, [initializeData, mergeDelta, updateLabQueue]);
}
