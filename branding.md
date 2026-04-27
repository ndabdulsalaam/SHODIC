# Fildah/RxChat Manual Branding Checklist

Use this checklist for settings that live outside the repository.

## Vercel

- Add `rxchat.fildah.com` as the production domain for the RxChat frontend.
- Set `VITE_API_BASE_URL=https://api.fildah.com`.
- Redeploy the frontend after changing environment variables.
- Keep `rxchat.vercel.app` only as a preview/fallback URL if you still need it.
- Give each future Fildah product its own frontend project/deployment, domain, and `VITE_API_BASE_URL=https://api.fildah.com`.
- Keep each frontend's product API namespace in its own product config, like RxChat uses `rxchat`.

## Render

- Add `api.fildah.com` as the backend custom domain.
- Set `ALLOWED_HOSTS=api.fildah.com,localhost,127.0.0.1,[::1]`.
- Set `ALLOWED_ORIGINS=https://rxchat.fildah.com,https://fildah.com,http://localhost:5173,http://localhost:3000`.
- Add `BREVO_SENDER_NAME_RXCHAT=RxChat`.
- Keep OpenRouter and Qdrant settings product-specific; RxChat can continue using its existing OpenRouter setup and Qdrant collection.
- Keep the deployment/start command running `python manage.py adopt_chat_migrations_for_rxchat` before `python manage.py migrate` for the first deployment after this rename.
- Optionally rename the Render service display name from `rxchat-backend` to `fildah-api`.

## Hostinger/DNS

- Point `api.fildah.com` to Render using Render's provided DNS target.
- Point `rxchat.fildah.com` to Vercel using Vercel's provided DNS target.
- Reserve `fildah.com` and `www.fildah.com` for the main Fildah company/account site.
- Wait for DNS propagation before testing Google OAuth and cookie/session behavior.

## Google OAuth Console

- Add authorized redirect URI `https://api.fildah.com/auth/google/callback/`.
- Keep local redirect URI `http://localhost:8000/auth/google/callback/`.
- Add `fildah.com` as an authorized domain.
- Update the OAuth consent screen app name, logo, privacy policy, support email, and homepage to match Fildah/RxChat.
- Remove old `/api/auth/google/callback/` redirect URIs only after the new production login flow is verified.

## Brevo

- Verify the Fildah sending domain or sender email.
- Keep RxChat-specific OTP template wording in Brevo.
- Use `BREVO_SENDER_NAME_RXCHAT=RxChat` for RxChat OTP sender branding.
- If future products use Brevo, give each product its own sender/template convention instead of reusing RxChat wording.

## Deployment Smoke Test

- Visit `https://rxchat.fildah.com`.
- Confirm the frontend calls `https://api.fildah.com/auth/me/`.
- Register or log in with OTP.
- Test Google login and confirm the callback uses `/auth/google/callback/`.
- Send a chat message and confirm the frontend calls `/rxchat/send/`.
- Open Django admin and confirm `Fildah` shows all admin apps while `RxChat` filters the index to RxChat sections.
