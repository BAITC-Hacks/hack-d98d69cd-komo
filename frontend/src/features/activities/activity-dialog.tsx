'use client';
import { useEffect, useRef, useState } from 'react';
import { dateLabel, statusLabels, type ActivityOption } from '@/shared/api/client';
import { Button, Notice, Tag } from '@/shared/ui';
import { formatLabels } from '@/features/recommendations/recommendations';
import s from './activity-dialog.module.css';
import { LearningResources } from './learning-resources';

export function ActivityDialog({ activity, busy, readOnly, error, onClose, onStart, onComplete, onCancel }: { activity: ActivityOption; busy: boolean; readOnly: boolean; error: string; onClose: () => void; onStart: (date?: string) => void; onComplete: () => void; onCancel: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [session, setSession] = useState(activity.next_session || activity.sessions?.[0] || '');
  useEffect(() => { dialog.current?.showModal(); const node = dialog.current; return () => node?.close(); }, []);
  return <dialog ref={dialog} className={s.dialog} onCancel={e => { if (busy) e.preventDefault(); else onClose(); }} aria-labelledby="activity-title">
    <div className={s.header}><Tag>{activity.participation_status ? statusLabels[activity.participation_status] : 'Подходящая активность'}</Tag><Button variant="secondary" onClick={onClose} disabled={busy}>Закрыть</Button></div>
    <h2 id="activity-title">{activity.title}</h2><p>{activity.description}</p>
    <p>{formatLabels[activity.format]} · {activity.duration_hours} ч{activity.next_session && ` · ${dateLabel(activity.next_session)}`}</p>
    <div className={s.gains}>{activity.gains.length ? activity.gains.map(g => <div key={g.skill_id}>{g.name}: <strong>{g.before} → {g.after}</strong></div>) : 'Эта активность не повысит оценку навыков: ваш уровень уже выше того, которому она учит.'}<p>После выполнения, по расчету программы: {activity.expected_progress}%</p></div>
    <LearningResources activity={activity} />
    {error && <Notice kind="error">{error}</Notice>}
    <p className={s.note}>Вы сами выбираете, в чем участвовать. Здесь можно составить план и отметить выполнение. Полную программу обучения и запись на мероприятия уточняйте у HR. Выполнение отмечайте после прохождения самой активности.</p>
    {!readOnly && !activity.record_id && activity.format !== 'self_paced' && <label className={s.field}>Дата занятия<select aria-label="Дата занятия" value={session} onChange={e => setSession(e.target.value)}>{activity.sessions?.map(day => <option key={day} value={day}>{dateLabel(day)}</option>)}</select></label>}
    {activity.record_id && !activity.can_complete && <Notice kind="warning">Активность уже в вашем плане. Отметить выполнение можно после занятия. В демо используется дата 1 октября 2026.</Notice>}
    <div className={s.actions}>{readOnly ? <Tag>Отметить выполнение может только сотрудник</Tag> : activity.record_id ? <>
      <Button disabled={busy || !activity.can_complete} onClick={onComplete}>{busy ? 'Сохраняем…' : 'Отметить выполненным'}</Button>
      {activity.can_cancel && <Button variant="secondary" disabled={busy} onClick={onCancel}>Отменить участие</Button>}
    </> : <Button disabled={busy || (activity.format !== 'self_paced' && !session)} onClick={() => onStart(activity.format === 'self_paced' ? undefined : session)}>{busy ? 'Сохраняем…' : activity.format === 'self_paced' ? 'Начать активность' : 'Запланировать участие'}</Button>}</div>
  </dialog>;
}
