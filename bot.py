import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from threading import Thread

import discord
from discord import app_commands
from discord.ext import commands, tasks
from flask import Flask

from bot_database import buscar_gw2_id, salvar_gw2_id, salvar_evento, buscar_meus_eventos, excluir_evento, buscar_eventos_expirados

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

        # Reconhece a interação sem criar uma mensagem visível no canal.
        # Todas as respostas ao usuário serão enviadas por DM.
        await interaction.response.defer(ephemeral=True)

        channel = interaction.guild.get_channel(LFG_CHANNEL_ID)

        if channel is None:
            try:
                await interaction.user.send(
                    "❌ Não foi possível encontrar o canal #lfg."
                )
            except discord.Forbidden:
                pass
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

            # Confirmação enviada exclusivamente por DM.
            try:
                await interaction.user.send(
                    "✅ Evento publicado no #lfg!"
                )
            except discord.Forbidden:
                print(
                    f"Não foi possível enviar DM de confirmação "
                    f"para {interaction.user.id}."
                )

        except discord.Forbidden:
            try:
                await interaction.user.send(
                    "❌ Não tenho permissão para publicar no #lfg."
                )
            except discord.Forbidden:
                pass

        except discord.HTTPException:
            try:
                await interaction.user.send(
                    "❌ Ocorreu um erro ao publicar o evento."
                )
            except discord.Forbidden:
                pass

        except (ValueError, TypeError):
            try:
                await interaction.user.send(
                    "❌ A data ou o horário do evento está em um formato inválido."
                )
            except discord.Forbidden:
                pass

        except Exception as erro:
            # O evento já pode ter sido publicado no Discord.
            # Mantemos a publicação e registramos o erro no log do Render.
            print(f"Erro ao salvar evento LFG no banco: {erro}")

            try:
                await interaction.user.send(
                    "⚠️ O evento foi publicado no #lfg, mas não foi possível "
                    "registrá-lo no banco."
                )
            except discord.Forbidden:
                pass


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


class ExcluirEventoView(discord.ui.View):
    def __init__(self, eventos, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

        for evento in eventos:
            self.add_item(
                ExcluirEventoButton(
                    evento_id=evento["id"],
                    message_id=evento["discord_message_id"],
                    titulo=evento["titulo"],
                    user_id=user_id
                )
            )


class ExcluirEventoButton(discord.ui.Button):
    def __init__(self, evento_id, message_id, titulo, user_id):
        # O Discord permite no máximo 5 botões por linha.
        # Cada botão representa um dos eventos listados.
        super().__init__(
            label="Excluir",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id=f"excluir_evento:{evento_id}"
        )
        self.evento_id = evento_id
        self.message_id = message_id
        self.titulo = titulo
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        # Somente o criador do evento pode excluí-lo.
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Você não pode excluir os eventos de outra pessoa.",
                ephemeral=True
            )
            return

        try:
            # Primeiro marca como inativo no banco.
            excluido = excluir_evento(
                evento_id=self.evento_id,
                organizer_discord_id=self.user_id
            )

            if not excluido:
                await interaction.response.send_message(
                    "❌ Esse evento não está mais disponível para exclusão.",
                    ephemeral=True
                )
                return

            # Depois tenta remover a mensagem do #lfg.
            guild = bot.get_guild(GUILD_ID)
            channel = guild.get_channel(LFG_CHANNEL_ID) if guild else None

            if channel is not None:
                try:
                    mensagem = await channel.fetch_message(self.message_id)
                    await mensagem.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    print(
                        f"Sem permissão para excluir a mensagem "
                        f"{self.message_id} do evento {self.evento_id}."
                    )
                except discord.HTTPException as erro:
                    print(
                        f"Erro ao excluir mensagem {self.message_id}: {erro}"
                    )

            await interaction.response.send_message(
                f"🗑️ Evento **{self.titulo}** excluído.",
                ephemeral=True
            )

            # Desabilita todos os botões desta lista depois da exclusão.
            for item in self.view.children:
                item.disabled = True

            try:
                await interaction.message.edit(view=self.view)
            except discord.HTTPException:
                pass

        except Exception as erro:
            print(f"Erro ao excluir evento {self.evento_id}: {erro}")

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Não foi possível excluir o evento.",
                    ephemeral=True
                )


class MeusEventosView(discord.ui.View):
    def __init__(self, eventos, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

        # Discord permite até 5 botões por Action Row.
        # Criamos uma linha de botões por grupo de até 5 eventos.
        for evento in eventos:
            self.add_item(
                ExcluirEventoButton(
                    evento_id=evento["id"],
                    message_id=evento["discord_message_id"],
                    titulo=evento["titulo"],
                    user_id=user_id
                )
            )


@bot.tree.command(
    name="meuseventos",
    description="Mostra seus próximos eventos no LFG."
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def meus_eventos(interaction: discord.Interaction):
    # Reconhece o comando sem deixar mensagem visível no canal.
    await interaction.response.defer(ephemeral=True)

    try:
        eventos = buscar_meus_eventos(interaction.user.id)
    except Exception as erro:
        print(
            f"Erro ao buscar eventos do usuário "
            f"{interaction.user.id}: {erro}"
        )
        try:
            await interaction.user.send(
                "❌ Não foi possível consultar seus eventos."
            )
        except discord.Forbidden:
            pass
        return

    if not eventos:
        print(
            f"/meuseventos: nenhum evento futuro encontrado para "
            f"discord_user_id={interaction.user.id}"
        )
        try:
            await interaction.user.send(
                "📅 Você não tem eventos futuros ativos."
            )
        except discord.Forbidden:
            pass
        return

    linhas = []

    for indice, evento in enumerate(eventos, start=1):
        titulo = evento["titulo"]
        data = evento["event_date"].strftime("%d/%m/%Y")
        horario = evento["event_time"].strftime("%H:%M")
        link = (
            f"https://discord.com/channels/"
            f"{GUILD_ID}/{LFG_CHANNEL_ID}/{evento['discord_message_id']}"
        )

        linhas.append(
            f"**{indice}.** [{titulo}]({link}) - {data} às {horario}"
        )

    embed = discord.Embed(
        title="📅 Seus eventos ativos:",
        description="\n".join(linhas),
        color=discord.Color.blue()
    )

    embed.set_footer(
        text="Use o botão 🗑️ correspondente para excluir um evento."
    )

    # Discord aceita no máximo 25 componentes em uma View.
    # Para manter o código simples, mostramos até 20 eventos.
    eventos_view = eventos[:20]

    view = MeusEventosView(
        eventos=eventos_view,
        user_id=interaction.user.id
    )

    # Os botões são adicionados em grupos de até 5 por linha.
    # O título do botão identifica o evento pelo número.
    for indice, button in enumerate(view.children, start=1):
        button.label = f"Excluir {indice}"

    try:
        # Envia a lista diretamente para a DM do usuário.
        await interaction.user.send(
            embed=embed,
            view=view
        )

        # Não envia confirmação no canal. A própria DM contém a resposta.

    except discord.Forbidden:
        print(
            f"Não foi possível enviar DM para {interaction.user.id}. "
            "Mensagens diretas podem estar bloqueadas."
        )


@tasks.loop(minutes=5)
async def verificar_eventos_expirados():
    """
    A cada 5 minutos, verifica eventos ativos que já passaram.
    Remove a mensagem do #lfg e marca o evento como expired no banco.
    """
    try:
        eventos_expirados = buscar_eventos_expirados()

        if not eventos_expirados:
            return

        channel = bot.get_channel(LFG_CHANNEL_ID)

        if channel is None:
            print("Verificação automática: canal #lfg não encontrado.")
            return

        for evento in eventos_expirados:
            event_id = evento["id"]
            message_id = evento["discord_message_id"]
            titulo = evento["titulo"]

            try:
                mensagem = await channel.fetch_message(message_id)
                await mensagem.delete()
                print(
                    f"Evento expirado removido do #lfg: "
                    f"id={event_id}, mensagem={message_id}, titulo={titulo}"
                )
            except discord.NotFound:
                print(
                    f"Mensagem do evento expirado já não existe: "
                    f"id={event_id}, mensagem={message_id}"
                )
            except discord.Forbidden:
                print(
                    f"Sem permissão para excluir mensagem do evento expirado: "
                    f"id={event_id}, mensagem={message_id}"
                )
                # Não marca como expirado se não conseguiu remover a mensagem.
                continue
            except discord.HTTPException as erro:
                print(
                    f"Erro ao excluir mensagem do evento expirado "
                    f"id={event_id}: {erro}"
                )
                continue

            # Só marca como expirado depois de remover a mensagem
            # (ou descobrir que ela já não existe).
            try:
                from bot_database import marcar_evento_expirado
                marcar_evento_expirado(event_id)
            except Exception as erro:
                print(
                    f"Mensagem removida, mas não foi possível marcar "
                    f"evento {event_id} como expirado: {erro}"
                )

    except Exception as erro:
        print(f"Erro na verificação automática de eventos: {erro}")


@verificar_eventos_expirados.before_loop
async def antes_de_verificar_eventos():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)

    if not verificar_eventos_expirados.is_running():
        verificar_eventos_expirados.start()

    print(f"Bot conectado como {bot.user}")
    print("Comandos /criarevento e /meuseventos sincronizados.")
    print("Verificação automática de eventos expirados ativada (a cada 5 minutos).")


app = Flask(__name__)

@app.route("/")
def home():
    return "Bot online!"


def iniciar_servidor():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


Thread(target=iniciar_servidor, daemon=True).start()

bot.run(TOKEN)
