import os
import threading

import discord
from discord.ext import commands
from flask import Flask


# ==========================================
# SERVIDOR WEB PARA O RENDER
# ==========================================

app = Flask(__name__)


@app.route("/")
def home():
    return "🐉 GW2 Events Bot está online!"


@app.route("/health")
def health():
    return "OK"


def run_web_server():
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )


# ==========================================
# BOT DO DISCORD
# ==========================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():

    await bot.tree.sync()

    print(f"Bot conectado como {bot.user}")
    print("Comandos sincronizados!")


@bot.tree.command(
    name="teste",
    description="Testa se o bot está funcionando"
)
async def teste(interaction: discord.Interaction):

    await interaction.response.send_message(
        "🐉 **Bot funcionando!**\n"
        "O GW2 Events está online."
    )


# ==========================================
# INICIAR TUDO
# ==========================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "A variável DISCORD_TOKEN não foi configurada."
    )


web_thread = threading.Thread(
    target=run_web_server,
    daemon=True
)

web_thread.start()


bot.run(TOKEN)
