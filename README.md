# 📞 Missed-Call — Secrétariat SMS Automatisé (IA)

**Transformez vos appels manqués en chantiers signés.** Ce service détecte un appel manqué chez un artisan, rejette l'appel (pour éviter les frais de communication), et engage instantanément une conversation par **SMS** avec le client via **OpenAI (GPT-4o-mini)** pour qualifier sa demande.

---

## 🚀 Le Workflow

1. **Appel Entrant** — Le client appelle l'artisan. Si celui-ci ne répond pas, l'appel est transféré au numéro Twilio.
2. **Silent Hangup** — L'API décroche, identifie quel artisan est concerné, envoie un SMS de bienvenue personnalisé et raccroche immédiatement.
3. **Qualification par IA** — Le client répond au SMS. L'IA extrait intelligemment :
   - Le **problème** (ex : fuite d'eau)
   - La **localisation** (ex : Paris 15e)
   - L'**urgence** (Faible, Moyenne, Haute)
4. **Notification Artisan** — Une fois le dossier complet, l'IA envoie un récapitulatif structuré sur le portable personnel de l'artisan.

---

## 🛠 Tech Stack

| Rôle | Technologie |
|---|---|
| Framework | FastAPI (Python 3.10+) |
| IA | OpenAI GPT-4o-mini (Structured Outputs JSON) |
| Téléphonie | Twilio (Voice & Programmable SMS) |
| Base de données | Supabase (PostgreSQL via SQLAlchemy & AsyncPG) |

---

## 📦 Installation rapide

### 1. Créer l'environnement virtuel

```bash
python -m venv venv

# Activation (Windows)
.\venv\Scripts\activate

# Activation (Mac/Linux)
source venv/bin/activate
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Configurer le fichier `.env`

Créez un fichier `.env` à la racine avec ces variables :

```ini
DATABASE_URL=postgresql+asyncpg://postgres:[PASS]@db.[ID].supabase.co:6543/postgres
OPENAI_API_KEY=sk-...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+339...
```

---

## 🏗 Initialisation de la base

Pour créer les tables et injecter ton premier artisan de test :

```bash
python seed_db.py
```

---

## 🚦 Lancement et Webhooks

### 1. Démarrer le serveur local

```bash
uvicorn main:app --reload
```

### 2. Exposer l'URL avec Ngrok

```bash
ngrok http 8000
```

### 3. Configurer la Twilio Console

| Webhook | URL |
|---|---|
| Voice — *A call comes in* | `https://votre-url.ngrok-free.app/welcome/voice/` |
| Messaging — *A message comes in* | `https://votre-url.ngrok-free.app/sms/reply/` |

---

## 📂 Structure du projet

| Fichier | Rôle |
|---|---|
| `main.py` | Logique des webhooks et orchestration IA |
| `models.py` | Schémas de base de données (Artisans, Conversations, Messages) |
| `utils.py` | Formatage des SMS et envoi Twilio |
| `openai_client.py` | Gestion des appels OpenAI avec auto-retry |
| `db.py` | Connexion asynchrone à Supabase |
| `prompts.py` | Intelligence de l'IA (extraction et conversation) |

---

## ⚠️ Notes de maintenance

- **Frais Twilio** : Ce projet utilise le rejet d'appel (`reject(reason='busy')`) pour minimiser les coûts vocaux.
- **Délai de transfert** : Il est recommandé de paramétrer le renvoi d'appel de l'artisan sur **10–15 secondes** pour une réactivité maximale.
- **Sécurité** : Le dossier `venv/` et le fichier `.env` sont exclus du versioning via `.gitignore`.