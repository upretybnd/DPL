# Dynamic Public Library

Website and management system for Dynamic Public Library (DPL) — a network of community libraries across Nepal.
Django 4.2 with server-rendered templates, Tailwind CSS and Alpine.js.

## What's inside

| App | Purpose |
|---|---|
| `web` | Home, about, contact, donations, newsletter, policy pages |
| `branches` | Chapters, teens wings, National Board and DPL Senate; teams, galleries, programs |
| `reports` | Project reporting workflow, dashboards, analytics, public impact pages, notifications |
| `forum` | Discussion forum and member profiles |
| `accounts` | Sign-up with email verification, login, password reset, election nominations |

## Local setup

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (source venv/bin/activate on Linux/macOS)
pip install -r requirements.txt
cp .env.example .env              # then set DEBUG=True and ENVIRONMENT=development for local work
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Frontend (Tailwind)

Styles live in `frontend/app.css` (design tokens + components) and compile to `dpl/static/css/app.css`,
which is committed so servers don't need Node.

```bash
npm install
npm run watch:css    # while editing templates
npm run build:css    # before committing
```

- Fonts: **Fraunces** (headings), **Plus Jakarta Sans** (UI), **Mukta** (Devanagari fallback)
- Icons: [Lucide](https://lucide.dev) via `<i data-lucide="name">`
- Shared partials: `templates/include/` (`page_header`, `field`, `pagination`, `empty_state`, `seo`)

## SEO

Every page sets its title/description/Open Graph tags through `include/seo.html`. Chapters, programs and
public reports add JSON-LD. `/sitemap.xml` and `/robots.txt` are generated automatically.

## Tests

```bash
python manage.py test
```

## Deploying

Set production values in `.env` (see `.env.example`): `DEBUG=False`, a real `SECRET_KEY`, `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS`, database, email and donation details. Then:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Serve `STATIC_ROOT` and `MEDIA_ROOT` from the web server. Uploaded candidacy documents and payment proofs
are sensitive — restrict `/media/citizenship_documents/`, `/media/payment_screenshots/` and
`/media/donation_proofs/` to admins rather than serving them publicly.
