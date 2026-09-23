import type { ActivityOption } from '@/shared/api/client';
import s from './learning-resources.module.css';

export function LearningResources({ activity }: { activity: ActivityOption }) {
  const resources = activity.resources || [];
  return <section className={s.section} aria-label="Материалы активности">
    <h4>{activity.format === 'self_paced' ? 'Материалы по теме' : 'Для подготовки к занятию'}</h4>
    {resources.length ? <>
      <ul>{resources.map(resource => <li key={resource.url}>
        <div className={s.source}>{resource.source} · {resource.language === 'en' ? 'На английском' : resource.language}</div>
        <strong>{resource.title}</strong>
        <p>{resource.description}</p>
        <a href={resource.url} target="_blank" rel="noopener noreferrer" aria-label={`Открыть материал: ${resource.title} (новая вкладка)`}>Открыть материал ↗</a>
      </li>)}</ul>
      <p className={s.note}>{activity.format === 'self_paced' ? 'Дополнительное чтение к программе. Само по себе не означает, что курс пройден.' : 'Материал поможет подготовиться, но не заменяет участие в занятии.'} Открытие ссылки не меняет ваш прогресс.</p>
    </> : <p className={s.note}>Материалы пока не добавлены. Уточните программу и доступ к обучению у HR.</p>}
  </section>;
}
