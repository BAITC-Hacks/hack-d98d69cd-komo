'use client';
import { useEffect, type ReactNode } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from './provider';
import { Loading } from '@/shared/ui';
import s from './shell.module.css';

export function Brand() { return <Link href="/" className={s.brand}><span className={s.mark}>↗</span>career quest<span style={{ color: '#bdc8b9', fontSize: 9 }}>●</span></Link>; }
export function AppShell({ children, hr = false }: { children: ReactNode; hr?: boolean }) {
  const { user, loading, logout } = useAuth(); const router = useRouter(); const pathname = usePathname();
  useEffect(() => { if (!loading && !user) router.replace('/login'); else if (user && hr && user.role !== 'hr') router.replace('/me'); }, [user, loading, hr, router]);
  if (loading || !user || (hr && user.role !== 'hr')) return <Loading />;
  return <div className={s.shell}><aside className={s.sidebar}><Brand /><div className={s.label}>ПРОСТРАНСТВО РАЗВИТИЯ</div><nav className={s.nav} aria-label="Основная навигация">
    {user.role === 'employee' ? <Link href="/me" className={pathname === '/me' ? s.active : ''}><span className={s.navIcon}>◈</span>Мое развитие</Link> : <><Link href="/hr" className={pathname === '/hr' || pathname.startsWith('/hr/employees') ? s.active : ''}><span className={s.navIcon}>▥</span>Обзор команды</Link><Link href="/hr/import" className={pathname === '/hr/import' ? s.active : ''}><span className={s.navIcon}>↥</span>Импорт данных</Link></>}
  </nav><div className={s.bottom}>Каждый шаг имеет значение.<br />HackAlem AI · Halyk Bank<br /><span>Синтетические данные</span></div></aside><div className={s.main}><header className={s.topbar}><span>Рабочее пространство <span style={{ margin: '0 12px', color: '#c0c8c0' }}>/</span> {user.role === 'hr' ? 'HR-аналитика' : 'Мое развитие'}</span><div className={s.account}><span className={s.avatar}>{user.role === 'hr' ? 'HR' : 'CQ'}</span><span>{user.role === 'hr' ? 'HR-специалист' : 'Сотрудник'}</span><button className={s.logout} onClick={() => void logout()}>Выйти</button></div></header><main className={s.content}>{children}<footer className={s.footer}>CAREER QUEST · Данные на 1 октября 2026 · Рекомендации помогают принять решение, участие добровольное</footer></main></div></div>;
}
