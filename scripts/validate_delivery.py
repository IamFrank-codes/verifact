from pathlib import Path
import sys
import yaml

root = Path(__file__).resolve().parents[1]
compose = yaml.safe_load((root / 'docker-compose.yml').read_text())
required = {'verifact-db', 'verifact-redis', 'verifact-mailpit', 'verifact-api', 'verifact-worker', 'verifact-frontend'}
actual = set(compose.get('services', {}))
missing = required - actual
if missing:
    raise SystemExit(f'Missing required Compose services: {sorted(missing)}')
for service in ('verifact-api', 'verifact-worker'):
    if 'build' not in compose['services'][service]:
        raise SystemExit(f'{service} must define a build context.')
if not ({'build', 'image'} & set(compose['services']['verifact-frontend'])):
    raise SystemExit('verifact-frontend must define either a build context or an image.')
proxy_target = compose['services']['verifact-frontend'].get('environment', {}).get('VITE_API_PROXY_TARGET')
if proxy_target != 'http://verifact-api:8000':
    raise SystemExit('verifact-frontend must proxy Docker API traffic to http://verifact-api:8000.')
for path in ('backend/Dockerfile', 'frontend/Dockerfile', '.env.example', 'README.md', 'docs/SCORING_AND_EVIDENCE.md', 'docs/SECURITY.md', 'backend/app/fixtures/source_policy.json'):
    if not (root / path).is_file():
        raise SystemExit(f'Missing required delivery file: {path}')
print('VeriFact delivery configuration passed static validation.')
print('Services:', ', '.join(sorted(actual)))
