# VeriFact local hybrid provider testing

VeriFact supports two local testing paths. The default path is deterministic and requires no credentials. The optional hybrid path uses the same OpenAI, Google Fact Check, NewsAPI, GDELT, and SMTP interfaces used in production, but reads every credential only from an ignored local environment file.

## 1. Default: Local Mock Mode

Run the normal command for fully deterministic test evidence:

```bash
docker compose up --build
```

This uses `VERIFACT_MODE=local-fixture`. It never contacts live providers, uses demonstration records only for fixture phrases, and may show a local password-reset token for development. It is the safe fallback when `.env.hybrid` does not exist or `VERIFACT_LOCAL_REAL_API_MODE=false`.

## 2. Optional: Local Real-API Mode

Create your untracked local credentials file from the example:

```bash
cp .env.hybrid.example .env.hybrid
chmod 600 .env.hybrid
```

On Windows PowerShell, use:

```powershell
Copy-Item .env.hybrid.example .env.hybrid
notepad .env.hybrid
```

Set this exact switch in `.env.hybrid`:

```text
VERIFACT_LOCAL_REAL_API_MODE=true
```

Then add only the credentials you have, for example `VERIFACT_OPENAI_API_KEY`, `VERIFACT_GOOGLE_FACTCHECK_KEY`, `VERIFACT_NEWSAPI_KEY`, and the `VERIFACT_SMTP_*` values. Do not send keys in chat, place them in frontend code, commit them, or use them in screenshots.

Start hybrid mode with the override file:

```bash
docker compose -f docker-compose.yml -f docker-compose.hybrid.yml up --build
```

On Windows PowerShell, run the same command from the cloned `verifact-fixed` folder.

## Behavioral guarantees

| Mode | Live network providers | Fixture evidence | Password reset behavior |
|---|---:|---:|---|
| `local-fixture` | No | Yes, deterministic demo data | Development token may be shown locally |
| `hybrid` + `VERIFACT_LOCAL_REAL_API_MODE=false` | No | Yes, deterministic mock behavior | No production SMTP call |
| `hybrid` + `VERIFACT_LOCAL_REAL_API_MODE=true` | Yes, only configured providers | **No** | Sends SMTP email only when SMTP is configured |
| `production` | Yes, only configured providers | **No** | SMTP-only; reset token is never shown in the UI |

In Local Real-API Mode, a missing or failing provider is recorded as a provider limitation. VeriFact does not replace it with fixture evidence, invent sources, or interpret an AI response as definitive truth. A score is still generated only if retained evidence satisfies the configured policy rules.

## Verify your local setup

After starting the stack, inspect the services and worker:

```bash
docker compose -f docker-compose.yml -f docker-compose.hybrid.yml ps
docker compose -f docker-compose.yml -f docker-compose.hybrid.yml logs --tail=80 verifact-api verifact-worker
```

Submit a non-fixture claim through the interface at `http://localhost:5173`. The report’s retrieval record identifies configured providers and any limitations. Do not use canned fixture phrases to judge real-provider behavior.

To return to deterministic testing, stop hybrid services and start the default stack again:

```bash
docker compose -f docker-compose.yml -f docker-compose.hybrid.yml down
docker compose up --build
```
