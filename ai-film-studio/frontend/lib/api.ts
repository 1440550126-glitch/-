import type { ContinuityReport, MemoryAnchor, Project } from '@/types/studio';
const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) }, cache: 'no-store' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
export const api = {
  projects: () => request<Project[]>('/api/projects'),
  project: (id: number) => request<Project>(`/api/projects/${id}`),
  createProject: (data: Partial<Project>) => request<Project>('/api/projects', { method: 'POST', body: JSON.stringify(data) }),
  gen: (id: number, step: string) => request<unknown>(`/api/projects/${id}/${step}`, { method: 'POST' }),
  autoSelect: (id: number) => request<unknown>(`/api/projects/${id}/auto-select-characters`, { method: 'POST' }),
  selectCharacter: (projectId:number, characterId:number) => request<unknown>(`/api/projects/${projectId}/select-character`, { method:'POST', body: JSON.stringify({ character_id: characterId }) }),
  shotAction: (shotId:number, action:string) => request<unknown>(`/api/shots/${shotId}/${action}`, { method:'POST' }),
  anchors: (id:number) => request<MemoryAnchor[]>(`/api/projects/${id}/memory-anchors`),
  reports: (id:number) => request<ContinuityReport[]>(`/api/projects/${id}/continuity-reports`),
};
