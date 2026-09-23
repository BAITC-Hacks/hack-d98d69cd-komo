import type { components } from './schema';

export type RoleOption = components['schemas']['RoleOption'];
export type ParticipationResult = components['schemas']['ParticipationResult'];
export type Identity = components['schemas']['Identity'];
export type EmployeeProfile = components['schemas']['EmployeeView'];
export type Development = components['schemas']['Development'];
export type HistoryView = components['schemas']['HistoryView'];
export type RecommendationResult = components['schemas']['RecommendationResult'];
export type RecommendationState = components['schemas']['RecommendationState'];
export type CompletionResult = components['schemas']['CompletionResult'];
export type HROverview = components['schemas']['HROverview'];
export type ImportResult = components['schemas']['ImportResult'];
export type ActivityOption = components['schemas']['ActivityOption'];

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: unknown) { super(message); }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(`/api/v1${path}`, { ...options, headers, credentials: 'same-origin', cache: 'no-store' });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, data?.code || 'request_failed', data?.message || 'Не удалось выполнить запрос. Повторите попытку.', data?.details);
  return data as T;
}

export function errorMessage(error: unknown): string { return error instanceof Error ? error.message : 'Не удалось выполнить запрос'; }
export function dateLabel(value: string): string { return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(`${value.slice(0, 10)}T12:00:00`)); }
export const statusLabels: Record<string, string> = { planned: 'Запланировано', cancelled: 'Отменено', completed: 'Завершено', in_progress: 'В процессе', dropped: 'Прервано', no_show: 'Пропуск', declined: 'Отказ', overdue: 'Просрочено', no_eligible_step: 'Нет доступного шага', not_generated: 'Подбор не запущен', stale: 'Нужен новый подбор', ready: 'Шаг подобран' };
