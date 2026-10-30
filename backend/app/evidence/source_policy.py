import json
from pathlib import Path
from urllib.parse import urlparse
from app.core.config import get_settings

class SourcePolicy:
    def __init__(self):
        path = Path(get_settings().source_policy_path)
        if not path.exists():
            path = Path(__file__).resolve().parents[1] / 'fixtures' / 'source_policy.json'
        self.data = json.loads(path.read_text())
        self.version = self.data['version']

    def classify(self, url: str) -> dict:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().removeprefix('www.')
        path = parsed.path.lower()
        for rule in self.data['rules']:
            if domain == rule['domain'] or domain.endswith('.' + rule['domain']):
                path_prefix = rule.get('path_prefix')
                if path_prefix:
                    prefix = path_prefix.lower().rstrip('/')
                    if path != prefix and not path.startswith(prefix + '/'):
                        continue
                return {**rule, 'domain': domain, 'policy_version': self.version}
        default = self.data['default']
        return {**default, 'domain': domain, 'policy_version': self.version}

policy = SourcePolicy()
