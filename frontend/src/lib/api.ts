export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) } })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`)
  return body as T
}

export type Vehicle = {
  'Model year': number; Make: string; Model: string; 'Vehicle class': string;
  'Motor (kW)': number; 'Recharge time (h)': number; 'Energy Efficiency (km/kWh)': number
}
export type Overview = { dataset_rows: number; makes: number; models: number; classes: number; efficiency_mean: number; efficiency_min: number; efficiency_max: number; model: { r2: number; mae: number; rmse: number; train_rows: number; test_rows: number } }
export type TripResult = any

export const api = {
  overview: () => request<Overview>('/api/overview'),
  vehicles: (search = '') => request<{items: Vehicle[]}>(`/api/vehicles?search=${encodeURIComponent(search)}`),
  vehicleOptions: () => request<{makes: string[]; records: Vehicle[]}>('/api/vehicle-options'),
  analytics: () => request<any>('/api/analytics'),
  analyzeTrip: (payload: any) => request<TripResult>('/api/trip/analyze', { method: 'POST', body: JSON.stringify(payload) }),
  health: () => request<{status: string; ors_configured: boolean}>('/api/health'),
}
