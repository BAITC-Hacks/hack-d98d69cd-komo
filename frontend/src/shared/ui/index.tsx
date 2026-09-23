import type { ButtonHTMLAttributes, ReactNode } from 'react';
import s from './ui.module.css';

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) { return <section className={`${s.panel} ${className}`}>{children}</section>; }
export function Button({ variant = 'primary', className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' }) { return <button {...props} className={`${s.button} ${variant === 'secondary' ? s.secondary : ''} ${className}`} />; }
export function Notice({ children, kind = 'success' }: { children: ReactNode; kind?: 'success' | 'error' | 'warning' }) { return <div role={kind === 'error' ? 'alert' : 'status'} className={`${s.notice} ${kind === 'error' ? s.error : kind === 'warning' ? s.warning : ''}`}>{children}</div>; }
export function Empty({ children }: { children: ReactNode }) { return <div className={s.empty}>{children}</div>; }
export function Loading({ label = 'Загружаем данные…' }: { label?: string }) { return <div role="status" className={s.loading}><div className={s.spinner} />{label}</div>; }
export function Progress({ value, label }: { value: number; label: string }) { return <div className={s.progress} role="progressbar" aria-label={label} aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}><div className={s.progressFill} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} /></div>; }
export function Tag({ children }: { children: ReactNode }) { return <span className={s.tag}>{children}</span>; }
