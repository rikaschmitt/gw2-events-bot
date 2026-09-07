import os
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask


# ==========================================
# CONFIGURAÇÕES
# ==========================================

GUILD_ID = 833150116582916096

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

guild = discord.Object(id=GUILD_ID)


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
# BOT
# ==========================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

def criar_opcoes_datas():

    hoje = datetime.now(BRAZIL_TZ).date()

    opcoes = []

    dias_semana = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sábado",
        "Domingo"
    ]

    for i in range(7):

        data = hoje + timedelta(days=i)

        if i == 0:
            descricao = "Hoje"
        elif i == 1:
            descricao = "Amanhã"
        else:
            descricao = dias_semana[data.weekday()]

        opcoes.append(
            discord.SelectOption(
                label=data.strftime("%d/%m/%Y"),
                value=data.isoformat(),
                description=descricao
            )
        )

    return opcoes


def criar_opcoes_horarios():

    opcoes = []

    for hora in range(8, 24):

        horario = f"{hora:02d}:00"

        opcoes.append(
            discord.SelectOption(
                label=horario,
                value=horario
            )
        )

    return opcoes



from bot_interactions import EventoView


# ==========================================
# COMANDO PARA CONFIGURAR O PAINEL
# ==========================================

@bot.tree.command(
    name="configurar_eventos",
    description="Cria o painel de criação de eventos neste canal"
)
async def configurar_eventos(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="🐉 Crie seu evento",
        description=(
            "Seja bem-vindo ao **GW2 Events**!\n\n"
            "Aqui você pode criar uma atividade para "
            "a comunidade participar.\n\n"
            "**Escolha qual tipo de evento você deseja criar:**"
        )
    )

    embed.set_footer(
        text="GW2 Events • Comunidade Guild Wars 2"
    )

    await interaction.channel.send(
        embed=embed,
        view=EventoView()
    )

    await interaction.response.send_message(
        "✅ Painel de criação de eventos criado!",
        ephemeral=True
    )


# ==========================================
# COMANDO /TESTE
# ==========================================

@bot.tree.command(
    name="teste",
    description="Testa se o bot está funcionando"
)
async def teste(
    interaction: discord.Interaction
):

    await interaction.response.send_message(
        "🐉 **Bot funcionando!**\n"
        "O GW2 Events está online."
    )


# ==========================================
# BOT ONLINE
# ==========================================

@bot.event
async def on_ready():

    # Mantém os botões do painel funcionando
    # mesmo depois de reiniciar o bot.
    bot.add_view(
        EventoView()
    )

    # Sincroniza os comandos somente
    # no servidor de testes.
    bot.tree.copy_global_to(
        guild=guild
    )

    await bot.tree.sync(
        guild=guild
    )

    print(
        f"Bot conectado como {bot.user}"
    )

    print(
        "Comandos sincronizados no servidor de testes!"
    )


# ==========================================
# TOKEN
# ==========================================

TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

if not TOKEN:

    raise RuntimeError(
        "A variável DISCORD_TOKEN não foi configurada."
    )


# ==========================================
# INICIAR SERVIDOR WEB
# ==========================================

web_thread = threading.Thread(
    target=run_web_server,
    daemon=True
)

web_thread.start()


# ==========================================
# INICIAR BOT
# ==========================================

bot.run(
    TOKEN
)
