/**
 * Typed API client — single source of truth for backend communication.
 *
 * Use these functions instead of raw fetch() so components stay declarative
 * and don't know URLs. All requests use credentials: 'include' for the
 * session cookie. Errors throw with a useful message rather than returning
 * non-ok responses.
 */
import type { SkippedFile } from '../lib/folderData';

// In dev, VITE_API_BASE_URL is unset so relative paths flow through the
// Vite proxy. In prod (cross-origin deploy), set VITE_API_BASE_URL to the
// backend's absolute URL.
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = (data as { message?: string; error?: string })?.message
      ?? (data as { message?: string; error?: string })?.error
      ?? `HTTP ${res.status}`;
    throw new ApiError(res.status, msg);
  }
  return data as T;
}

// ── Auth ─────────────────────────────────────────────────────────────────

export interface UserPayload {
  id: string;
  name: string;
  email: string;
  picture?: string;
}

export async function getCurrentUser(): Promise<UserPayload | null> {
  try {
    const data = await request<{ user: UserPayload | null }>('/api/auth/me');
    return data.user;
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return null;
    throw e;
  }
}

export async function signInWithGoogle(code: string): Promise<UserPayload> {
  const data = await request<{ user: UserPayload }>('/api/auth/google', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
  return data.user;
}

export async function signOut(): Promise<void> {
  await request<{ ok: boolean }>('/api/auth/logout', { method: 'POST' });
}

// ── Drive ────────────────────────────────────────────────────────────────

export interface ApiFile {
  name: string;
  mime_type: string;
  size: number;
  modified_time: string;
}

export interface ProcessFolderResponse {
  status: 'success';
  folder_id: string;
  folder_name: string;
  file_count: number;
  chunk_count: number;
  files: ApiFile[];
  skipped_files: SkippedFile[];
  unsupported_file_count: number;
  subfolder_count: number;
  vector_store_status: string;
  chunks_indexed: number;
}

export async function processFolder(folderUrl: string): Promise<ProcessFolderResponse> {
  return request<ProcessFolderResponse>('/api/drive/process-folder', {
    method: 'POST',
    body: JSON.stringify({ folder_url: folderUrl }),
  });
}

// ── Chat ─────────────────────────────────────────────────────────────────

export interface ChatSource {
  file_name: string;
  file_id: string;
  chunk_index: number;
}

export interface ChatResponse {
  reply: string;
  sources: ChatSource[];
}

export async function sendChatMessage(
  message: string,
  context: string,
  folderId: string | undefined,
): Promise<ChatResponse> {
  return request<ChatResponse>('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message, context, folder_id: folderId }),
  });
}

export { ApiError };
