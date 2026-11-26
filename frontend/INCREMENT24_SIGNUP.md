# Increment 24 — Sign-up UI

The login screen now has separate **Sign in** and **Create account** tabs. Sign-up uses the existing Supabase project with the publishable key, enforces matching passwords and an eight-character minimum in the UI, and requests trusted backend provisioning after Supabase returns an authenticated session. When email confirmation is enabled, the user is prompted to confirm their address and then sign in; the sign-in flow completes provisioning.

No service-role key or database credential is used in the browser/frontend. Existing sign-in behavior remains available.

See the backend `docs/INCREMENT24_SECURE_SIGNUP.md` for the migration and deployment steps.
