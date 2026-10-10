# MirrorLeech Bot

A lightweight Telegram bot inspired by the mirror/leech workflow: it accepts a URL, downloads the file locally, and sends it back to the Telegram chat.

It is intentionally simpler than the large production-grade downloader bot in the reference repository, but it gives you a working foundation you can extend with:

- inline buttons
- queue management
- Google Drive integration
- Rclone support
- torrent support
- user and admin permissions
- database-backed tracking

## Features

- `/start` - welcome message
- `/help` - command list
- `/mirror <url>` - download a direct file URL and send it back
- `/leech <url>` - alias for `/mirror`
- `/status` - basic bot health info
- automatic URL detection in plain text messages

## Stack

- Python 3.12+
- python-telegram-bot 21.x
- requests
- yt-dlp

## Quick start

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and set your Telegram bot token:

```bash
TELEGRAM_BOT_TOKEN=your_actual_token_here
ALLOWED_USER_IDS=123456789,987654321
DOWNLOAD_DIR=/tmp/mirrorbot
```

3. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Run the bot:

```bash
python bot.py
```

## Docker

```bash
docker build -t mirrorleech-bot .
docker run --rm -it --env-file .env mirrorleech-bot
```

## Example usage

```
/mirror https://example.com/file.zip
/leech https://youtu.be/dQw4w9WgXcQ
```

The bot will download the target to the local temp directory and send it back as a Telegram document.

## Next upgrades to build

- add queue and task status
- support torrent files and magnet links
- support Google Drive upload via API
- support Rclone cloud destinations
- add admin-only commands
- add MongoDB persistence
- add inline menu buttons

## Important note

This bot is a compact foundation, not the full mirror-leech platform from the reference repository. For production use, you will likely need additional storage, queueing, user auth, cloud integrations, and background workers.
