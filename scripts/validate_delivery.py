from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text()) or {}


def require(condition: bool, message: str):
    if not condition:
        raise SystemExit(message)


dev = load_yaml(root / 'docker-compose.yml')
hybrid = load_yaml(root / 'docker-compose.hybrid.yml')
prod = load_yaml(root / 'docker-compose.prod.yml')
dev_services = set(dev.get('services', {}))
hybrid_services = set(hybrid.get('services', {}))
prod_services = set(prod.get('services', {}))
require({'verifact-db', 'verifact-redis', 'verifact-mailpit', 'verifact-api', 'verifact-worker', 'verifact-frontend'} <= dev_services, 'Development Compose is missing a required VeriFact service.')
require({'verifact-api', 'verifact-worker'} <= hybrid_services, 'Hybrid Compose must configure both API and worker services.')
require({'verifact-db', 'verifact-redis', 'verifact-migrate', 'verifact-api', 'verifact-worker', 'verifact-frontend', 'verifact-proxy'} <= prod_services, 'Production Compose is missing a required VeriFact service.')
require(dev['services']['verifact-frontend'].get('environment', {}).get('VITE_API_PROXY_TARGET') == 'http://verifact-api:8000', 'Development frontend must proxy Docker API traffic to verifact-api.')
require(hybrid['services']['verifact-api'].get('environment', {}).get('VERIFACT_MODE') == 'hybrid', 'Hybrid API must explicitly use hybrid mode.')
require(hybrid['services']['verifact-api'].get('env_file') == ['.env.hybrid'], 'Hybrid provider credentials must come only from .env.hybrid.')
require(hybrid['services']['verifact-worker'].get('env_file') == ['.env.hybrid'], 'Hybrid worker credentials must come only from .env.hybrid.')
require(prod['services']['verifact-proxy'].get('image', '').startswith('caddy:'), 'Production must terminate HTTPS through the Caddy reverse proxy.')
require(prod['services']['verifact-migrate'].get('command') == 'alembic upgrade head', 'Production must include an Alembic migration service.')
require('python -m app.worker' in prod['services']['verifact-worker'].get('command', ''), 'Production worker must run as a separate worker process.')
for path in (
    'backend/Dockerfile', 'frontend/Dockerfile', '.env.example', '.env.hybrid.example', '.env.production.example',
    'README.md', 'docs/SCORING_AND_EVIDENCE.md', 'docs/SECURITY.md', 'docs/deployment.md', 'docs/hybrid-local-testing.md',
    'backend/app/fixtures/source_policy.json', 'ops/Caddyfile',
    'ops/backup-postgres.sh', 'ops/restore-postgres.sh', 'scripts/production_smoke.sh',
):
    require((root / path).is_file(), f'Missing required delivery file: {path}')
require('.env.hybrid' in (root / '.gitignore').read_text(), '.env.hybrid must remain ignored by Git.')
print('VeriFact development, hybrid, and production delivery configuration passed static validation.')
print('Development services:', ', '.join(sorted(dev_services)))
print('Hybrid services:', ', '.join(sorted(hybrid_services)))
print('Production services:', ', '.join(sorted(prod_services)))
