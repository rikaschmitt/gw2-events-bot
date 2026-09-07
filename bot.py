import os
import threading

import discord
from discord.ext import commands
from discord import app_commands
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


# ==========================================
# MODAL — CRIAR EVENTO
# ==========================================

class CriarEventoModal(discord.ui.Modal, title="🐉 Criar novo evento"):

    tipo = discord.ui.TextInput(
        label="Tipo do evento",
        placeholder="Raid, Fractal, Hero Point, Meta Event...",
        required=True,
        max_length=50
    )

    nome = discord.ui.TextInput(
        label="Nome do evento",
        placeholder="Ex.: Vale Guardian, Dragonstorm...",
        required=True,
        max_length=100
    )

    data_horario = discord.ui.TextInput(
        label="Data e horário",
        placeholder="Ex.: 12/09/2026 às 21:30",
        required=True,
        max_length=30
    )

    vagas = discord.ui.TextInput(
        label="Número de vagas",
        placeholder="Ex.: 10",
        required=True,
        max_length=3
    )

    descricao = discord.ui.TextInput(
        label="Descrição",
        placeholder="Informações adicionais...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):

        try:
            numero_vagas = int(self.vagas.value)

            if numero_vagas <= 0:
                raise ValueError

        except ValueError:
            await interaction.response.send_message(
                "❌ O número de vagas precisa ser um número maior que zero.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🎮 {self.tipo.value.upper()} — {self.nome.value}",
            description=self.descricao.value or "Sem descrição."
        )

        embed.add_field(
            name="📅 Data e horário",
            value=self.data_horario.value,
            inline=True
        )

        embed.add_field(
            name="👥 Vagas",
            value=f"0/{numero_vagas}",
            inline=True
        )

        embed.add_field(
            name="👤 Organizador",
            value=interaction.user.mention,
            inline=False
        )

        embed.set_footer(
            text="GW2 Events • Evento criado pela comunidade"
        )

        await interaction.response.send_message(
            "✅ **Evento criado com sucesso!**",
            ephemeral=True
        )

        await interaction.channel.send(
            embed=embed
        )


# ==========================================
# GRUPO /EVENTO
# ==========================================

class EventoGroup(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="evento",
            description="Gerenciamento de eventos"
        )

    @app_commands.command(
        name="criar",
        description="Cria um novo evento"
    )
    async def criar(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.send_modal(
            CriarEventoModal()
        )


bot.tree.add_command(EventoGroup())


# ==========================================
# /TESTE
# ==========================================

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
# BOT ONLINE
# ==========================================

@bot.event
async def on_ready():

    guild = discord.Object(id=833150116582916096)

    bot.tree.copy_global_to(guild=guild)

    await bot.tree.sync(guild=guild)

    print(f"Bot conectado como {bot.user}")
    print("Comandos sincronizados no servidor de testes!")


# ==========================================
# INICIAR SERVIDOR WEB
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
