# Guide de déploiement — Ideas Studio

Ce guide couvre le déploiement complet d'Ideas Studio : backend, frontend, base de données, worker et configuration réseau.

---

## Prérequis

### Serveur (backend)

- Python 3.11 ou supérieur
- Pip et venv
- Accès à une base de données (SQLite pour dev, PostgreSQL pour production)
- Ollama (optionnel, recommandé pour l'IA locale)

### Domaine

- Un nom de domaine pour l'API (ex: `api.ideas-studio.com`)
- Un nom de domaine pour le frontend (ex: `app.ideas-studio.com`)
- Un nom de domaine pour le blog connecté (déjà existant)

---

## Variables d'environnement

### Configuration minimale

```bash
APP_NAME=Ideas Studio
APP_ENV=production
APP_URL=https://api.ideas-studio.com
DATABASE_URL=postgresql://user:password@host:5432/ideas_studio
SECRET_KEY=<généré aléatoirement — 48+ caractères>
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### Provider IA (au moins un)

```bash
# Option 1 : Ollama (local, gratuit)
DEFAULT_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:14b
OLLAMA_FALLBACK_MODEL=qwen3:8b
OLLAMA_TIMEOUT_SECONDS=180

# Option 2 : Gemini (cloud, gratuit avec quota)
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash

# Option 3 : OpenRouter (cloud, modèles gratuits disponibles)
DEFAULT_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=deepseek/deepseek-v4-flash:free

# Option 4 : OpenAI (cloud, payant)
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### Optionnel

```bash
# Mode auto : essaie OpenRouter > Ollama > OpenAI dans l'ordre
DEFAULT_LLM_PROVIDER=auto

# Recherche SERP (SearXNG auto-hébergé)
DEFAULT_SEARCH_PROVIDER=searxng
SEARXNG_URL=https://searxng.votredomaine.com

# Revalidation de cache blog
BLOG_REVALIDATE_URL=https://votreblog.com/api/revalidate
BLOG_REVALIDATE_SECRET=secret-partage

# Répertoire d'upload
UPLOAD_DIR=uploads
```

---

## Backend — Déploiement

### Option A : Render

1. Créez un compte sur [Render](https://render.com)
2. Connectez votre dépôt GitHub/GitLab
3. Créez un **Web Service** :
   - **Name** : `ideas-studio-api`
   - **Runtime** : Python 3
   - **Build Command** :
     ```bash
     python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
     ```
   - **Start Command** :
     ```bash
     ./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Health Check Path** : `/health`
4. Ajoutez toutes les variables d'environnement dans la section **Environment Variables**
5. Déployez

### Option B : Railway

1. Créez un compte sur [Railway](https://railway.app)
2. Connectez votre dépôt
3. Créez un nouveau projet depuis le dépôt
4. Railway détecte automatiquement Python
5. Ajoutez les variables d'environnement dans le dashboard
6. La commande par défaut fonctionne :
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

### Option C : Serveur VPS (manuel)

```bash
# Mettez à jour le système
sudo apt update && sudo apt upgrade -y

# Installez les dépendances
sudo apt install -y python3-pip python3-venv nginx

# Clonez le dépôt
git clone https://github.com/votre-org/ideas-studio.git /opt/ideas-studio
cd /opt/ideas-studio

# Créez l'environnement Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurez les variables d'environnement
cp .env.example .env
nano .env  # Éditez avec vos valeurs

# Appliquez les migrations
alembic upgrade head

# Créez un service systemd
sudo nano /etc/systemd/system/ideas-studio.service
```

**Fichier systemd :**

```ini
[Unit]
Description=Ideas Studio API
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/ideas-studio
Environment=PATH=/opt/ideas-studio/venv/bin
ExecStart=/opt/ideas-studio/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ideas-studio
sudo systemctl start ideas-studio
```

---

## Worker — Tâches de fond

Le worker gère les publications planifiées, les pipelines automatisés et les tâches quotidiennes.

### Service systemd

```ini
[Unit]
Description=Ideas Studio Worker
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/ideas-studio
Environment=PATH=/opt/ideas-studio/venv/bin
ExecStart=/opt/ideas-studio/venv/bin/python /opt/ideas-studio/worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ideas-studio-worker
sudo systemctl start ideas-studio-worker
```

### Vérification

```bash
# Voir les logs
sudo journalctl -u ideas-studio-worker -f

# Exécution manuelle unique
python worker.py once
```

### Que fait le worker ?

| Tâche | Horaire | Description |
|---|---|---|
| `check_scheduled_publications` | Toutes les 5 minutes | Publie les articles dont `scheduled_at` est dépassé |
| `run_daily_tasks` | 6h00 chaque jour | Génère des idées, review les articles publiés |
| `run_pipelines` | Chaque heure | Exécute les pipelines activés projet par projet |

---

## Frontend — Déploiement (Vercel)

### Configuration

1. Poussez le code sur GitHub/GitLab
2. Importez le projet dans [Vercel](https://vercel.com)
3. **Root Directory** : `frontend`
4. **Framework Preset** : Vite
5. **Build Command** : `npm run build`
6. **Output Directory** : `dist`

### Variables d'environnement (frontend)

```bash
VITE_API_URL=https://api.ideas-studio.com
```

### Fichier `frontend/vercel.json`

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

### Domaine personnalisé

Dans le dashboard Vercel :
1. Allez dans **Domains**
2. Ajoutez `app.ideas-studio.com`
3. Suivez les instructions de configuration DNS

---

## Base de données

### PostgreSQL (Recommandé pour production)

#### Installation

```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Création de la base

```bash
sudo -u postgres psql -c "CREATE USER ideas_studio WITH PASSWORD 'mot-de-passe-securise';"
sudo -u postgres psql -c "CREATE DATABASE ideas_studio OWNER ideas_studio;"
```

#### Migration depuis SQLite

```bash
# En développement
python scripts/migrate_to_postgres.py
```

#### URL de connexion

```
DATABASE_URL=postgresql://ideas_studio:mot-de-passe-securise@localhost:5432/ideas_studio
```

### Migrations Alembic

```bash
# Appliquer les migrations
alembic upgrade head

# Créer une nouvelle migration
alembic revision --autogenerate -m "description"

# Revenir en arrière
alembic downgrade -1

# Voir l'historique
alembic history
```

---

## Reverse Proxy — Nginx

### Nginx

```nginx
server {
    listen 80;
    server_name api.ideas-studio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.ideas-studio.com;

    ssl_certificate /etc/letsencrypt/live/api.ideas-studio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.ideas-studio.com/privkey.pem;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /uploads/ {
        alias /opt/ideas-studio/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Cache des fichiers statiques
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Caddy (alternative plus simple)

```caddy
api.ideas-studio.com {
    reverse_proxy 127.0.0.1:8000

    # SSL automatique via Let's Encrypt
    tls admin@ideas-studio.com

    # Limite de taille
    request_body {
        max_size 20MB
    }

    # Headers de sécurité
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        X-XSS-Protection "1; mode=block"
    }

    handle_path /uploads/* {
        root * /opt/ideas-studio
        file_server
    }
}
```

---

## Ollama en production

### Installation

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Service systemd (déjà créé par l'installateur)

```bash
sudo systemctl status ollama
```

### Limiter la mémoire GPU

```bash
# Pour Ollama en mode production avec GPU partagé
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf <<EOF
[Service]
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
EOF
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Modèles recommandés

| Modèle | RAM/VRAM | Qualité |
|---|---|---|
| `qwen3:8b` | 8 Go | Correcte |
| `qwen3:14b` | 16 Go | Bonne |
| `qwen3:30b` | 32 Go | Très bonne |
| `llama3.2:8b` | 8 Go | Alternative |
| `mistral:7b` | 8 Go | Alternative |

---

## Optimisations production

### Gunicorn + Uvicorn multi-workers

```bash
# Installation
pip install gunicorn uvicorn

# Lancement avec workers
gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 50
```

### Configuration de base PostgreSQL

```sql
ALTER SYSTEM SET max_connections = 50;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
```

### Monitoring

```bash
# Vérifier que tout tourne
curl -s https://api.ideas-studio.com/health | jq .
curl -s https://api.ideas-studio.com/health/llm | jq .

# Logs
sudo journalctl -u ideas-studio -f
sudo journalctl -u ollama -f
```

---

## Checklist de déploiement

- [ ] `SECRET_KEY` généré (`openssl rand -hex 48`) et sécurisé
- [ ] `APP_ENV=production`
- [ ] Base de données PostgreSQL configurée
- [ ] Migrations exécutées (`alembic upgrade head`)
- [ ] Provider IA configuré et testé (`GET /health/llm`)
- [ ] Worker démarré et actif
- [ ] Nginx/Caddy configuré avec SSL
- [ ] Frontend déployé sur Vercel
- [ ] Domaine pointant vers l'API
- [ ] Monitoring en place (health endpoint)
- [ ] Backups automatisés de la base de données
- [ ] Logs configurés et accessibles
