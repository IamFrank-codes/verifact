# VeriFact technical diagrams

This directory contains source-controlled diagrams derived from the current VeriFact implementation.

| Diagram | Mermaid source | Rendered image | Purpose |
|---|---|---|---|
| Class diagram | [verifact-class-diagram.mmd](verifact-class-diagram.mmd) | [verifact-class-diagram.png](verifact-class-diagram.png) | Shows the implemented SQLAlchemy domain models and the named configuration, policy, provider, and structured-analysis classes. |
| Architecture diagram | [verifact-architecture-diagram.mmd](verifact-architecture-diagram.mmd) | [verifact-architecture-diagram.png](verifact-architecture-diagram.png) | Shows the browser/client, FastAPI service, worker, data stores, fixtures, provider interfaces, SMTP path, and production HTTPS edge. |

> The diagrams deliberately use the exact Python class names and service module names found in VeriFact. They describe the implemented system; they are not a future-state redesign.

To regenerate the images after a code change:

```bash
manus-render-diagram docs/diagrams/verifact-class-diagram.mmd docs/diagrams/verifact-class-diagram.png
manus-render-diagram docs/diagrams/verifact-architecture-diagram.mmd docs/diagrams/verifact-architecture-diagram.png
```

See [VALIDATION.md](VALIDATION.md) for the source-to-diagram validation record.
