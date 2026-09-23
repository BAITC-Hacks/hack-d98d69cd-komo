from app.qa_acceptance import prepare

def test_ai_counterfactual_cases_have_equal_competing_options(dataset):
    from app.features.data_import.service import parse_history
    from app.features.development.logic import calculate_development, history_facts, rank_candidates
    data = prepare(); history = parse_history(data['history_csv'].encode()); options = []
    for p in data['bundle']['employees'][6:]:
        records = [r for r in history if r['employee_id'] == p['employee_id']]
        dev = calculate_development(p, records, dataset[2], '2026-10-01', 1)
        candidates = {o.event_id: o for o in dev.available_events}
        assert {'EV_006', 'EV_007'} <= candidates.keys()
        assert candidates['EV_006'].expected_progress == candidates['EV_007'].expected_progress
        expected = 'EV_007' if p['employee_id'].endswith('ONLINE') else 'EV_006'
        facts = history_facts(records, candidates[expected], dataset[2])
        assert facts['same_event_recent_missed'] == 0
        assert rank_candidates(dev, records, dataset[2])[0].event_id == expected
        options.append(set(candidates))
    assert all(o == options[0] for o in options)

