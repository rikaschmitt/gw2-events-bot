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
LFG_CHANNEL_ID = 1546643357718020148
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
            placeholder="Ex.: Nome.1234",
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

            opcoes_data.append(discord.SelectOption(
                label=label,
                value=data.strftime("%d/%m/%Y")
            ))

        self.data_select = discord.ui.Select(
            custom_id="data",
            placeholder="Selecione a data",
            options=opcoes_data,
            min_values=1,
            max_values=1
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

        channel = interaction.guild.get_channel(LFG_CHANNEL_ID)

        if channel is None:
            await interaction.response.send_message(
                "❌ Não foi possível encontrar o canal #lfg.",
                ephemeral=True
            )
            return

        data_selecionada = self.data_select.values[0]

        # Formata cada linha da descrição como quote do Discord.
        descricao_formatada = self.descricao.value.replace(
            "\n",
            "\n> "
        )

        # O Discord não permite definir tamanho de fonte em pixels.
        # No Embed, porém, o texto segue a tipografia padrão do Discord
        # e o título recebe automaticamente maior destaque.
        embed = discord.Embed(
            title=self.titulo.value,
            description=(
                f"📅 **{data_selecionada}**   🕐 **{self.horario.value}**\n\n"
                f"> {descricao_formatada}"
            ),
            color=discord.Color.blue()
        )

        # "Author" é o elemento do Embed mais próximo do pequeno
        # cabeçalho "Novo Evento LFG" da referência.
        embed.set_author(
            name="Novo Evento LFG"
        )

        embed.add_field(
            name="Para entrar no squad",
            value=f"`/sqjoin {self.gw2_id.value}`",
            inline=False
        )

        embed.set_footer(
            text="Ficou interessado? Reaja com ✅ nesta mensagem."
        )


        try:
            evento = await channel.send(embed=embed)
            await evento.add_reaction("✅")

            await interaction.response.send_message(
                "✅ Evento publicado no #lfg!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para publicar no #lfg.",
                ephemeral=True
            )

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao publicar o evento.",
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
