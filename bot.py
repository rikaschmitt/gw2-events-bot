import os
import threading

import discord
from discord.ext import commands
from flask import Flask


# ============================================================
# CONFIGURAÇÕES
# ============================================================

GUILD_ID = 833150116582916096


# ============================================================
# FLASK / RENDER
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "🐉 GW2 Events Bot está online!"


@app.route("/health")
def health():
    return "OK"


def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# ============================================================
# DISCORD BOT
# ============================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# EVENTOS DO DISCORD
# ============================================================

@bot.event
async def on_ready():

    print(f"🤖 Bot conectado como {bot.user}")

    guild = discord.Object(id=GUILD_ID)

    # Sincroniza os slash commands apenas no servidor de testes.
    # Isso faz com que os comandos apareçam imediatamente.
    await bot.tree.sync(guild=guild)

    print("✅ Slash commands sincronizados.")


# ============================================================
# COMANDO DE TESTE
# ============================================================

@bot.tree.command(
    name="teste",
    description="Testa se o bot está funcionando."
)
async def teste(interaction: discord.Interaction):

    await interaction.response.send_message(
        "🐉 O bot está funcionando!",
        ephemeral=True
    )


# ============================================================
# COMANDO PARA CONFIGURAR O PAINEL DE EVENTOS
# ============================================================

@bot.tree.command(
    name="configurar_eventos",
    description="Cria o painel para criação de eventos."
)
async def configurar_eventos(interaction: discord.Interaction):

    await interaction.response.send_message(
        "⚙️ O painel de criação de eventos será configurado aqui.",
        ephemeral=True
    )


# ============================================================
# INICIALIZAÇÃO
# ============================================================

if __name__ == "__main__":

    # Inicia o servidor web do Render em uma thread separada.
    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )

    web_thread.start()

    print("🌐 Servidor web iniciado.")

    # Inicia o bot do Discord.
    token = os.environ.get("DISCORD_TOKEN")

    if not token:
        raise RuntimeError(
            "A variável de ambiente DISCORD_TOKEN não foi encontrada."
        )

    bot.run(token)
