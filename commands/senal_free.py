import discord
import json
import traceback
from typing import Literal
from discord import app_commands
from discord.ext import commands
from views.signal_resolution_view import SignalResolutionView
from utils.bot_logging import log_to_channel
from datetime import datetime
import os
import pytz
from utils.signal_utils import save_signal_log, get_ny_timestamp_iso
from utils.signal_utils import apply_gamma_watermark


FREE_CHANNEL_ID = 1365391408827207832

def setup_free_signal_command(bot: commands.Bot, anon_group: app_commands.Group):
    @anon_group.command(
        name="señal_free",
        description="Enviar una señal de trading FREE."
    )
    @app_commands.describe(
        activo="Nombre del activo",
        target="Precio objetivo",
        direccion="Dirección del trade: LONG o SHORT",
        contrato="Nombre del contrato (opcional)",
        imagen="Imagen adjunta (opcional)",
    )
    async def signal_free(
        interaction: discord.Interaction,
        activo: str,
        target: str,
        direccion: Literal["LONG", "SHORT"],
        contrato: str = None,
        imagen: discord.Attachment = None,
    ):
        try:
            canal = interaction.client.get_channel(FREE_CHANNEL_ID)
            if not canal:
                await interaction.response.send_message("❌ No se pudo obtener el canal FREE.", ephemeral=True)
                return

            permissions = canal.permissions_for(interaction.guild.me)
            if not permissions.send_messages or not permissions.embed_links:
                await interaction.response.send_message("🚫 El bot no tiene permisos para enviar mensajes o embeds en ese canal.", ephemeral=True)
                return

            # Limitar a 1 señal FREE por día por usuario
            tz_ny = pytz.timezone("America/New_York")
            hoy = datetime.now(tz_ny).date()
            user_id = str(interaction.user.id)

            tracker_file = "free_signal_tracker.json"
            tracker = {}
            if os.path.exists(tracker_file):
                with open(tracker_file, "r", encoding="utf-8") as f:
                    try:
                        tracker = json.load(f)
                    except json.JSONDecodeError:
                        tracker = {}

            if tracker.get(user_id) == str(hoy):
                await interaction.response.send_message("❌ Solo puedes enviar 1 señal FREE por día. Intenta nuevamente mañana.", ephemeral=True)
                return

            await interaction.response.defer(thinking=True, ephemeral=True)

            tracker[user_id] = str(hoy)

            if tracker.get("already_sent_note") == str(hoy):
                primera_del_dia = False
            else:
                primera_del_dia = True
                tracker["already_sent_note"] = str(hoy)

            with open(tracker_file, "w", encoding="utf-8") as f:
                json.dump(tracker, f, ensure_ascii=False, indent=2)

            image_file = None
            image_url = None
            if imagen:
                # Descargar y aplicar watermark
                fp = f"tmp_free_{interaction.id}_{imagen.filename}"
                await imagen.save(fp)
                watermarked_fp = f"wm_{fp}"
                apply_gamma_watermark(fp, watermarked_fp, "gamma_logo_watermark.png")
                file = discord.File(watermarked_fp, filename=imagen.filename)
                image_file = file
                image_url = f"attachment://{imagen.filename}"
                os.remove(fp)
                # Se elimina el archivo watermarked_fp después de enviar el mensaje

            embed = discord.Embed(
                title="📢 Señal de Trading (FREE)",
                color=discord.Color.blue(),
                timestamp=datetime.fromisoformat(get_ny_timestamp_iso())
            )
            embed.add_field(name="🔹 Activo", value=f"`{activo.upper()}`", inline=True)
            embed.add_field(name="🎯 Target", value=f"`{target}`", inline=True)
            embed.add_field(name="📈 Dirección", value=f"`{direccion}`", inline=True)
            if contrato:
                embed.add_field(name="📄 Contrato", value=f"`{contrato.upper()}`", inline=True)
            embed.add_field(name="📊 Resultado", value="`Pendiente`", inline=False)
            embed.set_footer(text="Gamma Society • Not financial advice")
            if image_url:
                embed.set_image(url=image_url)

            # Si es la primera señal del día, enviar el mensaje especial
            if primera_del_dia:
                await canal.send("@here Esta es una señal FREE. Accede a señales más detalladas y análisis exclusivos en el canal VIP.")

            # Enviar el embed
            if image_file:
                mensaje = await canal.send(embed=embed, file=image_file)
                # Limpiar archivo temporal
                try:
                    os.remove(image_file.fp.name)
                except Exception:
                    pass
            else:
                mensaje = await canal.send(embed=embed)

            # Añadir botones solo si el autor es admin, owner o tiene rol "Mod"
            member = interaction.user
            if not isinstance(member, discord.Member):
                member = await interaction.guild.fetch_member(interaction.user.id)
            if (
                member.guild_permissions.administrator
                or member.id == interaction.guild.owner_id
                or any(role.name == "Mod" for role in member.roles)
            ):
                await mensaje.edit(view=SignalResolutionView("free", activo, mensaje.id))

            # Registrar en signals_log.json
            log_entry = {
                "tipo_senal": "free",
                "user_id": user_id,
                "activo": activo,
                "target": target,
                "mensaje_id": mensaje.id,
                "canal_id": canal.id,
                "timestamp": get_ny_timestamp_iso(),
                "resultado": "pendiente",
                "direccion": direccion,
            }
            if contrato:
                log_entry["contrato"] = contrato
            if image_url:
                log_entry["imagen"] = imagen.filename

            save_signal_log(log_entry)

            await log_to_channel(
                interaction.client,
                f"📡 Señal FREE enviada por {interaction.user.mention} para **{activo.upper()}** → 🎯 {target} en {canal.mention}"
            )
            await interaction.followup.send("✅ Señal FREE enviada correctamente y registrada en el sistema.", ephemeral=True)

        except Exception as e:
            await log_to_channel(interaction.client, f"❌ Error inesperado en señal FREE:\n```\n{traceback.format_exc()}\n```")
            try:
                await interaction.followup.send(f"❌ Error inesperado: {e}", ephemeral=True)
            except Exception:
                pass