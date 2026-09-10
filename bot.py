import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from threading import Thread

import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 833150116582916096
TIMEZONE = ZoneInfo("America/Sao_Paulo")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


class CriarEventoModal(discord.ui.Modal, title="Criar evento"):

    def __init__(self):
        super().__init__()

        self.titulo = discord.ui.TextInput(
            custom_id="titulo",
            placeholder="Ex.: Dragon's End Meta",
            required=True,
            max_length=100
        )
        self.add_item(discord.ui.Label(
            text="Título",
            component=self.titulo
        ))

        self.gw2_id = discord.ui.TextInput(
            custom_id="gw2_id",
            placeholder="Ex.: 1.2.3.4.5.6.7.8",
            required=True,
            max_length=100
        )
        self.add_item(discord.ui.Label(
            text="ID do GW2",
            description="ID usado no comando /sqjoin.",
            component=self.gw2_id
        ))

        hoje = datetime.now(TIMEZONE).date()
        opcoes_data = []

        for i in range(7):
            data = hoje + timedelta(days=i)

            if i == 0:
                label = f"Hoje — {data.strftime('%d/%m/%Y')}"
            elif i == 1:
                label = f"Amanhã — {data.strftime('%d/%m/%Y')}"
            else:
                label = data.strftime("%d/%m/%Y")

            opcoes_data.append(
                discord.SelectOption(
                    label=label,
                    value=data.strftime("%d/%m/%Y")
                )
            )

        self.data_select = discord.ui.Select(
            custom_id="data",
            placeholder="Selecione a data",
            options=opcoes_data,
            min_values=1,
            max_values=1,
            required=True
        )
        self.add_item(discord.ui.Label(
            text="Data",
            component=self.data_select
        ))

        self.horario = discord.ui.TextInput(
            custom_id="horario",
            placeholder="Ex.: 10:00",
            required=True,
            max_length=5
        )
        self.add_item(discord.ui.Label(
            text="Horário",
            component=self.horario
        ))

        self.descricao = discord.ui.TextInput(
            custom_id="descricao",
            placeholder="Descreva o evento...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(discord.ui.Label(
            text="Descrição",
            component=self.descricao
        ))

    async def on_submit(self, interaction: discord.Interaction):
        data_selecionada = self.data_select.values[0]

        await interaction.response.send_message(
            (
                "✅ **Etapa 1 funcionando!**\n\n"
                f"**Título:** {self.titulo.value}\n"
                f"**ID do GW2:** {self.gw2_id.value}\n"
                f"**Data:** {data_selecionada}\n"
                f"**Horário:** {self.horario.value}\n"
                f"**Descrição:** {self.descricao.value}"
            ),
            ephemeral=True
        )


@bot.tree.command(
    name="criarevento",
    description="Cria um novo evento para o canal LFG."
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def criar_evento(interaction: discord.Interaction):
    await interaction.response.send_modal(CriarEventoModal())


@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print(f"Bot conectado como {bot.user}")
    print("Comando /criarevento sincronizado.")


app = Flask(__name__)

@app.route("/")
def home():
    return "Bot online!"


def iniciar_servidor():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


Thread(target=iniciar_servidor, daemon=True).start()

bot.run(TOKEN)
