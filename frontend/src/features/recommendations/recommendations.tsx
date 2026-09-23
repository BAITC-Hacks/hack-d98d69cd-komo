import { dateLabel, type RecommendationResult, type ActivityOption } from '@/shared/api/client';
import { Button, Empty, Loading, Notice, Tag } from '@/shared/ui';
import s from './recommendations.module.css';
import { LearningResources } from '@/features/activities/learning-resources';

const factorLabels: Record<string, string> = { grade: 'Подходит ли вам эта активность', skill_gap: 'Что вы сможете развить', history: 'Что учтено из вашего опыта', target_requirements: 'Как это связано с вашей целью' };
export const formatLabels: Record<string, string> = { online: 'Онлайн', offline: 'Очно', self_paced: 'В своем темпе' };
const percent = (value: number) => value.toLocaleString('ru-RU', { maximumFractionDigits: 1 });

export function Recommendations({ result, loading, readOnly, completing, onOpen, currentProgress }: { result: RecommendationResult | null; loading: boolean; readOnly: boolean; completing: string | null; onOpen: (activity: ActivityOption) => void; currentProgress: number }) {
  if (loading) return <Loading label="Ищем подходящие активности для вашей цели…" />;
  if (!result) return <Empty>Нажмите «Подобрать с AI», чтобы увидеть, чему можно научиться дальше и как это поможет вашей цели.</Empty>;
  return <>
    {result.stale && <Notice kind="warning">Цель или данные изменились. Обновите рекомендации, чтобы увидеть подходящие сейчас варианты.</Notice>}
    {result.source === 'fallback' && result.steps.length > 0 && <Notice kind="warning">{result.message}</Notice>}
    {!result.steps.length ? <Empty>{result.message}</Empty> : <>
      <div className={s.source}>{result.source === 'ai' ? 'Подобрано с AI с учетом вашей цели и истории участия' : 'Подобрано по правилам · без AI'}</div>
      <div className={s.grid}>{result.steps.map((step, i) => <article className={s.card} key={step.activity.event_id}>
        <div className={s.top}><span className={s.icon}>{['↗', '◇', '◎'][i]}</span><Tag>{i === 0 ? 'Рекомендуем попробовать' : 'Еще один вариант'}</Tag></div>
        <h3>{step.activity.title}</h3>
        <div className={s.meta}>{formatLabels[step.activity.format]} · {step.activity.duration_hours} ч{step.activity.next_session ? ` · ${dateLabel(step.activity.next_session)}` : ''}</div>
        <p className={s.reason}>{step.activity.description}</p>
        <h4 className={s.label}>Как это поможет вашей цели</h4>
        <p className={s.reason}>{step.explanation}</p>
        <div className={s.gain}><h4 className={s.label}>После выполнения</h4>{step.activity.gains.map(g => <div className={s.gainRow} key={g.skill_id}>
          <span>{g.name}: <strong>{g.before} → {g.after}</strong></span>
          <span className={s.gainHint}>{g.required ? `Для цели нужен уровень ${g.required}` : 'Дополнительный навык'}</span>
        </div>)}<div className={s.progress}>{result.stale ? <>Предыдущий прогноз: <strong>{percent(step.activity.expected_progress)}%</strong>. Обновите рекомендации.</> : <>Соответствие требованиям цели: <strong>{percent(currentProgress)}% → {percent(step.activity.expected_progress)}%</strong></>}</div><div className={s.gainHint}>По расчету программы для этой активности</div></div>
        <details className={s.details}><summary>Почему вам это подходит</summary><div className={s.facts}>{step.evidence.map(f => <div className={s.fact} key={f.factor}><strong>{factorLabels[f.factor]}</strong>{f.text}</div>)}</div></details>
        <LearningResources activity={step.activity} />
        {!readOnly && <Button variant="secondary" className={s.action} disabled={!!completing || result.stale} onClick={() => onOpen(step.activity)}>{completing === step.activity.event_id ? 'Сохраняем…' : step.activity.record_id ? 'Продолжить →' : step.activity.format === 'self_paced' ? 'Начать →' : 'Запланировать участие →'}</Button>}
        {!readOnly && !step.activity.record_id && step.activity.format !== 'self_paced' && <div className={s.future}>Добавим активность в ваш план. На само мероприятие нужно записаться отдельно.</div>}
        {step.activity.record_id && !step.activity.can_complete && <div className={s.future}>Уже в вашем плане. Отметить выполнение можно после занятия.</div>}
        {readOnly && <div className={s.future}>Выполнение отмечает сам сотрудник.</div>}
      </article>)}</div>
    </>}
  </>;
}
