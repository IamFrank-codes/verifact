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
        domain = urlparse(url).netloc.lower().removeprefix('www.')
        for rule in self.data['rules']:
            if domain == rule['domain'] or domain.endswith('.' + rule['domain']):
                return {**rule, 'domain': domain, 'policy_version': self.version}
        default = self.data['default']
        return {**default, 'domain': domain, 'policy_version': self.version}

policy = SourcePolicy()
