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
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options?.headers as Record<string, string>
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Clear auth and redirect to login on unauthorized
      localStorage.removeItem('token');
      localStorage.removeItem('role');
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
