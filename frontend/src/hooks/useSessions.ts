/**
 * Lenny Growth Assistant — Session State Management Hook
 *
 * Manages:
 * - Anonymous user identity generation and persistence via localStorage
 * - Session list fetching and active session selection
 * - New session creation, title updates, and deletion
 */

import { useCallback, useEffect, useState } from "react";
import {
  createSession as apiCreateSession,
  deleteSession as apiDeleteSession,
  getSession as apiGetSession,
  listSessions as apiListSessions,
  updateSessionTitle as apiUpdateSessionTitle,
} from "../lib/api";
import { getOrCreateAnonymousIdentifier } from "../lib/identity";
import type { Artifact, Message, SessionDetail, SessionSummary } from "../types/session";

export function useSessions() {
  const [anonymousId, setAnonymousId] = useState<string>("");
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<SessionDetail | null>(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState<boolean>(true);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);
  const [sessionError, setSessionError] = useState<string | null>(null);

  // 1. Initialize anonymous identity on mount
  useEffect(() => {
    const id = getOrCreateAnonymousIdentifier();
    setAnonymousId(id);
  }, []);

  // 2. Fetch session list whenever anonymousId is established
  const refreshSessions = useCallback(async () => {
    if (!anonymousId) return;

    try {
      setIsLoadingSessions(true);
      setSessionError(null);
      const items = await apiListSessions(anonymousId);
      setSessions(items);

      // If active session not selected and sessions exist, select first
      if (!activeSessionId && items.length > 0) {
        setActiveSessionId(items[0].id);
      }
    } catch (err: any) {
      setSessionError(err.message || "Failed to load conversations");
    } finally {
      setIsLoadingSessions(false);
    }
  }, [anonymousId, activeSessionId]);

  useEffect(() => {
    if (anonymousId) {
      refreshSessions();
    }
  }, [anonymousId, refreshSessions]);

  // 3. Load full history whenever activeSessionId changes
  const loadActiveSessionHistory = useCallback(async (sessionId: string) => {
    try {
      setIsLoadingHistory(true);
      setSessionError(null);
      const detail = await apiGetSession(sessionId);
      setActiveSession(detail);
    } catch (err: any) {
      setSessionError(err.message || "Failed to load session history");
      setActiveSession(null);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    if (activeSessionId) {
      loadActiveSessionHistory(activeSessionId);
    } else {
      setActiveSession(null);
    }
  }, [activeSessionId, loadActiveSessionHistory]);

  // 4. Create new conversation session
  const createNewSession = useCallback(
    async (title: string = "New Conversation"): Promise<string | null> => {
      if (!anonymousId) return null;

      try {
        setSessionError(null);
        const created = await apiCreateSession(anonymousId, title);
        const newSummary: SessionSummary = {
          id: created.id,
          title: created.title,
          updated_at: created.updated_at,
        };

        setSessions((prev) => [newSummary, ...prev]);
        setActiveSessionId(created.id);
        return created.id;
      } catch (err: any) {
        setSessionError(err.message || "Failed to create new conversation");
        return null;
      }
    },
    [anonymousId]
  );

  // 5. Update session title
  const renameSession = useCallback(
    async (sessionId: string, newTitle: string) => {
      try {
        const updated = await apiUpdateSessionTitle(sessionId, newTitle);
        setSessions((prev) =>
          prev.map((s) => (s.id === sessionId ? { ...s, title: updated.title } : s))
        );
        setActiveSession((prev) => (prev && prev.id === sessionId ? { ...prev, title: updated.title } : prev));
      } catch (err: any) {
        setSessionError(err.message || "Failed to update session title");
      }
    },
    []
  );

  // 6. Delete session
  const deleteSession = useCallback(
    async (sessionId: string) => {
      try {
        await apiDeleteSession(sessionId);
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        if (activeSessionId === sessionId) {
          setActiveSessionId(null);
          setActiveSession(null);
        }
      } catch (err: any) {
        setSessionError(err.message || "Failed to delete conversation");
      }
    },
    [activeSessionId]
  );

  // 7. Optimistic local message appends (e.g. after streaming completes)
  const appendMessageToActive = useCallback((msg: Message) => {
    setActiveSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        messages: [...prev.messages, msg],
      };
    });
  }, []);

  // 8. Optimistic local artifact appends
  const appendArtifactToActive = useCallback((artifact: Artifact) => {
    setActiveSession((prev) => {
      if (!prev) return prev;
      const currentArtifacts = prev.artifacts || [];
      const exists = currentArtifacts.some((a) => a.id === artifact.id);
      return {
        ...prev,
        artifacts: exists ? currentArtifacts : [...currentArtifacts, artifact],
      };
    });
  }, []);

  return {
    anonymousId,
    sessions,
    activeSessionId,
    activeSession,
    isLoadingSessions,
    isLoadingHistory,
    sessionError,
    setActiveSessionId,
    createNewSession,
    renameSession,
    deleteSession,
    refreshSessions,
    appendMessageToActive,
    appendArtifactToActive,
    loadActiveSessionHistory,
  };
}
