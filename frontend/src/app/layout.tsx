import type { Metadata } from 'next';
import { AuthProvider } from '@/features/auth/provider';
import './globals.css';

export const metadata: Metadata = { title: 'Career Quest — пространство развития', description: 'Объяснимые AI-рекомендации и видимый прогресс развития сотрудников.' };
export default function RootLayout({ children }: { children: React.ReactNode }) { return <html lang="ru"><body><AuthProvider>{children}</AuthProvider></body></html>; }
