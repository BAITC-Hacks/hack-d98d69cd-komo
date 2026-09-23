from copy import deepcopy
import pytest
from app.features.development.logic import effective_skills, calculate_development, choose_goal, rank_candidates


def profile(dataset):
    return deepcopy(dataset[0][0])


def record(event_id, date='2026-09-30', status='completed', record_id='TEST'):
    return dict(record_id=record_id, event_id=event_id, date=date, status=status)


def test_after_review_and_no_double_count(dataset):
    e = profile(dataset); catalog = dataset[2]; e['skills']['SK_PYTHON'] = 0
    event = next(v for v in catalog.events.values() if any(g['skill_id'] == 'SK_PYTHON' for g in v['develops_skills']))
    gain = next(g for g in event['develops_skills'] if g['skill_id'] == 'SK_PYTHON')
    r = record(event['event_id'])
    assert effective_skills(e, [r, r], catalog)['SK_PYTHON'] == min(gain['gain'], gain['max_level'])


@pytest.mark.parametrize('status', ['in_progress', 'declined', 'dropped', 'no_show', 'overdue'])
def test_incomplete_statuses_do_not_add_skills(dataset, status):
    e = profile(dataset)
    assert effective_skills(e, [record('EV_004', status=status)], dataset[2]) == e['skills']


@pytest.mark.parametrize('day', ['2024-10-01', '2026-09-11'])
def test_completed_before_or_on_review_is_in_baseline(dataset, day):
    e = profile(dataset)
    assert effective_skills(e, [record('EV_004', date=day)], dataset[2]) == e['skills']


def test_caps_never_lower_and_mandatory_history_counts(dataset):
    e = profile(dataset); catalog = dataset[2]
    for g in catalog.events['EV_004']['develops_skills']:
        e['skills'][g['skill_id']] = 5
    assert effective_skills(e, [record('EV_004')], catalog) == e['skills']
    for g in catalog.events['EV_004']['develops_skills']:
        e['skills'].pop(g['skill_id'], None)
    levels = effective_skills(e, [record('EV_004')], catalog)
    assert all(levels[g['skill_id']] == min(g['gain'], g['max_level']) for g in catalog.events['EV_004']['develops_skills'])


def test_goal_cross_role_and_lead(dataset):
    e = profile(dataset)
    e['career_goal'] = {'target_role': 'Product Manager', 'target_grade': 'Middle'}
    assert choose_goal(e).role == 'Product Manager'
    e['career_goal'] = None
    assert choose_goal(e).grade == 'Middle'
    e['grade'] = 'Lead'
    assert choose_goal(e).maintenance and choose_goal(e).grade == 'Lead'


def test_all_profiles_deterministic_eligibility(dataset):
    employees, records, catalog = dataset
    for e in employees:
        history = [r for r in records if r['employee_id'] == e['employee_id']]
        result = calculate_development(e, history, catalog, '2026-10-01', 1)
        levels = effective_skills(e, history, catalog)
        assert 0 <= result.progress <= 100
        for option in result.available_events:
            event = catalog.events[option.event_id]
            assert not event['mandatory']
            assert e['role'] in event['target_roles'] and e['grade'] in event['target_grades']
            assert all(levels.get(k, 0) >= v for k, v in event['prerequisites'].items())
            assert option.event_id == 'EV_036' or not any(r['event_id'] == option.event_id and r['status'] == 'completed' for r in history)
            assert all(g.after > g.before and g.after <= 5 for g in option.gains)
            if event['format'] == 'self_paced':
                assert option.can_complete


def test_recurring_event_remains_eligible(dataset):
    e = profile(dataset); catalog = dataset[2]
    e['last_review_date'] = '2026-09-30'
    before = calculate_development(e, [], catalog, '2026-10-01', 1)
    assert 'EV_036' in {o.event_id for o in before.available_events}
    after = calculate_development(e, [record('EV_036', date='2026-09-01')], catalog, '2026-10-01', 1)
    assert 'EV_036' in {o.event_id for o in after.available_events}


def test_completed_nonrecurring_removed(dataset):
    e = profile(dataset); catalog = dataset[2]
    result = calculate_development(e, [record('EV_005')], catalog, '2026-10-01', 1)
    assert 'EV_005' not in {o.event_id for o in result.available_events}


def test_critical_gap_beats_lowest_skill_with_repeated_no_shows(dataset):
    e = deepcopy(next(e for e in dataset[0] if e['employee_id'] == 'E0028'))
    catalog = dataset[2]
    e['career_goal'] = {'target_role': 'Backend Engineer', 'target_grade': 'Senior'}
    e['skills'].update(catalog.roles[('Backend Engineer', 'Senior')]['required_skills'])
    e['skills'].update(SK_SYSTEM_DESIGN=2, SK_PUBLIC_SPEAKING=0)
    history = [record('EV_036', status='no_show', record_id=f'R{i}') for i in range(3)]
    development = calculate_development(e, history, catalog, '2026-10-01', 1)
    top = rank_candidates(development, history, catalog)[0]
    assert any(g.skill_id == 'SK_SYSTEM_DESIGN' for g in top.gains)
    assert top.event_id != 'EV_036'


def test_prerequisites_and_capped_skills_excluded(dataset):
    e = deepcopy(next(e for e in dataset[0] if e['employee_id'] == 'E0028'))
    e['skills'].update(SK_SYSTEM_DESIGN=1, SK_CLOUD=5, SK_CICD=5)
    result = calculate_development(e, [], dataset[2], '2026-10-01', 1)
    ids = {o.event_id for o in result.available_events}
    assert 'EV_006' not in ids
    assert 'EV_009' not in ids


def test_local_completion_on_review_day_is_after_loaded_baseline(dataset):
    e = profile(dataset); catalog = dataset[2]
    e['last_review_date'] = '2026-10-01'
    e['skills']['SK_TEAMWORK'] = 0
    r = record('EV_004', date='2026-09-20')
    r.update(effective_date='2026-10-01', completed_at='2026-09-23T09:00:00Z')
    assert effective_skills(e, [r], catalog)['SK_TEAMWORK'] == 1
