# VeriFact validation log

## 2026-08-26 local interface review

The local Vite frontend at `http://localhost:5173` rendered the VeriFact sign-in page with the requested brand name, tagline, evidence-first messaging, and a professional navy/light visual identity. The registration page opened correctly and exposed full name, email address, password, confirmation, and an account-creation action. The initial desktop layout was visually coherent, responsive-looking, and did not resemble a generic AI chatbot.

The next validation steps will exercise registration, score-eligible fixture verification, scoreless insufficient-evidence verification, report sharing, history, and password reset.

The local registration flow accepted a strong test password and routed the new user to the authenticated VeriFact dashboard. The dashboard correctly showed zero reports, an explicitly empty eligible-score average, a zero scoreless-evidence count, source-policy version 1.0, the primary verification action, and a purposeful no-report state. Branding and dashboard hierarchy were consistent with the approved design direction.

The score-eligible local fixture workflow completed successfully. The report presented **Scored — evidence coverage sufficient** before the 80/100 value; disclosed 100% weighted claim coverage, policy version, formula components, and the statement that the score is not a measure of absolute truth. It rendered the evidence-bounded claim assessment, dated World Health Organization and CDC source cards, source-policy classifications, local-demonstration labeling, and a public-share control.

Expanding the claim evidence exposed the retained source excerpts, direct relevance explanations, canonical outbound links, provider provenance, local-fixture labels, dates, policy class, policy rule, policy rationale, and policy version. The report explicitly showed empty contradicting/contextual groups rather than inventing records. The verification form also clearly describes the local fixture inputs and scoreless fallback.

The insufficient-evidence fixture workflow completed successfully and met the core product rule. Its report showed **Insufficient evidence — no overall score**, displayed “No overall score” rather than a number, described the configurable 60% coverage and qualifying-source-policy threshold, and stated that the result is not a finding that the submitted claim is true or false. The claim itself was labeled **Insufficient Evidence** and showed zero retained records without fabricated citations.

The signed-in test user could sign out successfully, returning to the branded login page. The password-recovery page opened correctly and stated the neutral account-enumeration-safe message that reset instructions are sent only if an account exists.

In `local-fixture` mode, password-reset submission returned the same neutral account-existence message and displayed a development-only reset token plus continuation action. This behavior is documented as local-only; the production configuration must use a mail provider and never reveal reset tokens in the UI.

Browser testing exposed and corrected a client-side query-path issue in the reset continuation. The navigation handler now stores `location.pathname` after route changes, allowing the `/reset?token=…` URL to render the reset form correctly. The corrected reset form now pre-populates the local development token and displays the new-password controls.

The reset-form submission surfaced an API failure rendered as “VeriFact could not read the server response.” This is a validation defect rather than an accepted outcome. The next step is to inspect the API log, correct the backend reset handling, rerun the backend tests, and repeat the browser reset/login check.

After applying the timezone-safe expiry correction and adding regression coverage, the corrected reset form was reloaded and accepted the new password input. The final submission and reauthentication check remain in progress.

The local API was restarted after the code correction so the corrected password-reset handler is now active. The pending reset link reloads successfully and awaits final submission.

The corrected browser-based reset request completed successfully and displayed the confirmation that the password was updated. The API regression suite also passes with explicit reset-and-relogin coverage.

The reset flow returned to the branded sign-in page, where the test account’s email and newly reset password were accepted by the form. Final sign-in confirmation is the last browser-based acceptance step.

The final reauthentication check succeeded. The dashboard now correctly shows two completed reports: one 80/100 eligible evidence-backed report and one explicitly scoreless insufficient-evidence report. The aggregate average uses eligible scored reports only, while the scoreless-evidence counter remains distinct. The local journey from registration through verification, reporting, logout, reset, and login again is complete.

## Final automated validation

The backend regression suite completed with **4 passing tests**, covering an eligible scored fixture report, a scoreless insufficient-evidence report, private-to-public report access without account data, and reset-password followed by reauthentication. The React application completed a TypeScript production build successfully. The static delivery validator confirmed the Compose graph contains the database, Redis, Mailpit, API, worker, and frontend services plus all required Docker/configuration/documentation assets.

The sandbox does not include a Docker daemon, so `docker compose config` and container runtime validation could not be executed here. The delivered Compose files were instead parsed and checked statically; the README retains the exact Compose command for a Docker-enabled environment.
