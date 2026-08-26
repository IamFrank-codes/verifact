# VeriFact security controls

VeriFact hashes passwords with Argon2 and uses signed, `HttpOnly` access cookies. Production deployment must set a strong `VERIFACT_SECRET_KEY`, `VERIFACT_SECURE_COOKIES=true`, a specific `VERIFACT_FRONTEND_ORIGIN`, HTTPS, and a managed database backup policy.

The URL extractor accepts only public HTTP(S) addresses. It resolves the host and rejects loopback, private, link-local, reserved, multicast, and local-domain destinations before requesting an article. Retrieval is bounded by timeout, content-type, and response-size checks. In a hardened production deployment, repeat DNS/IP validation after every redirect at the network client layer as well.

Password-reset endpoints return the same generic response whether an account exists. Reset tokens are hashed, expire after 30 minutes, and are marked used after success. Development reset tokens are returned only in `local-fixture` mode and must never be enabled in production.
