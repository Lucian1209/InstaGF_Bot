
# MolyBot – Instagram AI Girlfriend Bot

Moly is a charming virtual girlfriend from Thailand. She flirts, chats, and replies to DMs and comments like a real person.  
This bot uses `instagrapi` to interact with Instagram and OpenRouter (free HuggingFace-compatible LLMs) for responses.

---

## Features

- Replies to Instagram DMs and comments with playful and emotional tone
- Adds natural delays before responding
- Filters inappropriate messages
- Suggests checking links in bio (Patreon, Telegram)
- Respects Instagram limits and behavior
- Authorization via `session.json`

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/molybot.git
cd molybot
```

### 2. Create `.env` file

```bash
cp .env.example .env
```

Fill in the OpenRouter key:

```
OPENROUTER_KEY=your_key_here
```

### 3. Install Dependencies

Create virtual env (optional):

```bash
python -m venv venv
source venv/bin/activate
```

Install:

```bash
pip install -r requirements.txt
```

### 4. Add your Instagram `session.json`

Place your working `session.json` file in the root directory.

---

## Run the bot

```bash
python bot.py
```

---

## Deploy on Railway

1. Push to GitHub
2. Go to [https://railway.app](https://railway.app)
3. Deploy project from your GitHub repo
4. Railway reads `railway.json` and starts bot

---

## Notes

- No adult content. Moly is safe and romantic.
- She dislikes apples and overly pushy men.
- Add OpenRouter-compatible models via the `.env`.

---
