from discord import app_commands, Interaction, Message, Object
from discord.ext import commands
from discord.ui import Modal, TextInput
from discord import TextStyle

def setup_reply_command(bot: commands.Bot):
    class ReplyModal(Modal, title="Responder como Gamma"):
        def __init__(self, message_to_reply: Message):
            super().__init__()
            self.message_to_reply = message_to_reply
            self.reply_input = TextInput(
                label="Respuesta",
                style=TextStyle.paragraph,
                placeholder="Escribe tu respuesta...",
                max_length=2000
            )
            self.add_item(self.reply_input)

        async def on_submit(self, interaction: Interaction):
            try:
                await self.message_to_reply.reply(self.reply_input.value)
                await interaction.response.send_message("✅ Respuesta enviada correctamente.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Error al enviar respuesta: {e}", ephemeral=True)

    @app_commands.context_menu(name="Reply")
    async def reply_as_bot(interaction: Interaction, message: Message):
        await interaction.response.send_modal(ReplyModal(message))

    bot.tree.add_command(reply_as_bot, guild=Object(id=bot.GUILD_ID))