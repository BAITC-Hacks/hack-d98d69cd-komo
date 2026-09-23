'use client';
import { useEffect, useState } from 'react';
import { api, errorMessage, type EmployeeAccess } from '@/shared/api/client';
import { Button, Notice, Panel } from '@/shared/ui';
import { randomToken } from '@/shared/lib/random';
import s from './access-panel.module.css';

export function AccessPanel({ employeeId }: { employeeId: string }) {
  const [access, setAccess] = useState<EmployeeAccess | null>(null);
  const [password, setPassword] = useState('');
  const [created, setCreated] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    setAccess(null); setCreated(false); setError('');
    api<EmployeeAccess>(`/employees/${employeeId}/access`).then(result => {
      if (active) { setAccess(result); if (!result.username) setPassword(randomToken().slice(0, 20)); }
    }).catch(e => { if (active) setError(errorMessage(e)); });
    return () => { active = false; };
  }, [employeeId]);
  async function create() {
    setBusy(true); setError('');
    try {
      const result = await api<EmployeeAccess>(`/employees/${employeeId}/access`, { method: 'POST', body: JSON.stringify({ password }) });
      setAccess(result); setCreated(true);
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <Panel className={s.panel}>
    <h2>Доступ сотрудника</h2>
    {error && <Notice kind="error">{error}</Notice>}
    {access?.username ? <>
      <p>Логин: <strong data-testid="employee-login">{access.username}</strong></p>
      {created ? <Notice>Доступ создан. Передайте сотруднику логин и пароль: <strong>{password}</strong>. Сохраните пароль сейчас: повторно он не показывается.</Notice>
        : <p>Учетная запись уже существует. Импорт профиля не меняет ее пароль.</p>}
    </> : access ? <>
      <p>Создайте доступ, чтобы сотрудник мог войти, выбрать цель и выполнять рекомендованные активности.</p>
      <div className={s.form}><label htmlFor="employee-access-password">Пароль нового сотрудника<input id="employee-access-password" value={password} minLength={10} maxLength={128} autoComplete="new-password" onChange={e => setPassword(e.target.value)} /></label>
      <Button disabled={busy || password.length < 10} onClick={() => void create()}>{busy ? 'Создаем…' : 'Создать доступ'}</Button></div>
      <p>Не менее 10 символов. Сотрудник получит доступ только к своему профилю.</p>
    </> : !error && <p>Проверяем доступ…</p>}
  </Panel>;
}
