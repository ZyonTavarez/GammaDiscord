import discord
from discord.ext import commands
import json
import traceback
from typing import Literal
from discord import app_commands
from views.signal_resolution_view import SignalResolutionView
from utils.bot_logging import log_to_channel
import os
from utils.signal_utils import save_signal_log, get_ny_timestamp_iso, apply_gamma_watermark
from datetime import datetime

VIP_CHANNEL_ID = 1377786759508787382

def setup_vip_signal_command(bot: commands.Bot, anon_group: app_commands.Group):
    @app_commands.checks.has_permissions(administrator=True)
    @anon_group.command(
        name="señal_vip",
        description="Enviar una señal de trading VIP."
    )
    @app_commands.describe(
        activo="Nombre del activo (ej: AAPL, SPY, QQQ...)",
        target="Precio objetivo de salida",
        stop="Stop Loss",
        analisis="Descripción del análisis",
        side="Dirección del trade: Long o Short",
        imagen="Imagen adjunta"
    )
    async def signal_vip(
        interaction: discord.Interaction,
        activo: str,
        target: str,
        stop: str,
        side: Literal["LONG", "SHORT"],
        imagen: discord.Attachment,
        analisis: str = None,
    ):
        try:
            await interaction.response.defer(thinking=True, ephemeral=True)
            canal = interaction.client.get_channel(VIP_CHANNEL_ID)
            if not canal or not isinstance(canal, discord.TextChannel):
                await interaction.followup.send("❌ No se encontró el canal de señales VIP o no es un canal de texto.", ephemeral=True)
                return
            permissions = canal.permissions_for(interaction.guild.me)
            if not permissions.send_messages or not permissions.embed_links:
                await interaction.followup.send("🚫 El bot no tiene permisos para enviar mensajes o embeds en ese canal.", ephemeral=True)
                return

            embed = discord.Embed(
                title="💎 Señal de Trading VIP",
                color=discord.Color.gold()
            )

            embed.add_field(name="🔹 Activo", value=f"`{activo.upper()}`", inline=True)
            embed.add_field(name="🎯 Target", value=f"`{target}`", inline=True)
            embed.add_field(name="🛑 Stop Loss", value=f"`{stop}`", inline=True)

            embed.add_field(name="📈 Dirección", value=f"`{side.upper()}`", inline=True)

            embed.add_field(name="📊 Resultado", value="`Pendiente`", inline=False)

            if analisis:
                embed.add_field(name="🧠 Análisis", value=analisis, inline=False)

            embed.set_footer(text="No es un consejo financiero. (Not financial advice)")
            embed.timestamp = datetime.fromisoformat(get_ny_timestamp_iso()) # type: ignore

            image_file = None
            if imagen:
                fp = f"tmp_vip_{interaction.id}_{imagen.filename}"
                await imagen.save(fp)
                print(f"Imagen guardada temporalmente en: {fp}")
                watermarked_fp = f"wm_{fp}"
                apply_gamma_watermark(fp, watermarked_fp, "gamma_logo_watermark.png")
                image_file = discord.File(watermarked_fp, filename=imagen.filename)
                embed.set_image(url=f"attachment://{imagen.filename}")  # Only apply image on initial post

            print("Enviando señal VIP al canal...")
            try:
                VIP_ROLE_ID = 1377443273190277240  # actual VIP role ID

                if image_file:
                    mensaje = await canal.send(content=f"<@&{VIP_ROLE_ID}>", embed=embed, file=image_file)
                    try:
                        os.remove(image_file.fp.name)
                    except Exception:
                        pass
                else:
                    mensaje = await canal.send(content=f"<@&{VIP_ROLE_ID}>", embed=embed)
                try:
                    view = SignalResolutionView("vip", activo, mensaje.id)
                    bot.add_view(view)  # Register persistent view BEFORE attaching to message
                    await mensaje.edit(view=view)
                except Exception as e:
                    await interaction.followup.send(f"⚠️ Señal enviada pero no se pudo añadir la vista de resolución: {e}", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Error al enviar el embed: {e}", ephemeral=True)
                return

            await log_to_channel(
                interaction.client,
                f"🔐 Señal VIP enviada por {interaction.user.mention} para **{activo.upper()}** → 🎯 {target} en {canal.mention}"
            )

            await interaction.followup.send("✅ Señal VIP enviada correctamente y registrada en el sistema.", ephemeral=True)

            log_entry = {
                "tipo_senal": "vip",
                "activo": activo,
                "target": target,
                "stop": stop,
                "analisis": analisis,
                "mensaje_id": mensaje.id,
                "timestamp": get_ny_timestamp_iso(),
                "resultado": "pendiente",
                "side": side.upper(),
            }
            if imagen:
                log_entry["imagen"] = imagen.filename

            try:
                save_signal_log(log_entry)
            except Exception as e:
                error_msg = f"❌ Error al registrar señal VIP: {e}\n```\n{traceback.format_exc()}\n```"
                await log_to_channel(interaction.client, error_msg)
                await interaction.followup.send("⚠️ La señal fue enviada, pero no se pudo registrar en el log.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error inesperado: {e}", ephemeral=True)
            import traceback
            print("Unhandled exception:", traceback.format_exc())