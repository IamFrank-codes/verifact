# Academic Demo diagrams

These source-controlled diagrams describe the VeriFact Academic Demo and its primary data relationships.

| Diagram | Mermaid source | Rendered image | Purpose |
|---|---|---|---|
| Domain class diagram | [verifact-class-diagram.mmd](verifact-class-diagram.mmd) | [verifact-class-diagram.png](verifact-class-diagram.png) | Shows the account, verification, claim, evidence, source-policy, and provider-analysis relationships used by the demo. |
| Academic Demo architecture | [verifact-architecture-diagram.mmd](verifact-architecture-diagram.mmd) | [verifact-architecture-diagram.png](verifact-architecture-diagram.png) | Shows the local browser, frontend, API, database, evidence providers, and optional email service. |

To regenerate the images after changing a source diagram:

```bash
manus-render-diagram docs/diagrams/verifact-class-diagram.mmd docs/diagrams/verifact-class-diagram.png
manus-render-diagram docs/diagrams/verifact-architecture-diagram.mmd docs/diagrams/verifact-architecture-diagram.png
```

See [VALIDATION.md](VALIDATION.md) for the diagram review record.
