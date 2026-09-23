import type { Development } from '@/shared/api/client';
import { Progress, Button } from '@/shared/ui';
import s from '@/features/employee-profile/workspace.module.css';

export function CareerPath({ development, onEdit }: { development: Development; onEdit?: () => void }) {
  const goal = development.goal;
  return <section className={s.goal}><div className={s.goalLabel}>ВАША КАРЬЕРНАЯ ТРАЕКТОРИЯ</div><h2>{goal.role}</h2><p>Целевой уровень · {goal.grade}{goal.maintenance ? ' · поддержание компетенций' : ''}</p><div className={s.goalRow}><span>Соответствие требованиям цели</span><strong>{development.progress}%</strong></div><Progress value={development.progress} label="Соответствие карьерной цели" /><div className={s.goalNote}>{goal.source === 'manual' ? 'Цель выбрана вами' : goal.inferred ? 'Цель предложена по текущей роли и грейду' : 'Цель из профиля сотрудника'} · Повышение грейда не происходит автоматически</div>{onEdit && <Button variant="secondary" style={{ marginTop: 18, position: 'relative', zIndex: 1 }} onClick={onEdit}>Изменить цель</Button>}</section>;
}

export function SkillGrid({ development, all }: { development: Development; all: boolean }) {
  const relevant = development.skills.filter(skill => skill.required > 0 || all);
  return <div className={s.skills}>{relevant.map(skill => <div key={skill.skill_id}><div className={s.skillHead}><span className={s.skillName}>{skill.name}{skill.critical && <span className={s.critical}>КРИТИЧЕСКИЙ</span>}</span><span className={s.skillScore}>{skill.current} / {skill.required || '—'}</span></div><Progress value={skill.current / 5 * 100} label={`${skill.name}: уровень ${skill.current} из 5`} /><div className={s.skillFoot}>{skill.gap > 0 ? `До требования цели: +${skill.gap}` : skill.required ? 'Требование цели выполнено' : 'Вне требований выбранной цели'} · шкала 0–5</div></div>)}</div>;
}
