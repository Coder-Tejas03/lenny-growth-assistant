/**
 * Lenny Growth Assistant — Citation Types
 *
 * Matches CitationResponse from backend/app/schemas/session.py
 * and Section 7 of docs/implementation-contract.md.
 */

export interface Citation {
  chunk_id: string;
  episode_title: string;
  guest_name: string;
  timestamp?: string | null;
  source_url?: string | null;
  similarity: number;
  excerpt?: string | null;
}
