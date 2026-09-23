import { AppShell } from '@/features/auth/shell';
import { EmployeeWorkspace } from '@/features/employee-profile/workspace';
export default async function EmployeePage({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; return <AppShell hr><EmployeeWorkspace employeeId={id} /></AppShell>; }
