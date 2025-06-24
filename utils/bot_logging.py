from discord.ext import commands

LOG_CHANNEL_ID = 1367148946480173116

async def log_to_channel(bot: commands.Bot, message: str):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        try:
            await log_channel.send(f"🛠️ {message}")
            try:
                with open("bot_logs.txt", "a", encoding="utf-8") as f:
                    f.write(f"{message}\n")
            except Exception as file_error:
                print(f"⚠️ No se pudo guardar el log local: {file_error}")
        except Exception as e:
            print(f"❌ No se pudo enviar el log al canal: {e}")
    else:
        print("⚠️ Canal de logs no encontrado.")
