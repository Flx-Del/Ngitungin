const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
let token = sessionStorage.getItem('ngitungin-token')

export function setToken(value: string | null) {
  token = value
  if (value) sessionStorage.setItem('ngitungin-token', value)
  else sessionStorage.removeItem('ngitungin-token')
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? 'Terjadi kendala. Coba lagi.')
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function exportUrl(start: string, end: string, dataset = 'transactions') {
  return `${API_URL}/api/reports/export.csv?start=${start}&end=${end}&dataset=${dataset}`
}
