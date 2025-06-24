import discord
import json
import os

ALLOWED_ROLES = ["Mod"]
LOG_CHANNEL_ID = 1367148946480173116

async def log_to_channel(client: discord.Client, message: str):
    log_channel = client.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        try:
            await log_channel.send(f"🛠️ **Log:** {message}")
        except Exception as e:
            print(f"❌ No se pudo enviar el log al canal: {e}")
    else:
        print("⚠️ Canal de logs no encontrado.")

class SignalResolutionView(discord.ui.View):
    def __init__(self, tipo_senal: str, activo: str, mensaje_id: int = None):
        super().__init__(timeout=None)
        # Handle "vip" same as "free"
        if tipo_senal == "vip":
            self.tipo_senal = "free"
        else:
            self.tipo_senal = tipo_senal
        self.activo = activo
        self.mensaje_id = mensaje_id
        target_button = discord.ui.Button(label="🎯 Target Alcanzado", style=discord.ButtonStyle.success, custom_id=f"target_reached_{self.mensaje_id}")
        stop_button = discord.ui.Button(label="🛑 Stop Loss Tocado", style=discord.ButtonStyle.danger, custom_id=f"stop_reached_{self.mensaje_id}")

        target_button.callback = self.target_reached_callback
        stop_button.callback = self.stop_reached_callback

        self.add_item(target_button)
        self.add_item(stop_button)

    async def interaction_is_allowed(self, interaction: discord.Interaction) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            member = await interaction.guild.fetch_member(interaction.user.id)
        return member.guild_permissions.administrator or \
               member.id == interaction.guild.owner_id or \
               any(role.name in ALLOWED_ROLES for role in member.roles)

    async def update_embed(self, interaction: discord.Interaction, result_text: str, color: discord.Color):
        await interaction.response.defer(thinking=True, ephemeral=True)

        if not await self.interaction_is_allowed(interaction):
            await interaction.followup.send("🚫 No tienes permiso para marcar esta señal.", ephemeral=True)
            return

        try:
            try:
                mensaje = await interaction.channel.fetch_message(self.mensaje_id)
                print(f"[DEBUG] Mensaje obtenido ID: {mensaje.id}, Esperado: {self.mensaje_id}")
            except Exception as e:
                await interaction.followup.send(f"⚠️ No se pudo obtener el mensaje: {e}", ephemeral=True)
                await log_to_channel(interaction.client, f"⚠️ Error al obtener el mensaje ID {self.mensaje_id}: {e}")
                return

            if mensaje.id != self.mensaje_id:
                await interaction.followup.send("⚠️ El mensaje no corresponde a esta señal.", ephemeral=True)
                return
            if not mensaje.embeds:
                print("[DEBUG] El mensaje no contiene embeds.")
                await interaction.followup.send("⚠️ No se encontró embed para actualizar.", ephemeral=True)
                return

            embed = mensaje.embeds[0]
            new_embed = discord.Embed(
                title=embed.title,
                description=embed.description,
                color=color
            )

            if "🎯" in result_text:
                new_embed.title = "📈 Señal Ejecutada – Target Alcanzado"
            elif "🛑" in result_text:
                new_embed.title = "📉 Señal Ejecutada – Stop Loss Tocado"

            for field in embed.fields:
                if field.name != "📊 Resultado":
                    new_embed.add_field(name=field.name, value=field.value, inline=field.inline)

            new_embed.add_field(name="📊 Resultado", value=result_text, inline=False)

            # new_embed.add_field(name="👤 Actualizado por", value=f"{interaction.user.display_name}", inline=True)

            # Copy footer and timestamp
            new_embed.set_footer(text=embed.footer.text if embed.footer else None)
            new_embed.timestamp = embed.timestamp

            # Preserve original image if present
            if embed.image and embed.image.url:
                new_embed.set_image(url=embed.image.url)

            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True

            await mensaje.edit(embed=new_embed, view=self, attachments=mensaje.attachments)
            print("[DEBUG] mensaje.edit ejecutado correctamente.")
            await log_to_channel(interaction.client, f"✅ Señal actualizada visualmente: {self.activo} - {result_text}")

            # Actualizar log si existe
            if os.path.exists("signals_log.json"):
                with open("signals_log.json", "r", encoding="utf-8") as f:
                    try:
                        logs = json.load(f)
                    except json.JSONDecodeError:
                        logs = []

                updated = False
                for entry in logs:
                    if (
                        str(entry.get("mensaje_id")) == str(self.mensaje_id) and
                        entry.get("resultado") == "pendiente"
                    ):
                        entry["resultado"] = result_text
                        updated = True

                if updated:
                    print(f"[DEBUG] Log actualizado para mensaje_id {self.mensaje_id} con resultado: {result_text}")
                    with open("signals_log.json", "w", encoding="utf-8") as f:
                        json.dump(logs, f, ensure_ascii=False, indent=2)
                else:
                    print(f"[DEBUG] No se encontró entrada pendiente para mensaje_id {self.mensaje_id}, log no actualizado.")

            await interaction.followup.send(f"✅ Resultado actualizado para **{self.activo}**: {result_text}", ephemeral=True)
            await log_to_channel(interaction.client, f"📍 Resultado marcado para {self.activo}: {result_text}")
        except Exception as e:
            await interaction.followup.send(f"❌ Error al actualizar la señal: {e}", ephemeral=True)
            await log_to_channel(interaction.client, f"❌ Error al actualizar embed: {e}")


    async def target_reached_callback(self, interaction: discord.Interaction):
        await self.update_embed(interaction, "🎯 Target Alcanzado", discord.Color.green())

    async def stop_reached_callback(self, interaction: discord.Interaction):
        await self.update_embed(interaction, "🛑 Stop Loss Tocado", discord.Color.red())