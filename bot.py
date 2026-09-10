import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from threading import Thread

import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

from bot_database import buscar_gw2_id, salvar_gw2_id, salvar_evento, buscar_meus_eventos

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 833150116582916096
LFG_CHANNEL_ID = 1546643357718020148
TIMEZONE = ZoneInfo("America/Sao_Paulo")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


class CriarEventoModal(discord.ui.Modal, title="Criar evento"):

    def __init__(self, gw2_id_salvo=None):
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
            default=gw2_id_salvo or discord.utils.MISSING,
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

        # Salva o ID do GW2 do usuário para reutilizar nos próximos eventos.
        salvar_gw2_id(
            discord_user_id=interaction.user.id,
            discord_username=interaction.user.display_name,
            gw2_id=self.gw2_id.value.strip()
        )

        # Formata cada linha da descrição como quote do Discord.
        descricao_formatada = self.descricao.value.replace(
            "\n",
            "\n> "
        )

        # O título fica no corpo da descrição usando Markdown "#",
        # que permite um destaque maior do que o campo "title" do Embed.
        # O Embed continua sendo usado para manter a caixa e a borda colorida.
        embed = discord.Embed(
            description=(
                f"# {self.titulo.value}\n"
                f"📅 **{data_selecionada}**\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0🕐 **{self.horario.value}**\n\n"
                f"> {descricao_formatada}\n\n"
                f"**Para entrar no squad:** `/sqjoin {self.gw2_id.value}`"
            ),
            color=discord.Color.blue()
        )

        # O author continua pequeno, como na referência.
        # O link para o próprio canal faz o texto aparecer como link
        # quando o Discord aplica o estilo de hyperlink.
        embed.set_author(
            name="Novo Evento LFG",
            url=f"https://discord.com/channels/{GUILD_ID}/{LFG_CHANNEL_ID}"
        )

        embed.set_footer(
            text="Ficou interessado? Reaja com ✅ nesta mensagem."
        )


        try:
            # Publica primeiro no Discord.
            evento = await channel.send(embed=embed)
            await evento.add_reaction("✅")

            # Depois registra o evento no banco, usando o ID real
            # da mensagem publicada no #lfg.
            event_id = salvar_evento(
                discord_message_id=evento.id,
                discord_channel_id=channel.id,
                discord_guild_id=interaction.guild.id,
                titulo=self.titulo.value.strip(),
                gw2_id=self.gw2_id.value.strip(),
                event_date=datetime.strptime(
                    data_selecionada,
                    "%d/%m/%Y"
                ).date(),
                event_time=datetime.strptime(
                    self.horario.value.strip(),
                    "%H:%M"
                ).time(),
                descricao=self.descricao.value.strip(),
                organizer_discord_id=interaction.user.id,
                organizer_name=interaction.user.display_name,
            )

            print(
                f"Evento LFG salvo no banco: "
                f"id={event_id}, mensagem={evento.id}"
            )

            # Confirmação somente para o criador.
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

        except (ValueError, TypeError):
            await interaction.response.send_message(
                "❌ A data ou o horário do evento está em um formato inválido.",
                ephemeral=True
            )

        except Exception as erro:
            # O evento já pode ter sido publicado no Discord.
            # Mantemos a publicação e registramos o erro no log do Render.
            print(f"Erro ao salvar evento LFG no banco: {erro}")

            try:
                await interaction.response.send_message(
                    "⚠️ O evento foi publicado no #lfg, mas não foi possível "
                    "registrá-lo no banco.",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                pass

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
    gw2_id_salvo = buscar_gw2_id(interaction.user.id)

    await interaction.response.send_modal(
        CriarEventoModal(gw2_id_salvo=gw2_id_salvo)
    )


@bot.tree.command(
    name="meuseventos",
    description="Mostra seus próximos eventos no LFG."
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def meus_eventos(interaction: discord.Interaction):
    try:
        eventos = buscar_meus_eventos(interaction.user.id)
    except Exception as erro:
        print(
            f"Erro ao buscar eventos do usuário "
            f"{interaction.user.id}: {erro}"
        )
        await interaction.response.send_message(
            "❌ Não foi possível consultar seus eventos.",
            ephemeral=True
        )
        return

    if not eventos:
        print(
            f"/meuseventos: nenhum evento futuro encontrado para "
            f"discord_user_id={interaction.user.id}"
        )
        await interaction.response.send_message(
            "📅 Você não tem eventos futuros ativos.",
            ephemeral=True
        )
        return

    linhas = []

    for evento in eventos:
        titulo = evento["titulo"]
        data = evento["event_date"].strftime("%d/%m/%Y")
        horario = evento["event_time"].strftime("%H:%M")
        link = (
            f"https://discord.com/channels/"
            f"{GUILD_ID}/{LFG_CHANNEL_ID}/{evento['discord_message_id']}"
        )

        linhas.append(
            f"• [{titulo}]({link}) - {data} às {horario}"
        )

    embed = discord.Embed(
        title="📅 Meus eventos",
        description="\n".join(linhas),
        color=discord.Color.blue()
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print(f"Bot conectado como {bot.user}")
    print("Comandos /criarevento e /meuseventos sincronizados.")


app = Flask(__name__)

@app.route("/")
def home():
    return "Bot online!"


def iniciar_servidor():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


Thread(target=iniciar_servidor, daemon=True).start()

bot.run(TOKEN)
