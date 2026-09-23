import { dateLabel, statusLabels, type HistoryView } from '@/shared/api/client';
import { Empty, Tag } from '@/shared/ui';
import s from '@/features/employee-profile/workspace.module.css';

export function ActivityHistory({ records }: { records: HistoryView[] }) {
  if (!records.length) return <Empty>Пока нет истории участия. Начните с подходящей активности.</Empty>;
  return <div className={s.tableWrap}><table className={s.table}><thead><tr><th>АКТИВНОСТЬ</th><th>ДАТА</th><th>СТАТУС</th><th>ПРОГРЕСС</th></tr></thead><tbody>{records.map(record => <tr key={record.record_id}><td>{record.title}</td><td>{dateLabel(record.date)}</td><td><Tag>{statusLabels[record.status] || record.status}</Tag></td><td>{record.completion_pct}%</td></tr>)}</tbody></table></div>;
}
