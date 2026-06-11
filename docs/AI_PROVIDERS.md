# Guide des providers IA — Ideas Studio

Ideas Studio utilise une architecture unifiée basée sur l'API OpenAI-compatible pour tous les providers de génération de texte. Cela permet de supporter une large gamme de services avec un socle technique commun.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Application                         │
│  idea_engine.py, writing_engine.py, orchestrator...   │
└────────────────────┬─────────────────────────────────┘
                     │ get_llm_provider()
┌────────────────────▼─────────────────────────────────┐
│              LLMProvider (classe abstraite)            │
│  generate_text(prompt, system, temperature) → str     │
│  generate_json(prompt, schema_hint) → dict            │
│  is_available() → bool                                │
└────────────────────┬─────────────────────────────────┘
                     │
    ┌────────────────┼────────────────────┬──────────┐
    ▼                ▼                    ▼          ▼
┌──────────┐  ┌──────────┐  ┌──────────────────┐  ┌────┐
│ OpenAI   │  │ Ollama   │  │ OpenRouter       │  │Mock│
│ (Native) │  │ (Local)  │  │ (OpenAI-compat.) │  │    │
└──────────┘  └──────────┘  └──────────────────┘  └────┘
                              ┌──────────────┐
                              │  Gemini      │
                              │ (OpenAI-c.)  │
                              └──────────────┘
```

### Principe de fonctionnement

1. **`LLMProvider`** — Classe de base abstraite définissant l'interface commune
2. **`OpenAILLMProvider`** — Implémentation OpenAI native avec support des retries et timeout
3. **`OpenRouterLLMProvider`** — Hérite d'OpenAI, ajoute les modèles spécialisés (writer, planner, fallback)
4. **`GeminiLLMProvider`** — Hérite d'OpenAI, utilise l'endpoint OpenAI-compatible de Google
5. **`OllamaLLMProvider`** — Implémentation spécifique via l'API chat d'Ollama
6. **`MockLLMProvider`** — Provider factice pour développement et tests

### Sélection automatique (mode `auto`)

Quand `DEFAULT_LLM_PROVIDER=auto`, le système essaie les providers dans cet ordre :

1. **OpenRouter** — Si `OPENROUTER_API_KEY` est configurée
2. **Ollama** — Si Ollama est accessible sur `OLLAMA_BASE_URL`
3. **OpenAI** — Si `OPENAI_API_KEY` est configurée

Le premier provider disponible est utilisé. Si aucun n'est disponible, une erreur `ProviderUnavailableError` est levée.

---

## Liste des providers et capacités

### Providers supportés nativement

| Provider | Clé .env | Type | Coût | Modèle par défaut |
|---|---|---|---|---|
| **Ollama** | `DEFAULT_LLM_PROVIDER=ollama` | Local | Gratuit | `qwen3:14b` |
| **Google Gemini** | `DEFAULT_LLM_PROVIDER=gemini` | Cloud | Gratuit (quota) | `gemini-2.5-flash` |
| **OpenRouter** | `DEFAULT_LLM_PROVIDER=openrouter` | Cloud | Gratuit/payant | `deepseek/deepseek-v4-flash:free` |
| **OpenAI** | `DEFAULT_LLM_PROVIDER=openai` | Cloud | Payant | `gpt-4o-mini` |
| **Mock** | `DEFAULT_LLM_PROVIDER=mock` | Local | Gratuit | `template` |

### Providers via CMS (configuration en base de données)

| Provider | Type | Modèle par défaut |
|---|---|---|
| **Anthropic** | Cloud | `claude-3-haiku-20240307` |
| **Mistral AI** | Cloud | `mistral-small-latest` |
| **Custom** | Variable | Libre |

---

## Google Gemini

### Obtenir une clé API

1. Allez sur [AI Studio Google](https://aistudio.google.com/apikey)
2. Connectez-vous avec votre compte Google
3. Cliquez sur **Create API Key**
4. Copiez la clé (commence par `AIza...`)

### Configuration

```bash
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_TIMEOUT_SECONDS=180
```

### Modèles disponibles

| Modèle | Description | Limites |
|---|---|---|
| `gemini-2.5-flash` | Rapide, bon rapport qualité/vitesse | 1M tokens |
| `gemini-2.5-pro` | Haute qualité, plus lent | 1M tokens |
| `gemini-1.5-flash` | Ancien, toujours disponible | 1M tokens |
| `gemini-1.5-pro` | Ancien, haute qualité | 1M tokens |

### Particularités

- Utilise l'endpoint OpenAI-compatible de Google (pas le SDK Google)
- Quota gratuit généreux (60 requêtes/minute)
- Timeout configurable (180 secondes par défaut)
- Fonctionne sans carte bancaire

### Test

```bash
curl -s https://api.ideas-studio.com/health/llm | jq .
```

Réponse attendue :
```json
{
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "configured": true,
  "available": true
}
```

---

## Ollama

Ollama permet d'exécuter des modèles de langage localement, sans dépendance cloud ni abonnement.

### Installation

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows
# Téléchargez depuis https://ollama.com/download
```

### Télécharger un modèle

```bash
# Recommandé (16 Go RAM)
ollama pull qwen3:14b

# Alternative (8 Go RAM)
ollama pull qwen3:8b

# Autres modèles compatibles
ollama pull llama3.2:8b
ollama pull mistral:7b
ollama pull qwen3:30b  # 32 Go RAM recommandé
```

### Configuration

```bash
DEFAULT_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:14b
OLLAMA_FALLBACK_MODEL=qwen3:8b
OLLAMA_TIMEOUT_SECONDS=180
```

### Vérification

```bash
# Vérifier qu'Ollama tourne
ollama list

# Tester l'API
curl http://127.0.0.1:11434/api/tags

# Tester le modèle
curl http://127.0.0.1:11434/api/chat \
  -d '{"model":"qwen3:14b","messages":[{"role":"user","content":"Bonjour"}],"stream":false}'
```

### Dépannage

**Erreur : `Ollama local indisponible`**
```bash
# Vérifier que le service tourne
sudo systemctl status ollama

# Voir les logs
sudo journalctl -u ollama -f

# Redémarrer
sudo systemctl restart ollama
```

**Erreur : `Modèle non trouvé`**
```bash
ollama pull qwen3:14b
```

**Erreur : `Timeout`**
- Augmentez `OLLAMA_TIMEOUT_SECONDS` (défaut: 180)
- Vérifiez les ressources système (RAM, CPU)
- Passez à un modèle plus petit (`qwen3:8b`)

### Performance

| Modèle | RAM | Génération (800 mots) | Qualité |
|---|---|---|---|
| `qwen3:8b` | 8 Go | ~45s | Correcte |
| `qwen3:14b` | 16 Go | ~60s | Bonne |
| `qwen3:30b` | 32 Go | ~90s | Très bonne |

---

## OpenAI

### Obtenir une clé API

1. Créez un compte sur [OpenAI](https://platform.openai.com)
2. Allez dans **API Keys**
3. Créez une nouvelle clé
4. Ajoutez un crédit de paiement

### Configuration

```bash
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

### Modèles recommandés

| Modèle | Usage | Coût (1M tokens input) |
|---|---|---|
| `gpt-4o-mini` | Génération rapide | $0.15 |
| `gpt-4o` | Haute qualité | $2.50 |
| `o3-mini` | Raisonnement | $1.10 |

---

## OpenRouter

OpenRouter donne accès à de nombreux modèles via une API unique, dont des modèles gratuits.

### Obtenir une clé API

1. Créez un compte sur [OpenRouter](https://openrouter.ai)
2. Allez dans **Keys**
3. Créez une nouvelle clé

### Configuration

```bash
DEFAULT_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=deepseek/deepseek-v4-flash:free
OPENROUTER_WRITER_MODEL=deepseek/deepseek-v4-flash:free
OPENROUTER_PLANNER_MODEL=openai/gpt-oss-120b:free
OPENROUTER_FALLBACK_MODEL=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### Modèles gratuits disponibles

| Modèle | Qualité | Limite |
|---|---|---|
| `deepseek/deepseek-v4-flash:free` | Bonne | 20 req/min |
| `openai/gpt-oss-120b:free` | Bonne | Variable |
| `openrouter/free` | (fallback) | Variable |

### Modèles spécialisés

OpenRouter permet de configurer des modèles différents pour chaque étape :
- **`OPENROUTER_MODEL`** — Génération principale
- **`OPENROUTER_WRITER_MODEL`** — Rédaction d'article
- **`OPENROUTER_PLANNER_MODEL`** — Planification et stratégie
- **`OPENROUTER_FALLBACK_MODEL`** — Fallback si le modèle principal échoue

---

## Configuration via le CMS

### Interface Providers

L'interface `/settings/ai-providers` permet de gérer les providers sans modifier les variables d'environnement.

**Endpoints :**
- `GET /settings/ai-providers` — Lister les providers configurés
- `POST /settings/ai-providers` — Ajouter un provider
- `PATCH /settings/ai-providers/{id}` — Modifier
- `DELETE /settings/ai-providers/{id}` — Supprimer
- `POST /settings/ai-providers/{id}/test` — Tester la connexion
- `GET /settings/ai-providers/default` — Provider par défaut

### Masquage des clés

Les clés API sont stockées chiffrées en base de données et partiellement masquées dans l'interface :
```
sk-proj-...AbCd
```

### Ordre de priorité

1. **Providers configurés en base** — Si un provider a `is_default=True`, il est utilisé
2. **Variables d'environnement** — Fallback si aucun provider par défaut en base
3. **Mode auto** — Sélection automatique (OpenRouter > Ollama > OpenAI)

---

## Test des providers

### Via l'API Health

```bash
# Test du provider par défaut
curl -s https://api.ideas-studio.com/health/llm | jq .

# Test avec un provider spécifique (via DEFAULT_LLM_PROVIDER)
```

### Via l'interface CMS

```
POST /settings/ai-providers/{provider_id}/test
```

Retourne :
```json
{
  "provider": "gemini",
  "status": "connected",
  "message": null,
  "model": "gemini-2.5-flash"
}
```

### En cas d'erreur

Les erreurs courantes retournées :
- `Aucune clé API configurée` — La clé est absente
- `API a retourné une erreur (clé invalide ?)` — La clé est invalide
- `Ollama local indisponible` — Ollama ne répond pas
- `Timeout` — Le modèle est trop lent

---

## Mode Mock

Le mode Mock est conçu pour le développement et les tests. Il ne nécessite aucune configuration.

```bash
DEFAULT_LLM_PROVIDER=mock
```

**Comportement :**
- `generate_text()` retourne un texte statique
- `generate_json()` retourne un objet vide `{}`
- `is_available()` retourne toujours `true`
- Toutes les idées et articles générés en mode mock sont marqués comme tels

**Limitations :**
- Le contenu généré n'est pas publiable
- Les articles mock sont détectés et bloqués à la publication
- Utilisation déconseillée en production

---

## Dépannage

### Problèmes courants

| Problème | Cause probable | Solution |
|---|---|---|
| `Aucun provider IA réel disponible` | Aucun provider configuré | Configurez au moins un provider (Ollama, Gemini, OpenRouter) |
| `Ollama local indisponible` | Ollama ne tourne pas | `ollama serve` ou `sudo systemctl start ollama` |
| `Modèle non trouvé` | Modèle non téléchargé | `ollama pull qwen3:14b` |
| `Timeout` | Modèle trop lent | Réduisez le temps d'execution ou passez à un modèle plus petit |
| `Clé API invalide` | Clé erronée ou expirée | Vérifiez votre clé API |
| `Provider non supporté` | Provider inconnu | Vérifiez la liste des providers supportés |
| `429 Too Many Requests` | Quota dépassé | Attendez ou passez à un autre provider |

### Vérification rapide

```bash
# Test Ollama
curl http://127.0.0.1:11434/api/tags

# Test Gemini
curl -H "Authorization: Bearer AIza..." \
  https://generativelanguage.googleapis.com/v1beta/models

# Test OpenAI
curl -H "Authorization: Bearer sk-..." \
  https://api.openai.com/v1/models

# Test OpenRouter
curl -H "Authorization: Bearer sk-or-..." \
  https://openrouter.ai/api/v1/models
```

### Logs

Les logs du backend contiennent des informations détaillées sur les providers :

```bash
# Voir les logs de génération
sudo journalctl -u ideas-studio -f | grep -E "provider|llm|generation"

# Dans les logs applicatifs
2026-01-15T10:00:00 [INFO] app.services.idea_engine: generate_idea provider=gemini model=gemini-2.5-flash is_mock=False project=abc123
```

---

## Bonnes pratiques

### Production

1. **Utilisez au moins 2 providers** — Configurez un provider principal et un fallback
2. **Évitez le mode mock** — Uniquement pour le développement
3. **Surveillez les quotas** — Gemini et OpenRouter ont des limites gratuites
4. **Préférez `auto`** — Laissez le système choisir le meilleur provider disponible
5. **Testez avant d'utiliser** — Vérifiez le health endpoint après configuration

### Développement

1. **Utilisez Ollama** — Gratuit, fonctionne hors-ligne
2. **Utilisez le mode mock** — Pour les tests automatisés
3. **Configurez `DEFAULT_LLM_PROVIDER=mock`** dans les environnements CI

### Sécurité

1. **Stockez les clés API dans les variables d'environnement**, pas dans le code
2. **Utilisez le gestionnaire de providers du CMS** pour une gestion centralisée
3. **Les clés sont chiffrées en base de données**
4. **Ne partagez jamais vos clés API**
5. **Utilisez des clés dédiées** plutôt que des clés root/compte principal
