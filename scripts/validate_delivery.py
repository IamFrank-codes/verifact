from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str):
    if not condition:
        raise SystemExit(message)


compose_path = root / 'docker-compose.academic.yml'
compose = yaml.safe_load(compose_path.read_text()) or {}
services = compose.get('services', {})
require({'verifact-api', 'verifact-frontend'} <= set(services), 'Academic demo Compose must include the API and frontend.')
require(set(services) == {'verifact-api', 'verifact-frontend'}, 'Academic demo Compose should contain only its API and frontend services.')

api = services['verifact-api']
api_environment = api.get('environment', {})
require(api_environment.get('VERIFACT_MODE') == 'academic-demo', 'Academic demo API must use the academic-demo profile.')
require(str(api_environment.get('VERIFACT_INLINE_PROCESSING', '')).lower() == 'true', 'Academic demo verification must run inline.')
require(api.get('env_file') == ['./backend/.env'], 'Academic demo credentials must come from backend/.env.')
frontend = services['verifact-frontend']
require(frontend.get('environment', {}).get('VITE_API_PROXY_TARGET') == 'http://verifact-api:8000', 'Academic demo frontend must proxy API requests to the API service.')

for path in (
    '.env.academic-demo.example',
    'README.md',
    'docs/academic-demo.md',
    'docs/SCORING_AND_EVIDENCE.md',
    'docs/SECURITY.md',
    'docs/supabase.md',
    'backend/app/fixtures/source_policy.json',
    'scripts/academic_demo.sh',
    'scripts/academic_demo.ps1',
):
    require((root / path).is_file(), f'Missing academic demo file: {path}')

academic_env = (root / '.env.academic-demo.example').read_text()
require('VERIFACT_MODE=academic-demo' in academic_env, 'Academic environment template must select the academic-demo profile.')
require('VERIFACT_INLINE_PROCESSING=true' in academic_env, 'Academic environment template must enable inline processing.')
require('VERIFACT_GDELT_ENABLED=true' in academic_env, 'Academic environment template must enable GDELT.')
print('VeriFact Academic Demo configuration passed static validation.')
print('Academic demo services:', ', '.join(sorted(services)))
