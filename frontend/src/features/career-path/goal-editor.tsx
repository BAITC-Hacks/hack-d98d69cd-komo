'use client';
import { useEffect, useState } from 'react';
import { api, errorMessage, type Development, type RoleOption } from '@/shared/api/client';
import { Button, Loading, Notice, Panel } from '@/shared/ui';
import s from './goal-editor.module.css';

export function GoalEditor({ development, busy, onSave, onClose }: { development: Development; busy: boolean; onSave: (goal: { target_role: string; target_grade: RoleOption['grade'] } | null) => Promise<void>; onClose: () => void }) {
  const [options, setOptions] = useState<RoleOption[]>([]);
  const [role, setRole] = useState(development.goal.role);
  const [grade, setGrade] = useState<RoleOption['grade']>(development.goal.grade as RoleOption['grade']);
  const [error, setError] = useState('');
  useEffect(() => { void api<RoleOption[]>('/catalog/role-profiles').then(setOptions).catch(e => setError(errorMessage(e))); }, []);
  const selected = options.find(o => o.role === role && o.grade === grade);
  return <Panel><div className={s.heading}><h2>Выберите карьерную цель</h2><Button variant="secondary" onClick={onClose} disabled={busy}>Закрыть</Button></div>
    <p>Цель может включать смену роли. Ваши навыки и текущий грейд от выбора цели не изменятся.</p>
    {error && <Notice kind="error">{error}</Notice>}
    {!options.length && !error ? <Loading /> : <form onSubmit={e => { e.preventDefault(); if (selected) void onSave({ target_role: role, target_grade: grade }); }}>
      <div className={s.fields}><label>Целевая роль<select aria-label="Целевая роль" value={role} onChange={e => { setRole(e.target.value); const first = options.find(o => o.role === e.target.value); if (first && !options.some(o => o.role === e.target.value && o.grade === grade)) setGrade(first.grade); }}>{Array.from(new Set(options.map(o => o.role))).map(r => <option key={r}>{r}</option>)}</select></label>
      <label>Целевой грейд<select aria-label="Целевой грейд" value={grade} onChange={e => setGrade(e.target.value as RoleOption['grade'])}>{options.filter(o => o.role === role).map(o => <option key={o.grade}>{o.grade}</option>)}</select></label></div>
      {selected && <details open className={s.preview}><summary>Требования выбранной цели</summary><ul>{Object.entries(selected.required_skills).map(([id, level]) => <li key={id}>{selected.skill_names[id]}: уровень {level}{selected.critical_skills.includes(id) ? ' · критический' : ''}</li>)}</ul></details>}
      <div className={s.actions}><Button disabled={busy || !selected}>{busy ? 'Сохраняем…' : 'Сохранить цель'}</Button><Button type="button" variant="secondary" disabled={busy} onClick={() => void onSave(null)}>Использовать автоматическую цель</Button></div>
    </form>}
  </Panel>;
}
