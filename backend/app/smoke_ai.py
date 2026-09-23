"""One real provider check. No secrets or raw profile are printed."""
import argparse
import json
import time
import httpx
from app.core.config import settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fresh', action='store_true')
    args = parser.parse_args()
    config = settings()
    with httpx.Client(base_url='http://localhost:8000/api/v1', timeout=12) as client:
        auth = client.post('/auth/login', json={'username': 'employee', 'password': config.employee_password})
        auth.raise_for_status()
        employee_id = auth.json()['employee_id']
        started = time.monotonic()
        response = client.post(f'/employees/{employee_id}/recommendations', params={'refresh': str(args.fresh).lower()})
        response.raise_for_status()
        result = response.json()
        print(json.dumps({'status': response.status_code, 'source': result['source'], 'cached': result['cached'],
                          'seconds': round(time.monotonic() - started, 3), 'model': result['model'],
                          'event_ids': [s['activity']['event_id'] for s in result['steps']],
                          'factors': [len(s['evidence']) for s in result['steps']]}, ensure_ascii=False))
        if result['source'] != 'ai' or not result['steps']:
            raise SystemExit('Real AI not verified; check provider access and API logs.')
        if result['cached']:
            print('Cached AI result; wait 5 minutes or change data revision to verify a fresh provider call.')


if __name__ == '__main__':
    main()
