import asyncio
import os
import re
import uuid
from email.message import Message
from pathlib import Path
from urllib.parse import urlparse

import requests
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_IDS = {
    int(user_id.strip())
    for user_id in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if user_id.strip()
}
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "/tmp/mirrorbot"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
TASK_LOG = []


async def auth_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not ALLOWED_USER_IDS:
        return True

    if update.effective_user is None:
        return False

    if update.effective_user.id not in ALLOWED_USER_IDS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return False

    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update, context):
        return

    await update.message.reply_text(
        "Welcome to MirrorLeech Bot\n\n"
        "Commands:\n"
        "• /mirror <url> - Download a file and send it back\n"
        "• /leech <url> - Alias for /mirror\n"
        "• /status - Check bot status\n"
        "• /help - Show commands\n"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update, context):
        return

    await start(update, context)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update, context):
        return

    message = (
        "✅ Bot is running\n"
        f"Download directory: {DOWNLOAD_DIR}\n"
        f"Tasks completed: {len(TASK_LOG)}"
    )
    await update.message.reply_text(message)


def sanitize_filename(raw_name: str) -> str:
    name = raw_name.strip()
    if not name:
        return "download.bin"
    name = os.path.basename(name)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    if not name or name in {".", ".."}:
        return "download.bin"
    return name


def parse_content_disposition_filename(headers: dict) -> str | None:
    disposition = headers.get("Content-Disposition")
    if not disposition:
        return None

    message = Message()
    message["content-disposition"] = disposition
    filename = message.get_filename()
    return sanitize_filename(filename) if filename else None


def detect_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    if not name:
        return "download.bin"
    return sanitize_filename(name)


def download_with_requests(url: str) -> str:
    response = requests.get(url, timeout=60, stream=True)
    response.raise_for_status()

    filename = parse_content_disposition_filename(dict(response.headers)) or detect_filename_from_url(url)
    target = DOWNLOAD_DIR / f"{uuid.uuid4().hex}_{filename}"

    with open(target, "wb") as file_handle:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file_handle.write(chunk)

    return str(target)


def download_with_ytdlp(url: str) -> str:
    output_path = DOWNLOAD_DIR / f"{uuid.uuid4().hex}_%(title)s.%(ext)s"
    ydl_opts = {
        "outtmpl": str(output_path),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "download") if isinstance(info, dict) else "download"
        final_name = sanitize_filename(f"{title}.mp4")
        generated = list(DOWNLOAD_DIR.glob(f"{uuid.uuid4().hex}_*"))
        if generated:
            return str(generated[0])
        return str(DOWNLOAD_DIR / final_name)


def is_supported_media_url(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    return "youtube.com" in domain or "youtu.be" in domain


def download_file(url: str) -> str:
    if is_supported_media_url(url):
        return download_with_ytdlp(url)
    return download_with_requests(url)


async def perform_mirror(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    if not url:
        await update.message.reply_text("❌ Please provide a URL. Example: /mirror https://example.com/file.zip")
        return

    reply = await update.message.reply_text(f"📥 Starting download for:\n{url}\nPlease wait...")

    try:
        task_id = str(uuid.uuid4())[:8]
        TASK_LOG.append({"task_id": task_id, "url": url, "status": "downloading"})

        file_path = await asyncio.to_thread(download_file, url)
        TASK_LOG[-1]["status"] = "complete"

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Downloaded file not found: {file_path}")

        await reply.edit_text(f"✅ Download complete. Sending file...\nTask ID: {task_id}")
        await update.message.reply_document(document=file_path)
    except Exception as exc:
        TASK_LOG[-1]["status"] = "failed"
        await reply.edit_text(f"❌ Mirror failed:\n{exc}")


async def mirror(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update, context):
        return

    url = " ".join(context.args).strip()
    if not url:
        text = update.message.text or ""
        match = re.search(r"https?://\S+", text)
        if match:
            url = match.group(0)

    await perform_mirror(update, context, url)


async def leech(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await mirror(update, context)


async def handle_plain_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_check(update, context):
        return

    text = update.message.text or ""
    if not text:
        return

    match = re.search(r"https?://\S+", text)
    if not match:
        return

    await perform_mirror(update, context, match.group(0))


async def main() -> None:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Add it to your environment or .env file.")

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("mirror", mirror))
    application.add_handler(CommandHandler("leech", leech))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plain_url))

    print("Bot started successfully...")
    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
