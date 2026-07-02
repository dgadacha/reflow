# Reflow

Transforme une vidéo YouTube (ou un podcast) en une semaine de contenu : article de
blog SEO, thread X, post LinkedIn, newsletter, légendes Instagram/TikTok et idées de
clips — en un seul clic.

MVP : **FastAPI** (backend) + **Astro/Vue** (frontend) + **Claude Opus 4.8**.

```
reflow/
├── start.sh          lance backend + frontend ensemble
├── backend/          API FastAPI (transcription + génération)
│   ├── main.py
│   ├── core/         config + quota
│   └── services/     transcribe (yt-dlp/Whisper) + generate (Claude)
└── frontend/         interface Astro + Vue
```

## Lancer en local

### Lancement rapide (recommandé)

```bash
./start.sh
```

Au premier lancement, le script crée le venv, installe les dépendances Python/npm
et prépare le `.env`. Ensuite il démarre backend (port 8787) et frontend (port 4321).
**Ctrl+C arrête les deux.**

> ⚠ Renseigne ta clé `ANTHROPIC_API_KEY` dans `backend/.env` avant de tester
> (le script crée le fichier mais ne l'écrase jamais).

Puis ouvre http://localhost:4321 et colle un lien YouTube.

### Lancement manuel (option)

**Backend** (port 8787) :

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # puis renseigner ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8787
```

**Frontend** (port 4321) :

```bash
cd frontend
npm install
npm run dev
```

Test rapide du backend : `curl -X POST localhost:8787/api/process -H "Content-Type: application/json" -d '{"url":"https://youtube.com/watch?v=..."}'`

> La transcription utilise d'abord les **sous-titres YouTube** (gratuit, instantané).
> Pour les vidéos sans sous-titres, active Whisper : `pip install faster-whisper`,
> installe `ffmpeg`, puis `REFLOW_WHISPER=true` dans `.env`.
>
> Backend distant : pointe le frontend via la variable d'env `PUBLIC_API_URL`.

## Économie du MVP

| Poste | Coût réel par vidéo | Prix de vente cible |
|-------|---------------------|---------------------|
| Sous-titres YouTube | 0 € | — |
| Génération Claude (~15-40k tokens) | ~0,10–0,40 $ | inclus dans l'abonnement |
| **Abonnement** | | 19 $ (20 vidéos) / 49 $ (illimité soft) / 99 $ (équipe) |

Marge > 85 %. Le quota gratuit (3 vidéos/mois) sert de hook d'acquisition.

## Passer en production

Les points d'extension sont balisés dans le code (`TODO`/commentaires) :

1. **Auth** — remplacer le quota par IP (`core/quota.py`) par Supabase Auth :
   récupérer `user_id` depuis le JWT dans `main.py::process`.
2. **Abonnements** — brancher **Stripe Billing** (webhooks `checkout.session.completed`
   et `customer.subscription.*`) → table `subscriptions` dans Supabase. Vérifier
   l'abonnement actif *avant* `check_and_reserve`.
3. **Quota** — migrer `core/quota.py` vers une table `usage` (colonnes : user_id,
   period, count) au lieu du fichier JSON local.
4. **File d'attente** — pour Whisper, passer le traitement en tâche asynchrone
   (Celery/RQ) et renvoyer un job_id + polling, plutôt qu'une requête bloquante.
5. **Déploiement** — backend sur Railway/Fly.io, frontend sur Vercel/Netlify.

## Prochaines features à fort levier

- Export direct (copie ✓ déjà là) → publication programmée (Buffer/API réseaux).
- Détection de timestamps précis pour les clips (nécessite le transcript horodaté).
- Multi-langue de sortie (traduire le contenu généré).
- Upload de fichier audio/vidéo (podcasts hors YouTube).
