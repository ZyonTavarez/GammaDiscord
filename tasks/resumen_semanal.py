from discord import app_commands
import discord
from discord.ext import tasks
from datetime import datetime
from dateutil import parser
import json
import os
from utils.signal_utils import get_ny_timestamp_iso

anon_group = app_commands.Group(name="gamma", description="Comandos de Gamma Bot")

LOG_PATH = os.path.join("data", "signals_log.json")
CHANNEL_ID = 1367148946480173116

def setup_resumen_semanal_task(bot):
    @tasks.loop(minutes=1)
    async def resumen_loop():
        now = datetime.fromisoformat(get_ny_timestamp_iso())
        if now.weekday() == 6 and now.hour == 18 and now.minute == 0:
            try:
                if not os.path.exists(LOG_PATH):
                    return
                with open(LOG_PATH, "r") as f:
                    logs = json.load(f)

                semana_actual = now.isocalendar()[1]
                vip_signals = [s for s in logs if s.get("tipo") == "VIP" and parser.parse(s["timestamp"]).astimezone().isocalendar()[1] == semana_actual]
                free_signals = [s for s in logs if s.get("tipo") == "FREE" and parser.parse(s["timestamp"]).astimezone().isocalendar()[1] == semana_actual]

                def contar_stats(signals):
                    total = len(signals)
                    tp = sum(1 for s in signals if s.get("resultado") == "TP")
                    sl = sum(1 for s in signals if s.get("resultado") == "SL")
                    efectividad = round((tp / total) * 100, 2) if total > 0 else 0
                    return total, tp, sl, efectividad

                vip_total, vip_tp, vip_sl, vip_ef = contar_stats(vip_signals)
                free_total, free_tp, free_sl, free_ef = contar_stats(free_signals)

                resumen = f"""
📊 **Resumen semanal de señales - Semana {semana_actual}**

🔐 **VIP**
• Totales: {vip_total}
• Ganadas (TP): {vip_tp}
• Perdidas (SL): {vip_sl}
• Efectividad: {vip_ef}%

📘 **FREE**
• Totales: {free_total}
• Ganadas (TP): {free_tp}
• Perdidas (SL): {free_sl}
• Efectividad: {free_ef}%

🧠 *Este resumen fue generado automáticamente por Gamma Society Bot*
                """.strip()

                canal = bot.get_channel(CHANNEL_ID)
                if canal:
                    await canal.send(resumen)

            except Exception as e:
                print(f"Error generando resumen semanal: {e}")

    @resumen_loop.before_loop
    async def before():
        await bot.wait_until_ready()
    resumen_loop.start()



# Comando manual para mostrar el resumen semanal
@anon_group.command(name="resumen", description="Mostrar el resumen semanal de señales (manual).")
async def resumen_manual(interaction: discord.Interaction):
    print("✅ /gamma resumen ejecutado por:", interaction.user)
    now = datetime.fromisoformat(get_ny_timestamp_iso())
    try:
        if not os.path.exists(LOG_PATH):
            await interaction.response.send_message("No hay señales registradas aún.", ephemeral=True)
            return
        with open(LOG_PATH, "r") as f:
            logs = json.load(f)

        semana_actual = now.isocalendar()[1]
        print("🧪 Semana actual:", semana_actual)
        for s in logs:
            try:
                parsed = parser.parse(s["timestamp"]).astimezone()
                print(f"🔍 Señal: {s.get('activo', 'N/A')}, Tipo: {s.get('tipo')}, Semana: {parsed.isocalendar()[1]}, Timestamp: {s['timestamp']}")
            except Exception as parse_error:
                print(f"⚠️ Error al parsear señal: {s}. Error: {parse_error}")
        vip_signals = [s for s in logs if s.get("tipo") == "VIP" and parser.parse(s["timestamp"]).astimezone().isocalendar()[1] == semana_actual]
        free_signals = [s for s in logs if s.get("tipo") == "FREE" and parser.parse(s["timestamp"]).astimezone().isocalendar()[1] == semana_actual]

        def contar_stats(signals):
            total = len(signals)
            tp = sum(1 for s in signals if s.get("resultado") == "TP")
            sl = sum(1 for s in signals if s.get("resultado") == "SL")
            efectividad = round((tp / total) * 100, 2) if total > 0 else 0
            return total, tp, sl, efectividad

        vip_total, vip_tp, vip_sl, vip_ef = contar_stats(vip_signals)
        free_total, free_tp, free_sl, free_ef = contar_stats(free_signals)

        resumen = f"""
📊 **Resumen semanal de señales - Semana {semana_actual}**

🔐 **VIP**
• Totales: {vip_total}
• Ganadas (TP): {vip_tp}
• Perdidas (SL): {vip_sl}
• Efectividad: {vip_ef}%

📘 **FREE**
• Totales: {free_total}
• Ganadas (TP): {free_tp}
• Perdidas (SL): {free_sl}
• Efectividad: {free_ef}%

🧠 *Este resumen fue generado manualmente por Gamma Society Bot*
        """.strip()

        await interaction.response.send_message(resumen, ephemeral=True)

    except Exception as e:
        print(f"Error al generar resumen manual: {e}")
        await interaction.response.send_message("Hubo un error generando el resumen.", ephemeral=True)