# Plutus-AI2 — Fix AI API authentication

## Critical: rotate leaked secrets

This repository previously committed `config/.env` publicly. Removing it from
the latest commit does NOT erase old commit history. Treat every credential in
that file as compromised and immediately revoke/rotate all of them:
`GROQ_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, and Django
`SECRET_KEY`. Audit usage and unexpected charges in each provider.

The repo also tracks `db.sqlite3`. Check whether it contains user records or
password hashes. Treat exposed account data as a separate incident; removing
the database without a migration/persistence plan can break the deployed app.

## Fix the running site on Render

1. Create a **new** Groq key at https://console.groq.com/keys.
2. In the Render dashboard open the **Web Service** running this app,
   then **Environment**.
3. Set `GROQ_API_KEY` to the **new** key. Do not add the key to GitHub.
   If the service already defines this variable, replace its value.
4. Rotate `SECRET_KEY` and update its Render environment value.
   Rotating it may log users out. Update `ALLOWED_HOSTS` for your actual domain.
5. Save the environment changes and deploy/redeploy the latest commit.
6. Log in and send a short test chat prompt. A 401 indicates a rejected key;
   429 indicates rate limiting/quota; a missing-key message means the environment
   variable was not supplied to the running process.
7. Revoke the old key(s). Do not paste API keys into an issue, chat, or commit.

Local development: copy `.env.example` to `.env` and replace placeholders.
The Django settings also supports a legacy local `config/.env`, but that file
must never be committed.

The Groq model is set by `GROQ_MODEL`, default
`llama-3.3-70b-versatile`. If the model is unavailable for the specific
provider account, pick a model shown in the Groq console.

## Check the fix locally

```sh
python manage.py test assistant
```

With no `GROQ_API_KEY`, the endpoint returns a clean 503 and
`missing_api_key`. With an invalid key, it returns 503 and
`invalid_api_key`. Provider rate limits return 429 rather than a misleading
200 response.

**Important:** Updating GitHub cannot create a new Groq credential or change
a Render environment variable by itself.
