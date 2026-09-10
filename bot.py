import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURAÇÕES
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 833150116582916096

TIMEZONE = ZoneInfo("America/Sao_Paulo")


# ============================================================
# BOT
# ============================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# MODAL — CRIAR EVENTO
# ============================================================

class CriarEventoModal(discord.ui.Modal, title="Criar evento"):

    titulo = discord.ui.TextInput(
        label="Título",
        placeholder="Ex.: Dragon's End Meta",
        required=True,
        max_length=100
    )

    gw2_id = discord.ui.TextInput(
        label="ID do GW2",
        placeholder="Ex.: 1.2.3.4.5.6.7.8",
        required=True,
        max_length=100
    )

    data = discord.ui.Select(
        placeholder="Selecione a data",
        options=[]
    )

    horario = discord.ui.TextInput(
        label="Horário",
        placeholder="Ex.: 10:00",
        required=True,
        max_length=5
    )

    descricao = discord.ui.TextInput(
        label="Descrição",
        placeholder="Descreva o evento...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    def __init__(self):
        super().__init__()

        hoje = datetime.now(TIMEZONE).date()

        opcoes = []

        for i in range(7):
            data = hoje + timedelta(days=i)

            if i == 0:
                nome = f"Hoje — {data.strftime('%d/%m/%Y')}"
            elif i == 1:
                nome = f"Amanhã — {data.strftime('%d/%m/%Y')}"
            else:
                nome = data.strftime("%d/%m/%Y")

            opcoes.append(
                discord.SelectOption(
                    label=nome,
                    value=data.strftime("%d/%m/%Y")
                )
            )

        self.data.options = opcoes

    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.send_message(
            (
                "✅ **Modal recebida!**\n\n"
                f"**Título:** {self.titulo.value}\n"
                f"**ID do GW2:** {self.gw2_id.value}\n"
                f"**Data:** {self.data.values[0]}\n"
                f"**Horário:** {self.horario.value}\n"
                f"**Descrição:** {self.descricao.value}"
            ),
            ephemeral=True
        )


# ============================================================
# COMANDO /CRIAR EVENTO
# ============================================================

@bot.tree.command(
    name="criarevento",
    description="Cria um novo evento para o canal LFG."
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def criar_evento(interaction: discord.Interaction):

    await interaction.response.send_modal(
        CriarEventoModal()
    )


# ============================================================
# INICIALIZAÇÃO
# ============================================================

@bot.event
async def on_ready():

    guild = discord.Object(id=GUILD_ID)

    await bot.tree.sync(guild=guild)

    print(f"Bot conectado como {bot.user}")
    print("Comando /criarevento sincronizado.")


# ============================================================
# SERVIDOR HTTP PARA O RENDER
# ============================================================

from flask import Flask
from threading import Thread

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot online!"


def iniciar_servidor():
    port = int(os.environ.get("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port
    )


Thread(
    target=iniciar_servidor,
    daemon=True
).start()


# ============================================================
# INICIA O BOT
# ============================================================

bot.run(TOKEN)
