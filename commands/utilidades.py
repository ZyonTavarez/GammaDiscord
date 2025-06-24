import discord
from discord import app_commands
from discord.ext import commands

def setup_utilidades_commands(anon_group: app_commands.Group):
    @app_commands.checks.has_permissions(administrator=True)
    @anon_group.command(
        name="mostrar_reglas",
        description="Muestra las reglas del servidor."
    )
    async def mostrar_reglas(interaction: discord.Interaction):
        reglas = (
            "**📜 Reglas del servidor Gamma Society**\n"
            "1. Respeto mutuo: No se tolera el acoso o la discriminación.\n"
            "2. Nada de contenido explícito, gore o NSFW.\n"
            "3. No spam. Usa los canales apropiados.\n"
            "4. No promociones sin permiso.\n"
            "5. Mantén el enfoque: estamos aquí para crecer como traders.\n"
        )
        await interaction.response.send_message(reglas, ephemeral=True)
    @app_commands.checks.has_permissions(administrator=True)
    @anon_group.command(
        name="analisis",
        description="Publica un análisis de mercado desde un archivo PDF, TXT o MD."
    )
    @app_commands.describe(
        archivo="Archivo del análisis (PDF, TXT o MD)",
        canal="Canal donde se publicará el análisis (opcional si el nombre del archivo contiene _vip o _free)",
        imagen="Imagen opcional para adjuntar al análisis"
    )
    async def publicar_analisis(
        interaction: discord.Interaction,
        archivo: discord.Attachment,
        canal: discord.TextChannel = None,
        imagen: discord.Attachment = None
    ):
        if not archivo.filename.endswith((".pdf", ".txt", ".md")):
            await interaction.response.send_message("❌ Solo se permiten archivos PDF, TXT o MD.", ephemeral=True)
            return

        # Autoasignar canal si no se seleccionó manualmente
        if canal is None:
            if "_vip" in archivo.filename.lower():
                canal = interaction.guild.get_channel(1351311086984626308)
            elif "_free" in archivo.filename.lower():
                canal = interaction.guild.get_channel(1365391408827207832)

        if canal is None:
            await interaction.response.send_message("❌ No se pudo determinar el canal automáticamente. Selecciona uno manualmente.", ephemeral=True)
            return

        try:
            contenido = ""
            if archivo.filename.endswith(".pdf"):
                import io
                from PyPDF2 import PdfReader
                buffer = io.BytesIO(await archivo.read())
                reader = PdfReader(buffer)
                for page in reader.pages:
                    contenido += page.extract_text() + "\n"
            else:
                contenido = (await archivo.read()).decode("utf-8")

            if not contenido.strip():
                await interaction.response.send_message("❌ El archivo no contiene texto legible.", ephemeral=True)
                return

            embed = discord.Embed(
                title="📊 Análisis de Mercado",
                description=contenido[:4000],  # Discord embed limit
                color=discord.Color.purple()
            )
            embed.set_footer(text="Gamma Society | Análisis")
            embed.timestamp = discord.utils.utcnow()
            if imagen:
                embed.set_image(url=imagen.url)

            await canal.send(embed=embed)
            await interaction.response.send_message("✅ Análisis publicado correctamente.", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error al procesar el archivo: {e}", ephemeral=True)