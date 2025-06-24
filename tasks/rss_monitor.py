import feedparser
import asyncio
from discord.ext import tasks
from datetime import datetime
import os
import json
import dateutil.parser as parser
from utils.signal_utils import get_ny_timestamp_iso

ALERT_TRACKER_FILE = "rss_alert_tracker.json"
alert_tracker = {}

if os.path.exists(ALERT_TRACKER_FILE):
    try:
        with open(ALERT_TRACKER_FILE, "r", encoding="utf-8") as f:
            alert_tracker = json.load(f)
    except json.JSONDecodeError:
        alert_tracker = {}

FEED_URL = "https://www.financialjuice.com/feed.ashx?xy=rss"
CHECK_INTERVAL = 60  # en segundos


def setup_rss_monitor(bot):
    seen_guids = set()
    KEYWORDS = {
        "trump to speak": "@everyone 📢 Trump hablará pronto.",
        "president trump remarks": "@everyone 📢 Trump está dando declaraciones.",
        "powell to speak": "@everyone 🧠 Jerome Powell hablará pronto.",
        "fed chair remarks": "@everyone 🧠 Atención: el presidente de la Fed está hablando.",
    }

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def rss_check():
        try:
            feed = feedparser.parse(FEED_URL)
            for entry in feed.entries:
                guid = entry.get("id", entry.get("link"))
                if not guid or guid in seen_guids:
                    continue
                seen_guids.add(guid)

                now = datetime.fromisoformat(get_ny_timestamp_iso())
                title = entry.title.lower()

                if "🔴" not in entry.title:
                    continue

                # Revisa si algún keyword relevante coincide y no es spam
                for keyword, alert_msg in KEYWORDS.items():
                    if keyword in title:
                        last_entry = alert_tracker.get(keyword, {})
                        last_time = parser.parse(last_entry.get("timestamp", "1970-01-01T00:00:00"))

                        if (now - last_time).total_seconds() < 1800:
                            break  # omitir si está dentro del margen

                        # Aquí se enviaría el mensaje si pasa validación

                        # Registrar alerta enviada
                        alert_tracker[keyword] = {"timestamp": now.isoformat()}
                        with open(ALERT_TRACKER_FILE, "w", encoding="utf-8") as f:
                            json.dump(alert_tracker, f, indent=2)
                        break  # No continuar revisando más keywords para esta entrada
        except Exception as e:
            print(f"❌ Error al leer RSS feed: {e}")

    @rss_check.before_loop
    async def before():
        await bot.wait_until_ready()

    rss_check.start()
