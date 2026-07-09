/**
 * API utility module for AI Digital Twin
 * Centralizes backend API configuration and fetch helpers.
 */

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

/**
 * Typed fetch wrapper with error handling.
 */
export async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-API-Request': 'true', // CSRF mitigation
    ...options?.headers as Record<string, string>
  };
  
  const response = await fetch(url, {
    ...options,
    credentials: 'include', // Send HttpOnly cookies
    headers
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Clear auth UI state and redirect to login
      document.cookie = "auth_status=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
      document.cookie = "user_role=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
      window.location.href = '/login';
    }
    
    let errorMessage = response.statusText;
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
      } else if (errorData && errorData.message) {
        errorMessage = errorData.message;
      }
    } catch (e) {
      // Ignore JSON parse errors for non-JSON responses
    }
    
    throw new Error(`API error ${response.status}: ${errorMessage}`);
  }

  return response.json() as Promise<T>;
}
