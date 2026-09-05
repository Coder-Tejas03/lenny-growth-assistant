/**
 * Lenny Growth Assistant — Main Application Page
 *
 * Assembles:
 * - Header (Brand, Health Diagnostics, Model Selector, Mobile Toggle)
 * - SessionList (Sidebar with New Chat and conversation history)
 * - ChatPane (Conversation timeline, streaming turns, citations, and Composer)
 *
 * Implements full responsive behavior and session reload per design.md.
 */

"use client";

import React, { useEffect, useState } from "react";
import { Header } from "../components/Layout/Header";
import { SessionList } from "../components/Session/SessionList";
import { ChatPane } from "../components/Chat/ChatPane";
import { ArtifactViewer } from "../components/Artifact";
import { useSessions } from "../hooks/useSessions";
import { useChatStream } from "../hooks/useChatStream";
import { ChatMode, ChatProvider } from "../types/chat";
import { Artifact, Message } from "../types/session";

export default function Home() {
  const [selectedProvider, setSelectedProvider] = useState<ChatProvider>("openai");
  const [selectedModel, setSelectedModel] = useState<string>("gpt-4o-mini");
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);

  // 1. Session state management
  const {
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
  } = useSessions();

  // Reset active artifact if switching to a session without it
  useEffect(() => {
    if (activeSession?.artifacts && activeSession.artifacts.length > 0) {
      if (activeArtifact && !activeSession.artifacts.some((a) => a.id === activeArtifact.id)) {
        setActiveArtifact(null);
      }
    } else {
      setActiveArtifact(null);
    }
  }, [activeSessionId]);

  // 2. Real-time SSE chat streaming hook
  const {
    status,
    statusMessage,
    streamingContent,
    citations,
    error: streamError,
    errorInfo,
    isStreaming,
    sendMessage,
    abortStream,
  } = useChatStream({
    sessionId: activeSessionId,
    onMessageCompleted: (completedMessage) => {
      appendMessageToActive(completedMessage);
      refreshSessions();
      if (activeSessionId) {
        loadActiveSessionHistory(activeSessionId);
      }
    },
    onArtifactCreated: (createdArtifact) => {
      setActiveArtifact(createdArtifact);
      appendArtifactToActive(createdArtifact);
      refreshSessions();
    },
  });

  // Handle user query submission
  const handleSendMessage = async (query: string, mode: ChatMode) => {
    let targetSessionId = activeSessionId;

    // If no active session, create one automatically
    if (!targetSessionId) {
      const generatedTitle =
        query.length > 36 ? query.slice(0, 36) + "..." : query;
      targetSessionId = await createNewSession(generatedTitle);
      if (!targetSessionId) return;
    }

    // Optimistically add user query to conversation timeline
    const userMessage: Message = {
      id: "user_msg_" + crypto.randomUUID(),
      role: "user",
      content: query,
      created_at: new Date().toISOString(),
    };
    appendMessageToActive(userMessage);

    // Send query to FastAPI SSE streaming endpoint
    await sendMessage(query, {
      provider: selectedProvider,
      model: selectedModel,
      mode: mode,
    });
  };

  const handleSelectModel = (provider: ChatProvider, model: string) => {
    setSelectedProvider(provider);
    setSelectedModel(model);
  };

  const handleSelectSession = (id: string) => {
    if (isStreaming) {
      abortStream();
    }
    setActiveSessionId(id);
    setIsSidebarOpen(false); // Close mobile drawer on selection
  };

  const handleNewChat = async () => {
    if (isStreaming) {
      abortStream();
    }
    await createNewSession("New Conversation");
    setIsSidebarOpen(false);
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-surface-950 text-slate-100">
      {/* Top Application Header */}
      <Header
        selectedProvider={selectedProvider}
        selectedModel={selectedModel}
        onSelectModel={handleSelectModel}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        isStreaming={isStreaming}
        hasArtifact={Boolean(activeSession?.artifacts && activeSession.artifacts.length > 0)}
        isArtifactOpen={Boolean(activeArtifact)}
        onToggleArtifact={() => {
          if (activeArtifact) {
            setActiveArtifact(null);
          } else if (activeSession?.artifacts && activeSession.artifacts.length > 0) {
            setActiveArtifact(
              activeSession.artifacts[activeSession.artifacts.length - 1]
            );
          }
        }}
      />

      {/* Main Workspace: Sidebar + Chat Pane + Artifact Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Desktop Sidebar */}
        <SessionList
          sessions={sessions}
          activeSessionId={activeSessionId}
          isLoading={isLoadingSessions}
          error={sessionError}
          anonymousId={anonymousId}
          onSelectSession={handleSelectSession}
          onNewChat={handleNewChat}
          onRenameSession={renameSession}
          onDeleteSession={deleteSession}
          onRetry={refreshSessions}
          className="hidden md:flex"
        />

        {/* Mobile Slide-over Drawer */}
        {isSidebarOpen && (
          <div className="fixed inset-0 z-40 md:hidden flex">
            <div
              className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
              onClick={() => setIsSidebarOpen(false)}
              aria-hidden="true"
            />
            <div className="relative z-50 flex-1 max-w-xs w-full bg-surface-950 h-full shadow-2xl animate-fade-in">
              <SessionList
                sessions={sessions}
                activeSessionId={activeSessionId}
                isLoading={isLoadingSessions}
                error={sessionError}
                anonymousId={anonymousId}
                onSelectSession={handleSelectSession}
                onNewChat={handleNewChat}
                onRenameSession={renameSession}
                onDeleteSession={deleteSession}
                onRetry={refreshSessions}
                className="w-full"
              />
            </div>
          </div>
        )}

        {/* Primary Chat Conversation Pane */}
        <div
          className={`flex-1 flex flex-col h-full min-w-0 transition-all duration-300 ${
            activeArtifact ? "hidden md:flex md:w-1/2 lg:w-3/5" : "w-full"
          }`}
        >
          <ChatPane
            messages={activeSession?.messages || []}
            streamingContent={streamingContent}
            streamingStatus={status}
            streamingStatusMessage={statusMessage}
            citations={citations}
            error={streamError}
            errorInfo={errorInfo}
            activeProvider={selectedProvider}
            activeModel={selectedModel}
            onSendMessage={handleSendMessage}
            onAbortStream={abortStream}
            onSelectModel={handleSelectModel}
            isLoadingHistory={isLoadingHistory}
            artifacts={activeSession?.artifacts || []}
            onViewArtifact={(art) => setActiveArtifact(art)}
            activeArtifactId={activeArtifact?.id}
          />
        </div>

        {/* Desktop Artifact Workspace Pane (Side-by-Side Dual-Pane) */}
        {activeArtifact && (
          <div className="hidden md:flex md:w-1/2 lg:w-2/5 h-full border-l border-surface-800 transition-all duration-300 animate-fade-in">
            <ArtifactViewer
              artifact={activeArtifact}
              onClose={() => setActiveArtifact(null)}
              className="w-full h-full"
            />
          </div>
        )}

        {/* Mobile Artifact Workspace Drawer (Full Screen / Slide-over) */}
        {activeArtifact && (
          <div className="fixed inset-0 z-50 md:hidden flex flex-col bg-surface-950 animate-fade-in">
            <ArtifactViewer
              artifact={activeArtifact}
              onClose={() => setActiveArtifact(null)}
              className="w-full h-full border-none"
            />
          </div>
        )}
      </div>
    </div>
  );
}
