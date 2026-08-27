from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text()) or {}


def require(condition: bool, message: str):
    if not condition:
        raise SystemExit(message)


dev = load_yaml(root / 'docker-compose.yml')
prod = load_yaml(root / 'docker-compose.prod.yml')
dev_services = set(dev.get('services', {}))
prod_services = set(prod.get('services', {}))
require({'verifact-db', 'verifact-redis', 'verifact-mailpit', 'verifact-api', 'verifact-worker', 'verifact-frontend'} <= dev_services, 'Development Compose is missing a required VeriFact service.')
require({'verifact-db', 'verifact-redis', 'verifact-migrate', 'verifact-api', 'verifact-worker', 'verifact-frontend', 'verifact-proxy'} <= prod_services, 'Production Compose is missing a required VeriFact service.')
require(dev['services']['verifact-frontend'].get('environment', {}).get('VITE_API_PROXY_TARGET') == 'http://verifact-api:8000', 'Development frontend must proxy Docker API traffic to verifact-api.')
require(prod['services']['verifact-proxy'].get('image', '').startswith('caddy:'), 'Production must terminate HTTPS through the Caddy reverse proxy.')
require(prod['services']['verifact-migrate'].get('command') == 'alembic upgrade head', 'Production must include an Alembic migration service.')
require('python -m app.worker' in prod['services']['verifact-worker'].get('command', ''), 'Production worker must run as a separate worker process.')
for path in (
    'backend/Dockerfile', 'frontend/Dockerfile', '.env.example', '.env.production.example',
    'README.md', 'docs/SCORING_AND_EVIDENCE.md', 'docs/SECURITY.md',
    'backend/app/fixtures/source_policy.json', 'ops/Caddyfile',
    'ops/backup-postgres.sh', 'ops/restore-postgres.sh', 'scripts/production_smoke.sh',
):
    require((root / path).is_file(), f'Missing required delivery file: {path}')
print('VeriFact development and production delivery configuration passed static validation.')
print('Development services:', ', '.join(sorted(dev_services)))
print('Production services:', ', '.join(sorted(prod_services)))
