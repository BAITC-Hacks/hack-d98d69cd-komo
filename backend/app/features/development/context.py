"""Content-addressed versions, independent of other employees' mutations."""
import hashlib
import json

LOGIC_VERSION = 'development-5'


def digest(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(encoded.encode()).hexdigest()


def context_version(employee, history, catalog, as_of) -> str:
    return digest({
        'logic': LOGIC_VERSION, 'as_of': as_of, 'employee': employee,
        'history': sorted(history, key=lambda r: r['record_id']),
        'catalog': {'skills': catalog.skills, 'events': catalog.events,
                    'roles': [catalog.roles[key] for key in sorted(catalog.roles)]},
    })
