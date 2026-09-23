'use client';
import { useState, type FormEvent } from 'react';
import Link from 'next/link';
import { api, ApiError, errorMessage, type ImportResult } from '@/shared/api/client';
import { Button, Notice, Panel } from '@/shared/ui';
import s from './import.module.css';

export function ImportScreen() {
  const [templateFormat, setTemplateFormat] = useState('xlsx');
  const [downloading, setDownloading] = useState(false);
  const [employees, setEmployees] = useState<File | null>(null); const [history, setHistory] = useState<File | null>(null); const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [details, setDetails] = useState(''); const [result, setResult] = useState<ImportResult | null>(null);
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(''); setDetails(''); setResult(null); const form = new FormData(); if (employees) form.append('employees', employees); if (history) form.append('history', history); try { setResult(await api<ImportResult>('/hr/import', { method: 'POST', body: form })); } catch (e) { setError(errorMessage(e)); if (e instanceof ApiError && e.details) setDetails(JSON.stringify(e.details, null, 2)); } finally { setBusy(false); } }
  async function downloadTemplate() {
    setDownloading(true); setError(''); setDetails('');
    try {
      const response = await fetch(`/api/v1/hr/import/template?format=${templateFormat}`);
      if (!response.ok) throw new Error(response.status === 401 ? 'Войдите заново, чтобы скачать шаблон.' : 'Не удалось скачать шаблон. Повторите попытку.');
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a'); link.href = url; link.download = `career-quest-template.${templateFormat}`;
      document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setError(errorMessage(e)); } finally { setDownloading(false); }
  }
  return <div className={s.body}>
    <header className={s.header}><h1>Новые данные — новые возможности</h1><p>Добавьте сотрудников и историю участия из Excel или JSON. Для истории также доступен CSV.</p></header>
    {error && <Notice kind="error">{error}{details && <pre className={s.details}>{details}</pre>}</Notice>}
    <Panel className={s.template}>
      <h2>Начните с шаблона</h2><p>Скачайте пример, замените данные на свои и загрузите заполненный файл. Excel содержит листы сотрудников, навыков и истории, инструкцию и справочники.</p>
      <div className={s.actions}><label className={s.format}>Формат шаблона<select aria-label="Формат шаблона" value={templateFormat} onChange={e => setTemplateFormat(e.target.value)}><option value="xlsx">Excel (.xlsx)</option><option value="json">JSON (.json)</option></select></label><Button type="button" variant="secondary" disabled={downloading} onClick={downloadTemplate}>{downloading ? 'Скачиваем…' : 'Скачать шаблон'}</Button></div>
    </Panel>
    <Panel><form onSubmit={submit}>
      <div className={s.info}>Файлы проверяются вместе и применяются целиком. Если найдена ошибка, данные останутся без изменений. Повторная загрузка не создает дубликаты.</div>
      <div className={s.files}>
        <label className={s.file}><h3>Профили сотрудников</h3><p>Excel (.xlsx) или JSON.<br />Заполненный шаблон может включать и историю — тогда второй файл не нужен.</p><input type="file" name="employees" accept=".json,.xlsx,application/json,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={e => setEmployees(e.target.files?.[0] || null)} aria-label="Профили сотрудников: Excel или JSON" /></label>
        <label className={s.file}><h3>История участия</h3><p>Excel (.xlsx), JSON или CSV.<br />Необязательно, если история уже включена в первый файл.</p><input type="file" name="history" accept=".csv,.json,.xlsx,text/csv,application/json,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={e => setHistory(e.target.files?.[0] || null)} aria-label="История участия: Excel, JSON или CSV" /></label>
      </div><div className={s.info}>Срез данных: 1 октября 2026 года. Названия колонок — как в шаблоне; их порядок можно менять. Файлы .xls сначала сохраните как .xlsx.</div>
      <div className={s.actions}><Button disabled={busy || (!employees && !history)}>{busy ? 'Проверяем и загружаем…' : 'Проверить и импортировать ↥'}</Button><span className={s.hint}>До 4 МБ на файл</span></div>
    </form></Panel>
    {result && <div className={s.result}><Notice>{result.message}</Notice><Panel><h2>Результат импорта</h2><div className={s.stats}>Новых профилей: {result.employees_created} · обновлено: {result.employees_updated}<br />Новых записей истории: {result.history_created} · обновлено: {result.history_updated}</div><div className={s.links}>{result.employee_ids.slice(0, 10).map(id => <Link key={id} href={`/hr/employees/${id}`}>Открыть профиль {id} и подобрать шаги ↗</Link>)}</div></Panel></div>}
  </div>;
}
