import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from views.signal_resolution_view import SignalResolutionView
from tasks.resumen_semanal import setup_resumen_semanal_task
from commands.reply import setup_reply_command
from commands.editar_senal import setup_editar_senal_command

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1339009338307510333

# Set up bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True


# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)
bot.GUILD_ID = GUILD_ID

# Import and set up application commands group and commands
from commands.analisis import setup_analisis_command
from commands.mensaje import setup_forward_message_command
from commands.senal_free import setup_free_signal_command
from commands.senal_vip import setup_vip_signal_command

anon_group = discord.app_commands.Group(name="gamma", description="Comandos de Gamma Bot")
from tasks.resumen_semanal import resumen_manual
anon_group.add_command(resumen_manual)

# Working async log_to_channel implementation
async def log_to_channel(bot: commands.Bot, message: str):
    channel = bot.get_channel(1377787534721155202)
    if not channel:
        try:
            channel = await bot.fetch_channel(1377787534721155202)
        except Exception as e:
            print(f"⚠️ Could not fetch log channel: {e}")
            return
    await channel.send(f"🛠️ **Log:** {message}")

setup_analisis_command(bot, anon_group)
setup_forward_message_command(bot, anon_group, log_to_channel)
setup_free_signal_command(bot, anon_group)
setup_vip_signal_command(bot, anon_group)
setup_reply_command(bot)
setup_editar_senal_command(bot, anon_group)
bot.tree.add_command(anon_group, guild=discord.Object(id=GUILD_ID))

# Handle bot ready event
@bot.event
async def on_ready():
    print("📡 Bot is ready and attempting to sync commands...")
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Synced {len(synced)} command(s) to the guild.")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

    setup_resumen_semanal_task(bot)


    try:
        from tasks.rss_monitor import setup_rss_monitor
        setup_rss_monitor(bot)
    except Exception as e:
        print(f"❌ Error cargando rss_monitor: {e}")

    # 🧩 RE-HYDRATE views for pending signals
    try:
        import json
        with open("signals_log.json", "r", encoding="utf-8") as f:
            logs = json.load(f)
        for entry in logs:
            if entry.get("resultado") == "pendiente":
                tipo = entry.get("tipo_senal")
                activo = entry.get("activo")
                msg_id = entry.get("mensaje_id")
                for guild in bot.guilds:
                    for channel in guild.text_channels:
                        try:
                            msg = await channel.fetch_message(msg_id)
                            view = SignalResolutionView(tipo, activo, msg_id)
                            await msg.edit(view=view)
                            bot.add_view(view)
                            break
                        except:
                            continue
    except Exception as e:
        print(f"❌ Error al rehidratar los views: {e}")

# Main entry point
async def main():
    await bot.start(TOKEN)

asyncio.run(main())