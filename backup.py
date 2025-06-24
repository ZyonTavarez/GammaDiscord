import discord
import json
import traceback
import yfinance as yf
import typing
from datetime import datetime, timezone
from typing import Annotated
from discord.ext import commands
from discord import app_commands

# ---- Configuration Placeholders ----
COMMAND_CHANNEL_ID = 1366087757671432284  # Replace with your actual command channel ID
LOG_CHANNEL_ID = 1367148946480173116  # Canal de logs del bot
ALLOWED_ROLES = ["Mod"]
TOKEN = "MTM2NjkzMjkzNzUyNTk1MjYwNA.Gy-HAZ.7GmhNWIkmAseAR3P89FqbPBlG5TW-gol0qWRQQ"  # Replace with your bot token
GUILD_ID = 1339009338307510333  # Replace with your server's guild ID

# ---- Bot definition ----
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
async def log_to_channel(bot: commands.Bot, message: str):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        try:
            await log_channel.send(f"🛠️ **Log:** {message}")
        except Exception as e:
            print(f"❌ No se pudo enviar el log al canal: {e}")
    else:
        print("⚠️ Canal de logs no encontrado.")

anon_group = app_commands.Group(name="gamma", description="Comandos de Gamma Bot")


@anon_group.command(name="analisis", description="Publicar uno o más análisis desde archivos .txt o .md")
@app_commands.describe(
    archivo="Archivo de texto con el análisis",
    canal="Canal donde enviar el análisis"
)
async def analisis(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    archivo: discord.Attachment
):
    if interaction.channel_id != COMMAND_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ Este comando solo puede usarse en <#{COMMAND_CHANNEL_ID}>.", ephemeral=True
        )
        return

    try:
        member = interaction.user
        if not isinstance(member, discord.Member):
            member = await interaction.guild.fetch_member(interaction.user.id)
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"❌ Error capturando el miembro: {e}\n{error_details}")
        await interaction.response.send_message("⚠️ No se pudo verificar tu perfil de miembro correctamente.", ephemeral=True)
        return

    if not member.guild_permissions.administrator and \
       member.id != interaction.guild.owner_id and \
       not any(role.name in ALLOWED_ROLES for role in member.roles):
        await interaction.response.send_message("🚫 No tienes permiso para usar este comando.", ephemeral=True)
        return

    if not archivo.filename.endswith((".txt", ".md")):
        await interaction.response.send_message("❌ Solo se permiten archivos .txt o .md", ephemeral=True)
        return

    try:
        content = await archivo.read()
        decoded = content.decode("utf-8")

        if len(decoded) > 2000:
            await interaction.response.send_message("❌ El contenido excede el límite de 2000 caracteres permitidos por Discord.", ephemeral=True)
            return

        await canal.send(content=decoded)
        await log_to_channel(bot, f"📤 Análisis enviado por {interaction.user.mention} al canal {canal.mention}")
        await interaction.response.send_message("✅ Análisis enviado correctamente.", ephemeral=True)

    except Exception as e:
        await log_to_channel(bot, f"❌ Error capturado: {str(e)}")
        await interaction.response.send_message(f"❌ Error al leer el archivo: {e}", ephemeral=True)

# Nuevo comando: /gamma mensaje
@anon_group.command(name="mensaje", description="Enviar un mensaje anónimo a un canal público.")
@app_commands.describe(
    message="The message you want to send anonymously.",
    destination_channel="Channel where the message should be sent.",
    attachment="Optional file or image to include"
)
async def anon(
    interaction: discord.Interaction,
    message: str,
    destination_channel: discord.TextChannel,
    attachment: discord.Attachment = None
):
    # Check the command is used in the correct channel
    if interaction.channel_id != COMMAND_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ This command can only be used in <#{COMMAND_CHANNEL_ID}>.", ephemeral=True
        )
        return

    try:
        member = interaction.user
        if not isinstance(member, discord.Member):
            member = await interaction.guild.fetch_member(interaction.user.id)
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"❌ Error capturando el miembro: {e}\n{error_details}")
        await interaction.response.send_message("⚠️ No se pudo verificar tu perfil de miembro correctamente.", ephemeral=True)
        return

    if not member.guild_permissions.administrator and \
       member.id != interaction.guild.owner_id and \
       not any(role.name in ALLOWED_ROLES for role in member.roles):
        await interaction.response.send_message(
            "🚫 No tienes permiso para usar este comando.", ephemeral=True
        )
        return

    # Get the target channel
    target_channel = destination_channel
    if not target_channel:
        await interaction.response.send_message("❌ Target channel not found.", ephemeral=True)
        return

    files = [await attachment.to_file()] if attachment else []
    # Send message to the public channel
    await target_channel.send(content=message, files=files, allowed_mentions=discord.AllowedMentions(everyone=True, roles=True))
    await log_to_channel(bot, f"📨 Mensaje anónimo enviado por {interaction.user.mention} al canal {target_channel.mention}")
    # Confirm anonymously
    await interaction.response.send_message("✅ Message sent anonymously.", ephemeral=True)

@anon.error
async def on_error(interaction: discord.Interaction, error: Exception):
    await log_to_channel(bot, f"❌ Error capturado: {str(error)}")
    await interaction.response.send_message(f"❌ Error: {str(error)}", ephemeral=True)



# ---- Reusable FeedbackView ----
class FeedbackView(discord.ui.View):
    def __init__(self, tipo_senal: str, activo: str):
        super().__init__(timeout=None)
        self.tipo_senal = tipo_senal
        self.activo = activo
        self.responded_users = set()

    @discord.ui.button(label="✅ Ejecutada", style=discord.ButtonStyle.success, custom_id="ejecutada")
    async def ejecutada(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.responded_users:
            await interaction.response.send_message("❗ Ya has enviado tu feedback para esta señal.", ephemeral=True)
            return
        self.responded_users.add(interaction.user.id)
        await interaction.response.send_message("👍 ¡Gracias por confirmar que ejecutaste la señal!", ephemeral=True)
        try:
            with open("feedback_log.json", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "user": str(interaction.user),
                    "respuesta": "ejecutada",
                    "tipo_senal": self.tipo_senal,
                    "activo": self.activo,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"❌ Error al registrar feedback ejecutada: {e}")
        # --- Update or create weekly summary log ---
        from collections import defaultdict
        import os
        summary_path = "feedback_summary.json"
        week_key = datetime.now(timezone.utc).strftime("%Y-W%U")
        entry_type = "ejecutada" if button.custom_id == "ejecutada" else "no_ejecutada"
        try:
            if os.path.exists(summary_path):
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary_data = json.load(f)
            else:
                summary_data = {}
            if week_key not in summary_data:
                summary_data[week_key] = {"ejecutada": 0, "no_ejecutada": 0}
            summary_data[week_key][entry_type] += 1
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Error al actualizar resumen semanal: {e}")

    @discord.ui.button(label="❌ No Ejecutada", style=discord.ButtonStyle.danger, custom_id="no_ejecutada")
    async def no_ejecutada(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.responded_users:
            await interaction.response.send_message("❗ Ya has enviado tu feedback para esta señal.", ephemeral=True)
            return
        self.responded_users.add(interaction.user.id)
        await interaction.response.send_message("👀 ¡Gracias por hacérnoslo saber!", ephemeral=True)
        try:
            with open("feedback_log.json", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "user": str(interaction.user),
                    "respuesta": "no ejecutada",
                    "tipo_senal": self.tipo_senal,
                    "activo": self.activo,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"❌ Error al registrar feedback no ejecutada: {e}")
        # --- Update or create weekly summary log ---
        from collections import defaultdict
        import os
        summary_path = "feedback_summary.json"
        week_key = datetime.now(timezone.utc).strftime("%Y-W%U")
        entry_type = "ejecutada" if button.custom_id == "ejecutada" else "no_ejecutada"
        try:
            if os.path.exists(summary_path):
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary_data = json.load(f)
            else:
                summary_data = {}
            if week_key not in summary_data:
                summary_data[week_key] = {"ejecutada": 0, "no_ejecutada": 0}
            summary_data[week_key][entry_type] += 1
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Error al actualizar resumen semanal: {e}")


# Refactored /gamma señal command for dynamic fields and embed
@anon_group.command(name="señal", description="Enviar una señal de trading formateada a un canal.")
@app_commands.describe(
    tipo_senal="Tipo de señal: free/vip",
    tipo_activo="Tipo de activo: ACCIÓN, CALL o PUT",
    activo="Activo subyacente (ej: AAPL, TSLA)",
    cantidad="Cantidad de activos",
    strike="Precio strike (solo para opciones)",
    vencimiento="Vencimiento (solo para opciones VIP)",
    imagen="Imagen del análisis técnico (opcional)",
    target="Target price (obligatorio)",
    stop_loss="Stop loss price (solo VIP)",
    side="Dirección de la operación (solo para ACCIÓN: LONG/SHORT)"
)
@app_commands.choices(
    tipo_senal=[
        app_commands.Choice(name="Free", value="free"),
        app_commands.Choice(name="VIP", value="vip")
    ],
    tipo_activo=[
        app_commands.Choice(name="ACCIÓN", value="ACCION"),
        app_commands.Choice(name="CALL", value="CALL"),
        app_commands.Choice(name="PUT", value="PUT")
    ],
    side=[
        app_commands.Choice(name="LONG", value="long"),
        app_commands.Choice(name="SHORT", value="short")
    ]
)
async def signal(
    interaction: discord.Interaction,
    tipo_senal: app_commands.Choice[str],
    tipo_activo: app_commands.Choice[str],
    activo: str,
    cantidad: int,
    strike: str = None,
    vencimiento: str = None,
    imagen: discord.Attachment = None,
    target: str = None,
    stop_loss: str = None,
    side: app_commands.Choice[str] = None,
):
    # Only allow in the command channel
    if interaction.channel_id != COMMAND_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ This command can only be used in <#{COMMAND_CHANNEL_ID}>.", ephemeral=True
        )
        return

    try:
        member = interaction.user
        if not isinstance(member, discord.Member):
            member = await interaction.guild.fetch_member(interaction.user.id)
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"❌ Error capturando el miembro: {e}\n{error_details}")
        await interaction.response.send_message("⚠️ No se pudo verificar tu perfil de miembro correctamente.", ephemeral=True)
        return

    if not member.guild_permissions.administrator and \
       member.id != interaction.guild.owner_id and \
       not any(role.name in ALLOWED_ROLES for role in member.roles):
        await interaction.response.send_message(
            "🚫 No tienes permiso para usar este comando.", ephemeral=True
        )
        return

    is_vip = tipo_senal.value == "vip"
    is_accion = tipo_activo.value == "ACCION"
    is_opcion = tipo_activo.value in ["CALL", "PUT"]

    # --- Dynamic validation logic ---
    validation_error = None
    # ACCION (stock)
    if is_accion:
        if side is None:
            validation_error = "❌ Para señales de ACCIÓN, debes especificar la dirección ('side'): LONG o SHORT."
        elif tipo_senal.value == "free":
            # Only require activo, cantidad, target, and side. Ignore strike, vencimiento, stop_loss.
            if not activo or not cantidad or not target:
                validation_error = "❌ Para señales FREE de ACCIÓN, 'activo', 'cantidad' y 'target' son obligatorios."
        else:  # VIP
            if not activo or not cantidad or not target or not stop_loss:
                validation_error = "❌ Para señales VIP de ACCIÓN, 'activo', 'cantidad', 'target' y 'stop_loss' son obligatorios."
    # Opciones (CALL/PUT)
    elif is_opcion:
        if is_vip:
            if not strike or not vencimiento or not target or not stop_loss:
                validation_error = "❌ Para señales VIP de opciones, 'strike', 'vencimiento', 'target' y 'stop_loss' son obligatorios."
        else:  # FREE
            if not target:
                validation_error = "❌ Para señales FREE de opciones, 'target' es obligatorio."
    else:
        validation_error = "❌ Tipo de activo no reconocido."

    if validation_error:
        await interaction.response.send_message(validation_error, ephemeral=True)
        return

    # Extra validation for FREE signals: no Stop Loss, Vencimiento, Strike, Imagen
    if tipo_senal.value == "free":
        if stop_loss or strike or vencimiento or imagen:
            await interaction.response.send_message(
                "❌ Las señales FREE no pueden incluir Stop Loss, Vencimiento, Strike ni Imagen.\n\n"
                "🧠 Las señales gratuitas son limitadas por diseño.\n"
                "Si deseas compartir setups completos y estrategias detalladas, por favor utiliza la zona VIP.",
                ephemeral=True
            )
            return

    # Determine channel based on tipo_senal
    if is_vip:
        canal_id = 1351311086984626308
    else:
        canal_id = 1365391408827207832
    canal = interaction.guild.get_channel(canal_id)
    if canal is None:
        await interaction.response.send_message("❌ No se pudo encontrar el canal de destino.", ephemeral=True)
        return

    # --- Dynamic embed creation ---
    embed = discord.Embed(
        title="📊 Señal de Trading",
        color=discord.Color.gold() if is_vip else discord.Color.blue()
    )
    # ACCION + FREE: Only show activo, cantidad, target, side
    if is_accion and not is_vip:
        embed.add_field(name="📌 Activo", value=activo, inline=True)
        embed.add_field(name="📈 Activo(s)", value=tipo_activo.value, inline=True)
        embed.add_field(name="🎯 Target", value=target if target else "N/A", inline=True)
        embed.add_field(name="📦 Cantidad", value=str(cantidad) if cantidad else "N/A", inline=True)
        embed.add_field(name="📊 Dirección", value=side.name.upper(), inline=True)
        # Do NOT include strike, vencimiento, stop_loss
    # ACCION + VIP
    elif is_accion and is_vip:
        embed.add_field(name="📌 Activo", value=activo, inline=True)
        embed.add_field(name="📈 Activo(s)", value=tipo_activo.value, inline=True)
        embed.add_field(name="🎯 Target", value=target if target else "N/A", inline=True)
        embed.add_field(name="📦 Cantidad", value=str(cantidad) if cantidad else "N/A", inline=True)
        embed.add_field(name="📊 Dirección", value=side.name.upper(), inline=True)
        embed.add_field(name="🛑 Stop Loss", value=stop_loss if stop_loss else "N/A", inline=True)
    # Opciones
    elif is_opcion:
        embed.add_field(name="📌 Activo", value=activo, inline=True)
        embed.add_field(name="📈 Activo(s)", value=tipo_activo.value, inline=True)
        embed.add_field(name="🎯 Target", value=target if target else "N/A", inline=True)
        embed.add_field(name="📦 Cantidad", value=str(cantidad) if cantidad else "N/A", inline=True)
        if is_vip:
            embed.add_field(name="📅 Vencimiento", value=vencimiento if vencimiento else "N/A", inline=True)
            embed.add_field(name="💥 Strike", value=strike if strike else "N/A", inline=True)
            embed.add_field(name="🛑 Stop Loss", value=stop_loss if stop_loss else "N/A", inline=True)
    else:
        # fallback
        embed.add_field(name="📌 Activo", value=activo, inline=True)
        embed.add_field(name="📈 Activo(s)", value=tipo_activo.value, inline=True)
        embed.add_field(name="🎯 Target", value=target if target else "N/A", inline=True)
        embed.add_field(name="📦 Cantidad", value=str(cantidad) if cantidad else "N/A", inline=True)

    if imagen:
        embed.set_image(url=imagen.url)

    embed.set_footer(text="🔒 Señal VIP" if is_vip else "📢 Señal Gratuita")
    embed.timestamp = interaction.created_at

    # FREE signal per-user-per-day limiter
    from datetime import date
    user_today_key = f"{interaction.user.id}_{date.today().isoformat()}"
    try:
        with open("signals_log.json", "r", encoding="utf-8") as f:
            existing_logs = [json.loads(line) for line in f.readlines()]
        for entry in existing_logs:
            if (
                entry.get("tipo_senal") == "free" and
                entry.get("autor") == str(interaction.user) and
                entry.get("fecha") == date.today().isoformat()
            ):
                await interaction.response.send_message(
                    "⚠️ **¡Límite alcanzado!**\nYa enviaste tu señal FREE de hoy. Puedes volver a enviar otra después de las 🕛 12:00 AM.",
                    ephemeral=True
                )
                return
    except FileNotFoundError:
        pass
    except Exception as e:
        await log_to_channel(bot, f"❌ Error capturado: {str(e)}")
        print(f"❌ Error al verificar duplicados: {e}")

    # --- VIP Disclaimer message logic (FREE signals only, once per day) ---
    if not is_vip:
        import os
        from datetime import date
        disclaimer_path = "vip_disclaimer_tracker.json"
        disclaimer_today = date.today().isoformat()
        send_disclaimer = True
        try:
            if os.path.exists(disclaimer_path):
                with open(disclaimer_path, "r", encoding="utf-8") as f:
                    tracker = json.load(f)
                if tracker.get("last_sent_date") == disclaimer_today:
                    send_disclaimer = False
            else:
                tracker = {}
        except Exception as e:
            print(f"⚠️ Error leyendo tracker de disclaimer VIP: {e}")

        vip_disclaimer_markdown = (
            "> 🔒 **¿Quieres señales premium?**\n"
            "> \n"
            "> Accede a **VIP** para:\n"
            "> • 🛑 Stop Loss claros  \n"
            "> • 📅 Fechas de vencimiento  \n"
            "> • 🧠 Análisis visual  \n"
            "> • 📈 Sin límites diarios  \n"
            "> \n"
            "> 🔗 Mejora tu operativa con setups avanzados y contexto real.\n\n"
        )
        if send_disclaimer:
            embed.description = vip_disclaimer_markdown + (embed.description or "")
            try:
                with open(disclaimer_path, "w", encoding="utf-8") as f:
                    json.dump({"last_sent_date": disclaimer_today}, f)
            except Exception as e:
                print(f"⚠️ Error actualizando tracker de disclaimer VIP: {e}")

    # Send embed and feedback buttons together
    await canal.send(embed=embed, view=FeedbackView(tipo_senal.value, activo))
    await log_to_channel(bot, f"📡 Señal '{tipo_senal.value.upper()}' enviada por {interaction.user.mention} para {activo}")
    await interaction.response.send_message("✅ Señal enviada correctamente.", ephemeral=True)

    # --- Log entry with dynamic fields ---
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "autor": str(interaction.user),
        "tipo_senal": tipo_senal.value,
        "tipo_activo": tipo_activo.value,
        "activo": activo,
        "cantidad": cantidad,
        "canal": str(canal.id),
        "resultado": "pendiente"
    }
    # For ACCION + FREE: only log side, target, no stop_loss, no strike, no vencimiento
    if is_accion and not is_vip:
        log_entry["side"] = side.value
        log_entry["target"] = target
    # For ACCION + VIP: log side, target, stop_loss
    elif is_accion and is_vip:
        log_entry["side"] = side.value
        log_entry["target"] = target
        log_entry["stop_loss"] = stop_loss
    # For opciones
    elif is_opcion:
        if is_vip:
            log_entry["strike"] = strike
            log_entry["vencimiento"] = vencimiento
            log_entry["stop_loss"] = stop_loss
            log_entry["target"] = target
        else:
            log_entry["target"] = target
    else:
        log_entry["target"] = target
    # Add current date to log entry
    log_entry["fecha"] = date.today().isoformat()
    try:
        with open("signals_log.json", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        await log_to_channel(bot, f"❌ Error capturado: {str(e)}")
        print(f"❌ Error writing to log file: {e}")


# ---- REGLAS COMMAND ----
@anon_group.command(name="mostrar_reglas", description="Publicar las reglas oficiales del servidor.")
async def reglas(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 Reglas de la Comunidad",
        color=discord.Color.green()
    )
    embed.description = (
        "**1. 🫱‍🫲 Respeto absoluto**\n"
        "• No insultos ni provocaciones.\n"
        "• Respeta a todos: comunidad y staff.\n\n"
        "**2. 🚫 Cero discriminación**\n"
        "• Racismo, sexismo, homofobia = ban directo.\n\n"
        "**3. ⚠️ Contenido prohibido**\n"
        "• Nada de NSFW, gore ni violencia gráfica.\n\n"
        "**4. 📈 Enfoque en trading**\n"
        "• Nada de política ni temas fuera del enfoque del canal.\n\n"
        "**5. 🔒 Seguridad y privacidad**\n"
        "• No compartas datos personales ni contraseñas.\n\n"
        "**6. 📢 Anti spam**\n"
        "• No promociones sin permiso. No spam.\n\n"
        "**7. 🧭 Orden de canales**\n"
        "• Usa los canales correctos. No flood.\n\n"
        "**8. 🧑‍⚖️ Autoridad del staff**\n"
        "• Las decisiones del staff son finales.\n\n"
        "**9. 💼 Profesionalismo**\n"
        "• Publica análisis o señales de forma seria.\n\n"
        "✅ Al usar este servidor, aceptas estas normas."
    )
    embed.set_image(url="https://www.onelegal.com/wp-content/uploads/2024/06/how-does-a-california-lawyer-become-a-judge.jpg")
    reglas_channel = interaction.guild.get_channel(1339009338307510335)
    if reglas_channel:
        sent_msg = await reglas_channel.send(embed=embed)
        await sent_msg.pin()
        await interaction.response.send_message("✅ Reglas enviadas y fijadas en el canal configurado.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ No se encontró el canal de reglas.", ephemeral=True)

@signal.autocomplete("activo")
async def activo_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    suggestions = []
    try:
        # Limit suggestions to common tickers for performance
        tickers = ["AAPL", "TSLA", "SPY", "NVDA", "AMZN", "GOOGL", "MSFT", "QQQ", "TQQQ", "SPX"]
        filtered = [t for t in tickers if current.upper() in t]
        suggestions = [app_commands.Choice(name=t, value=t) for t in filtered[:10]]
    except Exception:
        pass
    return suggestions

bot.tree.add_command(anon_group)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        bot.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Synced {len(synced)} command(s) to the guild.")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

bot.run(TOKEN)