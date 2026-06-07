# AURA Render Deployment Guide

This project is prepared for deployment as a Render Python web service.

## What Render Runs

- Build command:
  `pip install -r requirements.txt && python -m nltk.downloader -d nltk_data punkt stopwords wordnet averaged_perceptron_tagger`

- Start command:
  `gunicorn --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT app:app`

- SQLite path on Render:
  `/var/data/aura.db`

The `/var/data` folder is a Render persistent disk mount. Without a persistent
disk, SQLite data can disappear after deploys or restarts.

## Environment Variables

Add these in Render if you create the service manually. If you use
`render.yaml`, Render will prefill most of them and ask you for the secret
values marked as private.

| Key | Value |
| --- | --- |
| `SECRET_KEY` | Generate a long random value |
| `AURA_DB_PATH` | `/var/data/aura.db` |
| `NLTK_DATA` | `/opt/render/project/src/nltk_data` |
| `SESSION_COOKIE_SECURE` | `true` |
| `MAIL_SERVER` | `smtp.gmail.com` |
| `MAIL_PORT` | `587` |
| `MAIL_USE_TLS` | `true` |
| `MAIL_USE_SSL` | `false` |
| `MAIL_USERNAME` | Your Gmail address |
| `MAIL_PASSWORD` | Your Gmail app password |
| `MAIL_DEFAULT_SENDER` | Your Gmail address |
| `MAIL_SENDER_NAME` | `AURA - IZee` |

Use a Gmail app password, not your normal Gmail password.

## GitHub Steps

1. Open a terminal in the `aura` folder.
2. Remove generated/private files from Git tracking if they are already tracked:
   `git rm --cached aura.db __pycache__/*.pyc models/__pycache__/*.pyc gpt_module/__pycache__/*.pyc`
3. Add the deployment files and code changes:
   `git add .`
4. Commit:
   `git commit -m "Prepare AURA for Render deployment"`
5. Create a GitHub repository.
6. Add the remote:
   `git remote add origin https://github.com/YOUR_USERNAME/aura.git`
7. Push:
   `git push -u origin main`

If your branch is named `master`, use:
`git push -u origin master`

## Render Blueprint Deployment

1. Sign in to Render.
2. Choose **New** > **Blueprint**.
3. Connect your GitHub account if it is not connected yet.
4. Select the repository that contains this `aura` folder.
5. Render will read `render.yaml`.
6. Enter the private environment variables when Render asks for them.
7. Deploy the service.
8. After deployment, Render will show a permanent URL such as:
   `https://aura-izee.onrender.com`

## Manual Render Deployment

Use this if you do not use the Blueprint flow.

1. Choose **New** > **Web Service** in Render.
2. Connect the GitHub repository.
3. Set root directory to `aura` if your repository contains a parent folder.
4. Runtime: Python.
5. Build command:
   `pip install -r requirements.txt && python -m nltk.downloader -d nltk_data punkt stopwords wordnet averaged_perceptron_tagger`
6. Start command:
   `gunicorn --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT app:app`
7. Add a persistent disk:
   - Name: `aura-data`
   - Mount path: `/var/data`
   - Size: `1 GB`
8. Add all environment variables listed above.
9. Deploy.

## Notes

- Keep `aura.db`, `.env`, logs, and `__pycache__` files out of Git.
- Render will start the web service automatically when the public URL receives
  traffic. Free services can have a cold-start delay; a paid service stays more
  consistently available.
- This project uses one Gunicorn worker because OTPs are stored in memory during
  the short email verification window. For multiple workers, move OTP storage
  into the database or Redis.
