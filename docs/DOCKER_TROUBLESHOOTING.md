# VeriFact Docker troubleshooting

## Registration displays “VeriFact could not read the server response”

This message was caused by the frontend development server attempting to proxy API requests to `localhost:8000` **inside the frontend container**. In Docker, that address refers to the frontend container rather than the `verifact-api` service.

The corrected configuration sets:

```yaml
VITE_API_PROXY_TARGET: http://verifact-api:8000
```

This allows the Vite frontend service to send `/api/*` requests over Docker’s internal network to the API container.

## Apply the correction

If you extracted the earlier VeriFact archive, replace both `frontend/vite.config.ts` and `docker-compose.yml` with their corrected versions from the updated archive. Then, from the project directory, restart the stack:

```bash
docker compose down
docker compose up --build
```

If Docker has retained an old frontend dependency/container state, use:

```bash
docker compose down --volumes --remove-orphans
docker compose up --build
```

> Removing volumes deletes local VeriFact accounts and verification reports. Use it only for a clean local reset.

After the services start, open `http://localhost:5173`, create an account using any valid-format test email and a password of at least 10 characters containing uppercase, lowercase, and a number, then sign in with those same credentials.

## Collect logs if it still fails

Run these commands from the VeriFact project directory and share the output:

```bash
docker compose ps
docker compose logs --tail=120 verifact-api verifact-frontend
```

The API log should show a `201 Created` response for `POST /api/v1/auth/register`. If it instead shows `500`, the backend traceback identifies the next issue precisely.
