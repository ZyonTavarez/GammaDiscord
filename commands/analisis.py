import discord
from discord import app_commands
from discord.ext import commands
import tempfile
import os
from pdf2image import convert_from_bytes
from PyPDF2 import PdfReader

def setup_analisis_command(bot: commands.Bot, anon_group: app_commands.Group):

    @anon_group.command(name="analisis", description="Publicar un análisis visual desde un archivo PDF")
    @app_commands.describe(
        canal="Canal donde se publicará el análisis",
        archivo="Archivo PDF del análisis (.pdf)"
    )
    async def analisis(
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        archivo: discord.Attachment
    ):
        if not archivo.filename.lower().endswith((".pdf", ".txt", ".md")):
            await interaction.response.send_message(f"❌ El archivo `{archivo.filename}` no tiene un formato válido. Solo se permiten .pdf, .txt o .md.", ephemeral=True)
            return

        try:
            contenido_pdf = await archivo.read()

            if archivo.filename.lower().endswith(".pdf"):
                modo_envio = None
                # Activación automática si el nombre contiene 'market' o 'weekly'
                if "market" in archivo.filename.lower() or "weekly" in archivo.filename.lower():
                    modo_envio = "imagen"
                else:
                    try:
                        from io import BytesIO
                        reader = PdfReader(BytesIO(contenido_pdf))
                        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()

                        if extracted_text and len(extracted_text) <= 4000:
                            modo_envio = "texto"
                        else:
                            modo_envio = "imagen"
                    except Exception:
                        modo_envio = "imagen"

                if modo_envio == "texto":
                    formatted_lines = []
                    for line in extracted_text.splitlines():
                        clean_line = line.strip()
                        if not clean_line:
                            formatted_lines.append("\n")
                        elif clean_line.startswith("•") or clean_line[0].isdigit():
                            formatted_lines.append(clean_line)
                        else:
                            formatted_lines.append(f"\n**{clean_line}**")

                    formatted = f"""📌 **Análisis Completo e Integrado – Market Analysis**

---

{chr(10).join(formatted_lines)}

---

📘 *Gamma Society | Análisis Diario • No es un consejo financiero.*
"""
                    embed = discord.Embed(
                        title="📊 Análisis de Mercado",
                        description=formatted[:4000],
                        color=0x2ECC71
                    )
                    await canal.send(embed=embed)
                    await interaction.response.send_message("✅ Análisis PDF enviado como texto.", ephemeral=True)
                    return

                if modo_envio == "imagen":
                    # Convertir el PDF a imágenes (una por página)
                    imagenes = convert_from_bytes(contenido_pdf)
                    if not imagenes:
                        await interaction.response.send_message("❌ No se pudieron extraer imágenes del PDF.", ephemeral=True)
                        return

                    # Guardar imágenes temporalmente y enviarlas
                    temp_files = []
                    for i, imagen in enumerate(imagenes):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp:
                            imagen.save(temp.name, "PNG")
                            temp_files.append(temp.name)

                    batch_size = 10
                    for batch_start in range(0, len(temp_files), batch_size):
                        batch_paths = temp_files[batch_start:batch_start+batch_size]
                        files = []
                        embeds = []

                        for i, path in enumerate(batch_paths, start=batch_start + 1):
                            with open(path, "rb") as f:
                                filename = f"analisis_{i}.png"
                                files.append(discord.File(f, filename=filename))
                                embed = discord.Embed(
                                    title=f"📊 Análisis de Mercado",
                                    description="\u200b",  # invisible space to create separation
                                    color=0x2ECC71
                                )
                                embed.set_image(url=f"attachment://{filename}")
                                embed.set_footer(text="Gamma Society | Análisis Diario • No es un consejo financiero.")
                                embeds.append(embed)

                        await canal.send(embeds=embeds, files=files)

                    # Limpieza de archivos temporales
                    for path in temp_files:
                        os.remove(path)

                    await interaction.response.send_message("✅ Análisis visual enviado correctamente.", ephemeral=True)
                    return

            if archivo.filename.lower().endswith((".txt", ".md")):
                contenido = contenido_pdf.decode("utf-8").strip()
                # Sanitize to avoid duplicate disclaimers
                disclaimers = [
                    "-- No constituye consejo financiero.",
                    "Gamma Society | Análisis Diario • No es un consejo financiero.",
                    "Gamma Society | Análisis Del Mercado • No es un consejo financiero."
                ]
                for disclaimer in disclaimers:
                    contenido = contenido.replace(disclaimer, "")
                contenido = contenido.strip()
                if not contenido:
                    await interaction.response.send_message("❌ El archivo está vacío.", ephemeral=True)
                    return

                MAX_EMBED_LEN = 4000
                bloques = [contenido[i:i+MAX_EMBED_LEN] for i in range(0, len(contenido), MAX_EMBED_LEN)]

                for i, bloque in enumerate(bloques):
                    embed = discord.Embed(
                        title=f"📊 Análisis de Mercado ({i+1}/{len(bloques)})" if len(bloques) > 1 else "📊 Análisis de Mercado",
                        description=f"""📌 **Análisis Completo e Integrado – Market Analysis**\n\n{bloque}\n\n📘 *Gamma Society | Análisis Del Mercado • No es un consejo financiero.*""",
                        color=0x2ECC71
                    )
                    embed.set_footer(text="Gamma Society | Análisis Diario • No es un consejo financiero.")
                    await canal.send(embed=embed)

                await interaction.response.send_message("✅ Análisis textual enviado correctamente.", ephemeral=True)
                return

        except Exception as e:
            await interaction.response.send_message(f"❌ Error al procesar el análisis: {e}", ephemeral=True)
