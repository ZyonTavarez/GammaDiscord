from discord.ext import commands
import discord
from discord import app_commands
import traceback

def setup_forward_message_command(bot: commands.Bot, anon_group: app_commands.Group, log_to_channel):
    @anon_group.command(name="mensaje", description="Enviar un mensaje anónimo a un canal público.")
    @app_commands.describe(
        message="Contenido del mensaje",
        destination_channel="Canal donde se enviará el mensaje",
        attachment="Imagen opcional para adjuntar al mensaje"
    )
    async def forward_message(
        interaction: discord.Interaction,
        message: str = None,
        destination_channel: discord.TextChannel = None,
        attachment: discord.Attachment = None
    ):
        allowed = (
            interaction.user.guild_permissions.administrator or
            interaction.user.id == interaction.guild.owner_id or
            any(role.name in ["Mod"] for role in interaction.user.roles)
        )
        if not allowed:
            await interaction.response.send_message("🚫 No tienes permiso para usar este comando.", ephemeral=True)
            return

        if not message and not attachment:
            await interaction.response.send_message(
                "❌ Debes incluir al menos un mensaje o una imagen para enviar.",
                ephemeral=True
            )
            return

        if not destination_channel:
            await interaction.response.send_message(
                "❌ Debes seleccionar un canal de destino.",
                ephemeral=True
            )
            return

        try:
            file = None
            if attachment:
                if attachment.filename.endswith((".txt", ".md")):
                    content_bytes = await attachment.read()
                    content = content_bytes.decode("utf-8")
                else:
                    file = await attachment.to_file()

            content = message or None
            if attachment and attachment.filename.endswith((".txt", ".md")):
                content_bytes = await attachment.read()
                content = content_bytes.decode("utf-8")

            if file:
                try:
                    await destination_channel.send(content=content, file=file, allowed_mentions=discord.AllowedMentions.none())
                except discord.HTTPException as file_error:
                    await interaction.response.send_message(f"❌ Error al subir el archivo: {file_error}", ephemeral=True)
                    return
            else:
                await destination_channel.send(content=content, allowed_mentions=discord.AllowedMentions.none())
            await interaction.response.send_message("✅ Mensaje enviado correctamente.", ephemeral=True)
            await log_to_channel(bot, f"📨 Mensaje anónimo enviado a {destination_channel.mention}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al enviar el mensaje: {e}", ephemeral=True)
            await log_to_channel(bot, f"❌ Error al enviar mensaje anónimo:\n```\n{traceback.format_exc()}\n```")
