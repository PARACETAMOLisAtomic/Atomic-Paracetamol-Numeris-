import { getAccessToken } from './supabase';

export type NumerisModule = {
  id: number;
  name: string;
  domain: string;
  description: string;
  status: string;
  metric: number;
  gradient: string;
  depth: number;
};

export type NumerisSignal = {
  id: number;
  symbol: string;
  verdict: string;
  confidence: number;
  momentum: number;
  risk: number;
  agent: string;
  price: number;
};

export type NumerisSimulation = {
  id: number;
  name: string;
  engine: string;
  region: string;
  intensity: number;
  forecast: string;
  updated_at: string;
};

export type NumerisReport = {
  id: number;
  title: string;
  category: string;
  severity: string;
  summary: string;
  created_at: string;
};

export type NumerisInteraction = {
  id: number;
  prompt: string;
  response: string;
  agent: string;
  confidence: number;
  created_at: string;
};

export type NumerisEvent = {
  id: number;
  event_type: string;
  title: string;
  detail: string;
  impact: number;
  region: string;
  created_at: string;
};

export type GeoNewsItem = {
  id: number;
  title: string;
  source: string;
  url: string;
  region: string;
  impact: number;
  summary: string;
  published_at: string;
};

export type BrainTrait = {
  id: number;
  title?: string;
  label: string;
  description?: string;
  confidence?: number;
  value?: number;
  color?: string;
  priority: number;
};

export type BrainRegion = {
  id: number;
  name: string;
  system: string;
  description: string;
  section_id: string;
  x: number;
  y: number;
  position_order: number;
};

export type NumerisData = {
  modules: NumerisModule[];
  signals: NumerisSignal[];
  simulations: NumerisSimulation[];
  reports: NumerisReport[];
  interactions: NumerisInteraction[];
  events: NumerisEvent[];
  brainTraits: BrainTrait[];
  brainRegions: BrainRegion[];
};

export type Holding = {
  symbol: string;
  quantity: number;
  avg_price: number;
};

export type SearchResult = {
  symbol: string;
  name: string;
  type: string;
  region: string;
};

export type Candle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type CandleResponse = {
  symbol: string;
  candles: Candle[];
};

const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';
const apiBaseUrl = rawBaseUrl.replace(/\/+$/, '');

function buildUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${apiBaseUrl}${normalizedPath}`;
}

async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getAccessToken();
  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type') && init.body) headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(buildUrl(path), {
    ...init,
    headers,
  });

  const contentType = response.headers.get('content-type') ?? '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    const message =
      typeof payload === 'object' && payload !== null && 'detail' in payload
        ? String(payload.detail)
        : typeof payload === 'object' && payload !== null && 'error' in payload
          ? String(payload.error)
          : `Request failed with ${response.status}`;
    throw new Error(message);
  }

  return payload as T;
}

export function getNumerisDashboard() {
  return apiRequest<NumerisData>('/api/numeris');
}

export function sendNumerisPrompt(prompt: string) {
  return apiRequest<NumerisInteraction>('/api/numeris', {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  });
}

export function tuneNumerisSimulation(id: number, intensity: number) {
  return apiRequest<NumerisSimulation>('/api/numeris', {
    method: 'PUT',
    body: JSON.stringify({ id, intensity }),
  });
}

export function deleteNumerisInteraction(id: number) {
  return apiRequest<{ ok: true }>('/api/numeris', {
    method: 'DELETE',
    body: JSON.stringify({ id }),
  });
}

export function getGeopoliticalNews() {
  return apiRequest<GeoNewsItem[]>('/api/geopolitical-news');
}

export function getEntranceSequence() {
  return apiRequest<Array<{ id: number; label: string; value: string; sequence_order: number }>>('/api/entrance-sequence');
}

export function getManualPortfolio() {
  return apiRequest<{ holdings: Holding[] }>('/api/portfolio/manual');
}

export function addManualHolding(symbol: string, quantity: number, buy_price: number) {
  return apiRequest<{ status: string }>('/api/portfolio/manual', {
    method: 'POST',
    body: JSON.stringify({ symbol, quantity, buy_price }),
  });
}

export function deleteManualHolding(symbol: string) {
  return apiRequest<{ status: string }>(`/api/portfolio/manual/${encodeURIComponent(symbol)}`, {
    method: 'DELETE',
  });
}

export function searchMarkets(query: string) {
  return apiRequest<{ results: SearchResult[] }>(`/api/market/search?query=${encodeURIComponent(query)}`);
}

export function getMarketCandles(symbol: string) {
  return apiRequest<CandleResponse>(`/api/market/candles?symbol=${encodeURIComponent(symbol)}`);
}

export type AuthStatusResponse = {
  authenticated: boolean;
  has_access: boolean;
  role: 'admin' | 'beta_user' | 'standard_user' | null;
  feature_flags: Record<string, boolean>;
};

export type AdminCodeItem = {
  code: string;
  is_active: boolean;
  role: 'admin' | 'beta_user' | 'standard_user';
  created_at: string;
};

export function getAuthStatus() {
  return apiRequest<AuthStatusResponse>('/api/auth/status');
}

export function redeemAccessCode(code: string) {
  return apiRequest<{ status: string; role: 'admin' | 'beta_user' | 'standard_user' }>('/api/auth/redeem', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

export function getAdminCodes() {
  return apiRequest<{ codes: AdminCodeItem[] }>('/api/auth/admin/codes');
}

export function generateAdminCodes(role: string, count: number) {
  return apiRequest<{ status: string; codes: AdminCodeItem[] }>('/api/auth/admin/codes', {
    method: 'POST',
    body: JSON.stringify({ role, count }),
  });
}

export function revokeAdminCode(code: string, is_active: boolean) {
  return apiRequest<{ status: string; code: string; is_active: boolean }>('/api/auth/admin/codes/revoke', {
    method: 'PUT',
    body: JSON.stringify({ code, is_active }),
  });
}

