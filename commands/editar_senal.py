import discord
from discord import app_commands
from discord.ext import commands
import json

def setup_editar_senal_command(bot: commands.Bot, anon_group: app_commands.Group):

    @anon_group.command(
        name="editar_senal",
        description="Editar manualmente el resultado de una señal (Target o Stop)."
    )
    @app_commands.describe(
        message_id="ID del mensaje de la señal",
        resultado="Resultado a establecer: 🎯 Target Alcanzado o 🛑 Stop Loss Tocado"
    )
    @app_commands.choices(
        resultado=[
            app_commands.Choice(name="🎯 Target Alcanzado", value="🎯 Target Alcanzado"),
            app_commands.Choice(name="🛑 Stop Loss Tocado", value="🛑 Stop Loss Tocado")
        ]
    )
    async def editar_senal(
        interaction: discord.Interaction,
        message_id: str,
        resultado: app_commands.Choice[str]
    ):
        # Verificar permisos de admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
            return

        try:
            message_id_int = int(message_id)
            mensaje = await interaction.channel.fetch_message(message_id_int)
        except Exception as e:
            await interaction.response.send_message(f"❌ No se pudo obtener el mensaje: {e}", ephemeral=True)
            return

        # Leer signals_log.json
        try:
            with open("signals_log.json", "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al leer signals_log.json: {e}", ephemeral=True)
            return

        # Buscar la señal
        updated = False
        for entry in logs:
            if str(entry.get("mensaje_id")) == str(message_id_int) and entry.get("resultado") == "pendiente":
                entry["resultado"] = resultado.value
                updated = True
                break

        if not updated:
            await interaction.response.send_message("⚠️ No se encontró una señal pendiente con ese mensaje_id.", ephemeral=True)
            return

        # Actualizar embed del mensaje
        try:
            embed = mensaje.embeds[0]
            new_embed = embed.copy()
            for i, field in enumerate(new_embed.fields):
                if field.name == "📊 Resultado":
                    new_embed.set_field_at(i, name="📊 Resultado", value=f"`{resultado.value}`", inline=False)

            # Preserve the existing embed image reference, no need to set_image again
            await mensaje.edit(embed=new_embed, attachments=mensaje.attachments)

            # Guardar log actualizado
            with open("signals_log.json", "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)

            # Log al canal de logs usando log_to_channel util
            from utils.bot_logging import log_to_channel
            await log_to_channel(
                bot,
                f"🛠️ Señal actualizada manualmente por {interaction.user.mention}: {resultado.value} para mensaje_id {message_id_int}"
            )

            await interaction.response.send_message(f"✅ Señal actualizada a: {resultado.value}", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error al actualizar la señal: {e}", ephemeral=True)