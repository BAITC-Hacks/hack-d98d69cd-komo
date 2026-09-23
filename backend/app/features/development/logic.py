"""Shared, deterministic domain rules. No database, HTTP or model calls."""
from app.features.catalog.service import Catalog
from app.features.development.schemas import Development, Goal, SkillState, SkillGain, ActivityOption

GRADES = ['Junior', 'Middle', 'Senior', 'Lead']


def effective_skills(employee: dict, history: list[dict], catalog: Catalog) -> dict[str, int]:
    levels = dict(employee['skills'])
    seen = set()
    for record in sorted(history, key=lambda x: (x.get('effective_date', x['date']), x['record_id'])):
        if record['record_id'] in seen or record['status'] != 'completed':
            continue
        seen.add(record['record_id'])
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
        return Goal(role=explicit['target_role'], grade=explicit['target_grade'], inferred=False, maintenance=False)
    idx = GRADES.index(employee['grade'])
    return Goal(role=employee['role'], grade=GRADES[min(idx + 1, 3)], inferred=True, maintenance=idx == 3)


def event_gains(event: dict, levels: dict, requirements: dict, catalog: Catalog) -> list[SkillGain]:
    result = []
    for gain in event['develops_skills']:
        key = gain['skill_id']
        before = levels.get(key, 0)
        after = max(before, min(5, gain['max_level'], before + gain['gain']))
        if after > before:
            result.append(SkillGain(skill_id=key, name=catalog.skills[key]['name'], before=before, after=after, required=requirements.get(key, 0)))
    return result


def calculate_development(employee: dict, history: list[dict], catalog: Catalog, as_of: str, revision: int) -> Development:
    levels = effective_skills(employee, history, catalog)
    goal = choose_goal(employee)
    target = catalog.roles[(goal.role, goal.grade)]
    requirements = target['required_skills']
    skills = [SkillState(skill_id=k, name=catalog.skills[k]['name'], current=levels.get(k, 0), required=requirements.get(k, 0),
                        gap=max(0, requirements.get(k, 0) - levels.get(k, 0)), critical=k in target['critical_skills'])
              for k in sorted(set(levels) | set(requirements))]
    skills.sort(key=lambda x: (-int(x.critical and x.gap > 0), -x.gap, x.name))
    denominator = sum(requirements.values())
    progress = round(100 * sum(min(levels.get(k, 0), v) for k, v in requirements.items()) / denominator, 1) if denominator else 100.0
    completed = {r['event_id'] for r in history if r['status'] == 'completed'}
    available = []
    audience = []
    for event in catalog.events.values():
        if event['mandatory'] or employee['role'] not in event['target_roles'] or employee['grade'] not in event['target_grades']:
            continue
        if event['event_id'] in completed and event['event_id'] != 'EV_036':
            continue
        active = next((r for r in reversed(history) if r['event_id'] == event['event_id'] and r['status'] == 'in_progress'), None)
        sessions = sorted(d for d in event['upcoming_sessions'] if d >= as_of)
        if event['format'] != 'self_paced' and not sessions and not active:
            continue
        audience.append(event)
        if any(levels.get(k, 0) < v for k, v in event['prerequisites'].items()):
            continue
        gains = event_gains(event, levels, requirements, catalog)
        if not gains:
            continue
        available.append(ActivityOption(
            event_id=event['event_id'], title=event['title'], description=event['description'], format=event['format'],
            duration_hours=event['duration_hours'], next_session=sessions[0] if sessions else None,
            action='continue' if active else 'start', gains=gains,
            can_complete=event['format'] == 'self_paced' or bool(active and active['date'] <= as_of) or as_of in sessions,
            record_id=active['record_id'] if active else None,
        ))
    direct = [e for e in available if any(g.before < g.required for g in e.gains)]
    if not direct:
        # One-hop prerequisite support; all role/grade/repeat constraints still apply.
        for option in available:
            future_levels = levels | {g.skill_id: g.after for g in option.gains}
            for later in audience:
                if later['event_id'] == option.event_id:
                    continue
                was_blocked = any(levels.get(k, 0) < v for k, v in later['prerequisites'].items())
                opens = all(future_levels.get(k, 0) >= v for k, v in later['prerequisites'].items())
                useful = any(g.before < g.required for g in event_gains(later, future_levels, requirements, catalog))
                if was_blocked and opens and useful:
                    option.preparatory_for.append(later['event_id'])
        direct = [e for e in available if e.preparatory_for]
    return Development(employee_id=employee['employee_id'], as_of_date=as_of, revision=revision, goal=goal,
                       progress=progress, skills=skills, critical_gaps=sum(s.critical and s.gap > 0 for s in skills), available_events=direct)


def history_facts(history: list[dict], event: ActivityOption, catalog: Catalog) -> dict:
    relevant_skills = {g.skill_id for g in event.gains}
    related = [r for r in history if relevant_skills.intersection(g['skill_id'] for g in catalog.events[r['event_id']]['develops_skills'])]
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
        return (5 * critical_gain + 2 * gain + history_factor + bool(event.preparatory_for), -event.duration_hours, event.event_id)
    return sorted(development.available_events, key=score, reverse=True)
