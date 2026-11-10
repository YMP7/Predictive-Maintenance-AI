/**
 * API utility module for ATLAS
 * Centralizes backend API configuration and fetch helpers.
 */

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

/** Non-2xx reply. The message keeps the "API error <status>: <detail>" form older callers match on. */
export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(`API error ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

export const statusOf = (err: unknown) => (err instanceof ApiError ? err.status : null);

/**
 * Typed fetch wrapper with error handling. Every call carries a fresh correlation ID, which the
 * server copies into the audit trail and its logs.
 */
export async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-API-Request': 'true', // CSRF mitigation
    'X-Correlation-ID': crypto.randomUUID(),
    ...options?.headers as Record<string, string>
  };
  
  const response = await fetch(url, {
    ...options,
    credentials: 'include', // Send HttpOnly cookies
    headers
  });

  if (!response.ok) {
    // Session missing or expired: back to sign-in, then return here. A failed login itself
    // is also a 401, so it falls through and its message reaches the form.
    if (response.status === 401 && endpoint !== '/api/auth/login' && window.location.pathname !== '/login') {
      window.location.href = `/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
    }
    
    let errorMessage = response.statusText;
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
      } else if (errorData && errorData.message) {
        errorMessage = errorData.message;
      }
    } catch {
      // Ignore JSON parse errors for non-JSON responses
    }
    
    throw new ApiError(response.status, errorMessage);
  }

  return response.json() as Promise<T>;
}

/**
 * Extracts a human-readable message from an unknown thrown value.
 */
export function errorMessage(err: unknown, fallback = 'Unexpected error'): string {
  if (err instanceof Error && err.message) return err.message;
  if (typeof err === 'string' && err) return err;
  return fallback;
}

