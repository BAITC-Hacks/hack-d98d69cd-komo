'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/features/auth/provider';
import { api, errorMessage, dateLabel, statusLabels, type EmployeeProfile, type Development, type HistoryView, type RecommendationResult, type RecommendationState, type CompletionResult, type ActivityOption, type ParticipationResult, type RoleOption } from '@/shared/api/client';
import { Button, Empty, Loading, Notice, Panel } from '@/shared/ui';
import { CareerPath, SkillGrid } from '@/features/career-path/career-path';
import { GoalEditor } from '@/features/career-path/goal-editor';
import { ActivityHistory } from '@/features/activities/history';
import { ActivityDialog } from '@/features/activities/activity-dialog';
import { Recommendations, formatLabels } from '@/features/recommendations/recommendations';
import s from './workspace.module.css';

export function EmployeeWorkspace({ employeeId }: { employeeId?: string }) {
  const { user } = useAuth(); const router = useRouter(); const id = employeeId || user?.employee_id;
  const [employee, setEmployee] = useState<EmployeeProfile | null>(null);
  const [development, setDevelopment] = useState<Development | null>(null);
  const [history, setHistory] = useState<HistoryView[]>([]);
  const [recommendation, setRecommendation] = useState<RecommendationResult | null>(null);
  const [loading, setLoading] = useState(true); const [thinking, setThinking] = useState(false); const [busy, setBusy] = useState(false);
  const [error, setError] = useState(''); const [actionError, setActionError] = useState(''); const [success, setSuccess] = useState('');
  const [tab, setTab] = useState('skills'); const [allSkills, setAllSkills] = useState(false); const [editingGoal, setEditingGoal] = useState(false);
  const [selected, setSelected] = useState<ActivityOption | null>(null);
  const keys = useRef<Record<string, string>>({}); const recommendationRequest = useRef(0); const readOnly = user?.role === 'hr';
  const load = useCallback(async () => {
    if (!id) return; setError('');
    try {
      const [profile, dev, records, rec] = await Promise.all([api<EmployeeProfile>(`/employees/${id}`), api<Development>(`/employees/${id}/development`), api<HistoryView[]>(`/employees/${id}/history`), api<RecommendationState>(`/employees/${id}/recommendations`)]);
      setEmployee(profile); setDevelopment(dev); setHistory(records); setRecommendation(rec.result);
    } catch (e) { setError(errorMessage(e)); } finally { setLoading(false); }
  }, [id]);
  useEffect(() => { if (user?.role === 'hr' && !employeeId) router.replace('/hr'); else void load(); }, [load, user, employeeId, router]);
  async function recommend(refresh = false) {
    if (!id) return; const request = ++recommendationRequest.current; setThinking(true);
    try { const result = await api<RecommendationResult>(`/employees/${id}/recommendations?refresh=${refresh}`, { method: 'POST' }); if (request === recommendationRequest.current) setRecommendation(result); }
    catch (e) { if (request === recommendationRequest.current) setError(`Не удалось обновить подбор: ${errorMessage(e)}`); }
    finally { if (request === recommendationRequest.current) setThinking(false); }
  }
  async function refreshHistory() {
    try { setHistory(await api<HistoryView[]>(`/employees/${id}/history`)); }
    catch (e) { setError(`Изменение сохранено. Историю не удалось обновить: ${errorMessage(e)}`); }
  }
  function changed(dev: Development) { recommendationRequest.current += 1; setThinking(false); setDevelopment(dev); setRecommendation(prev => prev ? { ...prev, stale: true } : null); }
  async function saveGoal(goal: { target_role: string; target_grade: RoleOption['grade'] } | null) {
    if (!id || busy || readOnly) return; setBusy(true); setError(''); setSuccess('');
    try {
      const dev = await api<Development>(`/employees/${id}/career-goal`, { method: 'PATCH', body: JSON.stringify({ career_goal: goal }) });
      changed(dev); setEditingGoal(false); setSuccess('Цель сохранена. Требования и соответствие пересчитаны; навыки и текущий грейд не изменились.');
      void recommend();
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  function open(activity: ActivityOption) { setActionError(''); setSelected(activity); }
  async function mutate(action: 'start' | 'complete' | 'cancel', activity: ActivityOption, sessionDate?: string) {
    if (!id || busy || readOnly) return; setBusy(true); setActionError(''); setError(''); setSuccess('');
    const signature = `${action}:${activity.event_id}:${activity.record_id || ''}:${sessionDate || ''}`;
    const key = keys.current[signature] ||= crypto.randomUUID();
    const path = action === 'cancel' ? `/employees/${id}/participations/${activity.record_id}/cancel` : `/employees/${id}/activities/${activity.event_id}/${action}`;
    try {
      const result = await api<CompletionResult | ParticipationResult>(path, { method: 'POST', body: JSON.stringify({ idempotency_key: key, record_id: activity.record_id, session_date: sessionDate }) });
      delete keys.current[signature]; changed(result.development);
      if ('gains' in result) {
        setSuccess(`Готово! ${result.gains.length ? result.gains.map(g => `${g.name}: ${g.before} → ${g.after}`).join(' · ') : 'Участие завершено без нового прироста навыков'}. Соответствие цели: ${result.before_progress}% → ${result.development.progress}%.`);
        setSelected(null);
      } else if (action === 'cancel') { setSuccess('Участие отменено. Навыки не изменились.'); setSelected(null); }
      else {
        setSuccess(result.status === 'planned' ? 'Участие запланировано локально. Внешняя регистрация не выполнялась.' : 'Активность начата. Навыки изменятся после подтверждения выполнения.');
        setSelected(result.development.participations?.find(p => p.record_id === result.record_id) || null);
      }
      void refreshHistory(); void recommend();
    } catch (e) { setActionError(errorMessage(e)); } finally { setBusy(false); }
  }
  if (loading) return <Loading />;
  if (!employee || !development) return <><Notice kind="error">{error || 'Профиль недоступен'}</Notice><Button onClick={() => void load()}>Повторить</Button></>;
  const participations = development.participations || [];
  const activities = tab === 'participations' ? participations : development.available_events;
  return <>
    {readOnly && <Link href="/hr" className={s.back}>← К обзору команды</Link>}
    <div className={s.heading}><div><div className={s.eyebrow}>{readOnly ? 'ПРОФИЛЬ СОТРУДНИКА' : 'МОЕ РАЗВИТИЕ'}</div><h1>{readOnly ? employee.full_name : `Ваш следующий шаг, ${employee.full_name.split(' ')[0]}`}</h1><div className={s.sub}>{employee.role} · {employee.grade} | {employee.department}{employee.is_test ? ' · Тестовые данные' : ''}</div></div><div className={s.date}>{dateLabel(development.as_of_date)}</div></div>
    {error && <Notice kind="error">{error}</Notice>}{success && <Notice>{success}</Notice>}
    <div className={s.summary}><CareerPath development={development} onEdit={readOnly ? undefined : () => setEditingGoal(!editingGoal)} /><Panel className={s.stats}><div className={s.statTitle}>Ваше развитие в цифрах</div><div className={s.statRow}><div><div className={s.statNumber}>{history.filter(r => r.status === 'completed').length}</div><div className={s.statLabel}>активностей завершено</div></div><div><div className={s.statNumber}>{development.critical_gaps}</div><div className={s.statLabel}>критических разрывов<br />до цели</div></div></div><div className={s.statHint}>{development.available_events.length} подходящих шагов · {participations.length} текущих участий<br />Оценка навыков {dateLabel(employee.last_review_date)}. Последующие завершения учтены.</div></Panel></div>
    {editingGoal && !readOnly && <GoalEditor development={development} busy={busy} onSave={saveGoal} onClose={() => setEditingGoal(false)} />}
    <div className={s.sectionHeading}><div><h2>Следующие шаги</h2><p>Подобраны под вашу цель, опыт и историю участия</p></div><Button onClick={() => { setError(''); void recommend(true); }} disabled={thinking || busy}>{thinking ? 'Подбираем…' : recommendation ? 'Обновить подбор ↻' : 'Подобрать с AI ↗'}</Button></div>
    {!!development.uncovered_critical_skills?.length && <Notice kind="warning">Для критических навыков {development.uncovered_critical_skills.join(', ')} сейчас нет допустимого прямого шага в каталоге. Подбор может предложить другие полезные активности.</Notice>}
    <Recommendations result={recommendation} loading={thinking} readOnly={readOnly} completing={busy ? selected?.event_id || 'busy' : null} onOpen={open} />
    <div className={s.tabs}>{[['skills', 'Навыки и разрывы'], ['participations', `Мои активности (${participations.length})`], ['history', `История участия (${history.length})`], ['activities', 'Подходящие активности']].map(([value, label]) => <button key={value} className={`${s.tab} ${tab === value ? s.selected : ''}`} onClick={() => setTab(value)}>{label}</button>)}</div>
    <Panel>{tab === 'skills' ? <><SkillGrid development={development} all={allSkills} /><button className={s.more} onClick={() => setAllSkills(!allSkills)}>{allSkills ? 'Только навыки карьерной цели ↑' : 'Показать все навыки ↓'}</button></> : tab === 'history' ? <ActivityHistory records={history} /> : activities.length ? <div className={s.activityList}>{activities.map(activity => <div className={s.activity} key={activity.record_id || activity.event_id}><div className={s.activityTitle}>{activity.title}<div className={s.activityMeta}>{formatLabels[activity.format]} · {activity.duration_hours} ч · {activity.participation_status ? statusLabels[activity.participation_status] : activity.format === 'self_paced' ? 'Можно начать сейчас' : 'Сессия по расписанию'}{activity.next_session && ` · ${dateLabel(activity.next_session)}`}</div><div className={s.description}>{activity.description}</div></div><Button variant="secondary" className={s.compactButton} disabled={busy} onClick={() => open(activity)}>{readOnly ? 'Подробнее' : activity.record_id ? 'Продолжить' : activity.format === 'self_paced' ? 'Начать' : 'Запланировать'}</Button></div>)}</div> : <Empty>{tab === 'participations' ? 'Вы пока не начали и не запланировали активности. Выберите подходящий шаг.' : development.availability_reasons?.join(' ') || 'Сейчас нет подходящих активностей для этой цели.'}</Empty>}</Panel>
    {selected && <ActivityDialog activity={selected} busy={busy} readOnly={readOnly} error={actionError} onClose={() => { setSelected(null); setActionError(''); }} onStart={day => void mutate('start', selected, day)} onComplete={() => void mutate('complete', selected)} onCancel={() => void mutate('cancel', selected)} />}
  </>;
}
