'use client';
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { api, type Identity } from '@/shared/api/client';

const Context = createContext<{ user: Identity | null; loading: boolean; setUser: (user: Identity | null) => void; logout: () => Promise<void> }>({ user: null, loading: true, setUser: () => {}, logout: async () => {} });
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Identity | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  useEffect(() => { api<Identity>('/auth/me').then(setUser).catch(() => setUser(null)).finally(() => setLoading(false)); }, []);
  async function logout() { await api('/auth/logout', { method: 'POST' }); setUser(null); router.replace('/login'); }
  return <Context.Provider value={{ user, loading, setUser, logout }}>{children}</Context.Provider>;
}
export const useAuth = () => useContext(Context);
