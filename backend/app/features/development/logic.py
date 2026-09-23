"""Shared, deterministic domain rules. No database, HTTP or model calls."""
from app.features.catalog.service import Catalog
from app.features.development.context import context_version
from app.features.development.schemas import Development, Goal, SkillState, SkillGain, ActivityOption

GRADES = ['Junior', 'Middle', 'Senior', 'Lead']


def completion_identity(record: dict, catalog: Catalog) -> tuple:
    """A course awards once; recurring sessions/compliance remain distinct by date."""
    event = catalog.events[record['event_id']]
    recurring = event['mandatory'] or record['event_id'] == 'EV_036'
    return record.get('employee_id'), record['event_id'], record['date'] if recurring else None


def effective_skills(employee: dict, history: list[dict], catalog: Catalog) -> dict[str, int]:
    levels = dict(employee['skills'])
    seen = set()
    for record in sorted(history, key=lambda x: (x.get('effective_date', x['date']), x['record_id'])):
        if record['status'] != 'completed':
            continue
        identity = completion_identity(record, catalog)
        if identity in seen:
            continue
        seen.add(identity)
        effective_date = record.get('effective_date', record['date'])
        # Imported same-day history belongs to the assessment; an action
        # confirmed in this app occurs after the loaded baseline on that day.
        if effective_date < employee['last_review_date'] or (effective_date == employee['last_review_date'] and not record.get('completed_at')):
            continue
        for gain in catalog.events[record['event_id']]['develops_skills']:
            key = gain['skill_id']
            before = levels.get(key, 0)
            levels[key] = max(before, min(5, gain['max_level'], before + gain['gain']))
    return levels


def choose_goal(employee: dict) -> Goal:
    explicit = employee.get('career_goal')
    if explicit:
        return Goal(role=explicit['target_role'], grade=explicit['target_grade'], inferred=False, maintenance=False, source='profile')
    idx = GRADES.index(employee['grade'])
    return Goal(role=employee['role'], grade=GRADES[min(idx + 1, 3)], inferred=True, maintenance=idx == 3, source='automatic')


def event_gains(event: dict, levels: dict, requirements: dict, catalog: Catalog) -> list[SkillGain]:
    result = []
    for gain in event['develops_skills']:
        key = gain['skill_id']
        before = levels.get(key, 0)
        after = max(before, min(5, gain['max_level'], before + gain['gain']))
        if after > before:
            result.append(SkillGain(skill_id=key, name=catalog.skills[key]['name'], before=before, after=after, required=requirements.get(key, 0)))
    return result


def progress_for(levels: dict, requirements: dict) -> float:
    denominator = sum(requirements.values())
    return round(100 * sum(min(levels.get(k, 0), v) for k, v in requirements.items()) / denominator, 1) if denominator else 100.0


def activity_option(event, levels, requirements, catalog, as_of, history, active=None):
    completed_dates = {r['date'] for r in history if r['event_id'] == event['event_id'] and r['status'] == 'completed'}
    sessions = sorted(d for d in event['upcoming_sessions'] if d >= as_of and d not in completed_dates)
    gains = event_gains(event, levels, requirements, catalog)
    return ActivityOption(
        event_id=event['event_id'], title=event['title'], description=event['description'], format=event['format'],
        duration_hours=event['duration_hours'], next_session=active['date'] if active and event['format'] != 'self_paced' else (sessions[0] if sessions else None),
        action='continue' if active else 'start', gains=gains,
        can_complete=event['format'] == 'self_paced' or (active['date'] <= as_of if active else as_of in sessions),
        record_id=active['record_id'] if active else None, sessions=sessions,
        participation_status=active['status'] if active else None,
        can_cancel=bool(active and active.get('origin') == 'local'),
        expected_progress=progress_for(levels | {g.skill_id: g.after for g in gains}, requirements),
    )


def calculate_development(employee: dict, history: list[dict], catalog: Catalog, as_of: str, revision: int) -> Development:
    levels = effective_skills(employee, history, catalog)
    goal = choose_goal(employee)
    target = catalog.roles[(goal.role, goal.grade)]
    requirements = target['required_skills']
    skills = [SkillState(skill_id=k, name=catalog.skills[k]['name'], current=levels.get(k, 0), required=requirements.get(k, 0),
                        gap=max(0, requirements.get(k, 0) - levels.get(k, 0)), critical=k in target['critical_skills'])
              for k in sorted(set(levels) | set(requirements))]
    skills.sort(key=lambda x: (-int(x.critical and x.gap > 0), -x.gap, x.name))
    progress = progress_for(levels, requirements)
    completed = {r['event_id'] for r in history if r['status'] == 'completed'}
    participations = [activity_option(catalog.events[r['event_id']], levels, requirements, catalog, as_of, history, r)
                      for r in history if r['status'] in ('in_progress', 'planned') and not catalog.events[r['event_id']]['mandatory']]
    available, audience = [], []
    exclusions = {'completed': 0, 'schedule': 0, 'prerequisites': 0, 'cap': 0}
    for event in catalog.events.values():
        if event['mandatory'] or employee['role'] not in event['target_roles'] or employee['grade'] not in event['target_grades']:
            continue
        if event['event_id'] in completed and event['event_id'] != 'EV_036':
            exclusions['completed'] += 1
            continue
        active = next((r for r in reversed(history) if r['event_id'] == event['event_id'] and r['status'] in ('in_progress', 'planned')), None)
        option = activity_option(event, levels, requirements, catalog, as_of, history, active)
        if event['format'] != 'self_paced' and not option.sessions and not active:
            exclusions['schedule'] += 1
            continue
        audience.append(event)
        if any(levels.get(k, 0) < v for k, v in event['prerequisites'].items()):
            exclusions['prerequisites'] += 1
            continue
        if not option.gains:
            exclusions['cap'] += 1
            continue
        available.append(option)
    # Consider one-hop preparation alongside direct gains, not only as a last resort.
    critical_ids = set(target['critical_skills'])
    for option in available:
        future_levels = levels | {g.skill_id: g.after for g in option.gains}
        ready_on = max(as_of, option.next_session or as_of)
        for later in audience:
            if later['event_id'] == option.event_id:
                continue
            was_blocked = any(levels.get(k, 0) < v for k, v in later['prerequisites'].items())
            opens = all(future_levels.get(k, 0) >= v for k, v in later['prerequisites'].items())
            useful = [g for g in event_gains(later, future_levels, requirements, catalog) if g.before < g.required]
            # A dated preparatory session must precede the follow-up session.
            later_dates = sorted(d for d in later['upcoming_sessions'] if d >= ready_on and
                                 (catalog.events[option.event_id]['format'] == 'self_paced' or d > ready_on))
            if later['format'] != 'self_paced' and not later_dates:
                continue
            if was_blocked and opens and useful:
                option.preparatory_for.append(later['event_id'])
                option.preparatory_critical_skills.extend(g.skill_id for g in useful if g.skill_id in critical_ids)
                if later['format'] != 'self_paced':
                    option.preparatory_sessions[later['event_id']] = later_dates[0]
        option.preparatory_critical_skills = sorted(set(option.preparatory_critical_skills))
    direct = [e for e in available if e.preparatory_for or any(g.before < g.required for g in e.gains)]
    reasons = []
    if not direct:
        if progress == 100:
            reasons = ['Требования выбранной цели уже выполнены. Можно выбрать новую цель.']
        else:
            labels = {'completed': 'Уже пройдены', 'schedule': 'Нет доступных сессий', 'prerequisites': 'Не выполнены требования к участию', 'cap': 'Достигнут потолок развиваемых навыков'}
            reasons = [f'{labels[k]}: {v}.' for k, v in exclusions.items() if v]
            reasons.append('Среди оставшихся активностей нет шага, который уменьшает разрыв до цели или открывает подготовительный переход.')
    uncovered = [s.name for s in skills if s.critical and s.gap > 0 and not any(any(g.skill_id == s.skill_id and g.after > g.before for g in e.gains) for e in direct)]
    return Development(employee_id=employee['employee_id'], as_of_date=as_of, revision=revision, goal=goal,
                       context_version=context_version(employee, history, catalog, as_of),
                       progress=progress, skills=skills, critical_gaps=sum(s.critical and s.gap > 0 for s in skills), available_events=direct,
                       participations=participations, availability_reasons=reasons, uncovered_critical_skills=uncovered)


def history_facts(history: list[dict], event: ActivityOption, catalog: Catalog) -> dict:
    relevant_skills = {g.skill_id for g in event.gains}
    related = [r for r in history if r['status'] not in ('planned', 'cancelled') and relevant_skills.intersection(g['skill_id'] for g in catalog.events[r['event_id']]['develops_skills'])]
    return {
        'total': len(history), 'related': len(related),
        'completed': sum(r['status'] == 'completed' for r in related),
        'missed': sum(r['status'] in ('no_show', 'dropped', 'declined') for r in related),
        'same_event_completed': sum(r['event_id'] == event.event_id and r['status'] == 'completed' for r in history),
    }


def rank_candidates(development: Development, history: list[dict], catalog: Catalog) -> list[ActivityOption]:
    critical = {s.skill_id for s in development.skills if s.critical and s.gap > 0}
    def score(event):
        gain = sum(max(0, min(g.after, g.required) - g.before) for g in event.gains)
        critical_gain = sum(max(0, min(g.after, g.required) - g.before) for g in event.gains if g.skill_id in critical)
        facts = history_facts(history, event, catalog)
        history_factor = (facts['completed'] - facts['missed']) / max(1, facts['related'])
        return (bool(critical_gain), critical_gain, bool(event.preparatory_critical_skills),
                2 * gain + history_factor + bool(event.preparatory_for), -event.duration_hours, event.event_id)
    return sorted(development.available_events, key=score, reverse=True)
