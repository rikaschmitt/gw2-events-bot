import os
import asyncio
import base64
import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from threading import Thread

import discord
from discord import app_commands
from discord.ext import commands, tasks
from flask import Flask

from bot_database import (
    buscar_gw2_id,
    salvar_gw2_id,
    salvar_evento,
    buscar_meus_eventos,
    excluir_evento,
    buscar_eventos_expirados,
    buscar_eventos_para_lembrete,
    marcar_lembrete_enviado,
    buscar_eventos_ativos,
)

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 833150116582916096
LFG_CHANNEL_ID = 1546643357718020148
TIMEZONE = ZoneInfo("America/Sao_Paulo")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# ---------------------------------------------------------------------------
# Sincronização pública dos eventos com o GitHub
# ---------------------------------------------------------------------------

def sincronizar_json_github_sync():
    """
    Gera data/events.json a partir dos eventos ativos do Supabase e publica
    o arquivo no repositório GitHub configurado nas variáveis de ambiente.

    A função é síncrona e deve ser executada fora do event loop do Discord.
    """

    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")
    path = os.getenv("GITHUB_JSON_PATH", "data/events.json")

    if not token or not repo:
        print("GitHub: GITHUB_TOKEN ou GITHUB_REPO não configurado.")
        return False

    try:
        eventos = buscar_eventos_ativos()
        eventos_publicos = []

        for evento in eventos:
            guild_id = evento["discord_guild_id"]
            channel_id = evento["discord_channel_id"]
            message_id = evento["discord_message_id"]

            eventos_publicos.append({
                "id": evento["id"],
                "title": evento["titulo"],
                "date": evento["event_date"].isoformat(),
                "time": evento["event_time"].strftime("%H:%M"),
                "description": evento["descricao"],
                "gw2_id": evento["gw2_id"],
                "organizer": evento["organizer_name"],
                "discord_url": (
                    f"https://discord.com/channels/"
                    f"{guild_id}/{channel_id}/{message_id}"
                ),
            })

        api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Shekyra-GW2-Bot",
        }

        sha = None
        eventos_atuais = None

        request_get = urllib.request.Request(
            api_url,
            headers=headers,
            method="GET",
        )

        try:
            with urllib.request.urlopen(request_get, timeout=20) as response:
                dados_atuais = json.loads(response.read().decode("utf-8"))
                sha = dados_atuais.get("sha")

                conteudo_codificado = dados_atuais.get("content", "")
                if conteudo_codificado:
                    conteudo_atual = base64.b64decode(
                        conteudo_codificado.replace("\n", "")
                    ).decode("utf-8")
                    try:
                        eventos_atuais = json.loads(
                            conteudo_atual
                        ).get("events")
                    except (json.JSONDecodeError, TypeError):
                        eventos_atuais = None

        except urllib.error.HTTPError as erro:
            if erro.code != 404:
                raise

        if eventos_atuais == eventos_publicos:
            print("GitHub: events.json já está atualizado. Nenhum commit necessário.")
            return True

        payload = {
            "version": 1,
            "updated_at": datetime.now(TIMEZONE).isoformat(timespec="seconds"),
            "timezone": "America/Sao_Paulo",
            "events": eventos_publicos,
        }

        novo_conteudo = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ) + "\n"

        body = {
            "message": "Atualiza eventos do LFG",
            "content": base64.b64encode(
                novo_conteudo.encode("utf-8")
            ).decode("ascii"),
        }

        if sha:
            body["sha"] = sha

        request_put = urllib.request.Request(
            api_url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                **headers,
                "Content-Type": "application/json",
            },
            method="PUT",
        )

        with urllib.request.urlopen(request_put, timeout=20) as response:
            resultado = json.loads(response.read().decode("utf-8"))

        commit_sha = resultado.get("commit", {}).get("sha", "desconhecido")
        print(
            f"GitHub: events.json atualizado com sucesso. "
            f"Eventos ativos={len(eventos_publicos)}, commit={commit_sha}"
        )
        return True

    except Exception as erro:
        print(f"GitHub: erro ao sincronizar events.json: {erro}")
        return False


async def sincronizar_json_github():
    """Executa a sincronização do GitHub sem bloquear o event loop do Discord."""
    return await asyncio.to_thread(sincronizar_json_github_sync)


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

        await interaction.response.defer(ephemeral=True)
        evento_publicado = None

        try:
            guild = interaction.guild
            if guild is None:
                raise RuntimeError("A interação não pertence a um servidor Discord.")

            channel = guild.get_channel(LFG_CHANNEL_ID)
            if channel is None:
                raise RuntimeError(
                    f"Canal #lfg não encontrado. LFG_CHANNEL_ID={LFG_CHANNEL_ID}"
                )

            data_selecionada = self.data_select.values[0]
            event_date = datetime.strptime(
                data_selecionada, "%d/%m/%Y"
            ).date()
            event_time = datetime.strptime(
                self.horario.value.strip(), "%H:%M"
            ).time()

            gw2_id = self.gw2_id.value.strip()
            titulo = self.titulo.value.strip()
            descricao = self.descricao.value.strip()

            if not gw2_id:
                raise ValueError("O ID do GW2 não pode ficar vazio.")
            if not titulo:
                raise ValueError("O título não pode ficar vazio.")
            if not descricao:
                raise ValueError("A descrição não pode ficar vazia.")

            salvar_gw2_id(
                discord_user_id=interaction.user.id,
                discord_username=interaction.user.display_name,
                gw2_id=gw2_id,
            )

            descricao_formatada = descricao.replace("\n", "\n> ")

            embed = discord.Embed(
                description=(
                    f"# {titulo}\n"
                    f"📅 **{data_selecionada}**\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0"
                    f"🕐 **{event_time.strftime('%H:%M')}**\n\n"
                    f"> {descricao_formatada}\n\n"
                    f"**Para entrar no squad:** `/sqjoin {gw2_id}`"
                ),
                color=discord.Color.blue()
            )

            embed.set_author(
                name="Novo Evento LFG",
                url=f"https://discord.com/channels/{GUILD_ID}/{LFG_CHANNEL_ID}"
            )
            embed.set_footer(
                text="Ficou interessado? Reaja com ✅ nesta mensagem."
            )

            evento_publicado = await channel.send(embed=embed)
            await evento_publicado.add_reaction("✅")

            event_id = salvar_evento(
                discord_message_id=evento_publicado.id,
                discord_channel_id=channel.id,
                discord_guild_id=guild.id,
                titulo=titulo,
                gw2_id=gw2_id,
                event_date=event_date,
                event_time=event_time,
                descricao=descricao,
                organizer_discord_id=interaction.user.id,
                organizer_name=interaction.user.display_name,
            )

            print(
                f"Evento LFG salvo no banco: "
                f"id={event_id}, mensagem={evento_publicado.id}"
            )

            await sincronizar_json_github()

            try:
                confirmacao = discord.Embed(
                    description=(
                        f"✅ Evento **{titulo}** "
                        f"criado com sucesso no canal #lfg"
                    ),
                    color=discord.Color.green()
                )
                await interaction.user.send(embed=confirmacao)
            except discord.Forbidden:
                print(
                    f"Não foi possível enviar DM de confirmação "
                    f"para {interaction.user.id}."
                )

            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass

        except discord.Forbidden as erro:
            print(f"Erro de permissão ao criar evento: {erro}")
            try:
                await interaction.user.send(
                    embed=discord.Embed(
                        description="❌ Não tenho permissão para publicar no #lfg.",
                        color=discord.Color.red()
                    )
                )
            except discord.Forbidden:
                pass
            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass

        except discord.HTTPException as erro:
            print(f"Erro HTTP do Discord ao criar evento: {erro}")
            try:
                await interaction.user.send(
                    embed=discord.Embed(
                        description="❌ Ocorreu um erro no Discord ao publicar o evento.",
                        color=discord.Color.red()
                    )
                )
            except discord.Forbidden:
                pass
            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass

        except (ValueError, TypeError) as erro:
            print(f"Dados inválidos ao criar evento: {erro}")
            try:
                await interaction.user.send(
                    embed=discord.Embed(
                        description="❌ A data ou o horário do evento está em um formato inválido.",
                        color=discord.Color.red()
                    )
                )
            except discord.Forbidden:
                pass
            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass

        except Exception as erro:
            import traceback
            print("========== ERRO AO CRIAR EVENTO ==========")
            traceback.print_exc()
            print("===========================================")

            # Evita deixar uma mensagem no #lfg que não esteja registrada no banco.
            if evento_publicado is not None:
                try:
                    await evento_publicado.delete()
                    print(
                        f"Mensagem órfã removida após falha no cadastro: "
                        f"{evento_publicado.id}"
                    )
                except (
                    discord.Forbidden,
                    discord.NotFound,
                    discord.HTTPException
                ) as erro_delete:
                    print(
                        f"Não foi possível remover mensagem órfã "
                        f"{evento_publicado.id}: {erro_delete}"
                    )

            try:
                await interaction.user.send(
                    embed=discord.Embed(
                        description=(
                            "❌ Não foi possível criar o evento. "
                            "Verifique o log do bot para identificar o erro."
                        ),
                        color=discord.Color.red()
                    )
                )
            except discord.Forbidden:
                pass

            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass


@bot.tree.command(
    name="criarevento",
    description="Cria um novo evento para o canal LFG."
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def criar_evento(interaction: discord.Interaction):
    try:
        gw2_id_salvo = buscar_gw2_id(interaction.user.id)

        await interaction.response.send_modal(
            CriarEventoModal(gw2_id_salvo=gw2_id_salvo)
        )

    except Exception as erro:
        import traceback
        print("========== ERRO AO ABRIR /CRIAREVENTO ==========")
        traceback.print_exc()
        print("=================================================")

        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Não foi possível abrir o formulário de criação de evento.",
                ephemeral=True
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
            try:
                confirmacao = discord.Embed(
                    description="❌ Você não pode excluir os eventos de outra pessoa.",
                    color=discord.Color.red()
                )
                await interaction.user.send(embed=confirmacao)
            except discord.Forbidden:
                pass
            return

        try:
            # Primeiro marca como inativo no banco.
            excluido = excluir_evento(
                evento_id=self.evento_id,
                organizer_discord_id=self.user_id
            )

            if not excluido:
                try:
                    confirmacao = discord.Embed(
                        description="❌ Esse evento não está mais disponível para exclusão.",
                        color=discord.Color.red()
                    )
                    await interaction.user.send(embed=confirmacao)
                except discord.Forbidden:
                    pass
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

            # Confirmação enviada exclusivamente por DM, no mesmo
            # padrão visual do /meuseventos.
            try:
                confirmacao = discord.Embed(
                    description=(
                        f"🗑️ Evento **{self.titulo}** "
                        f"foi excluído com sucesso!"
                    ),
                    color=discord.Color.red()
                )
                await interaction.user.send(embed=confirmacao)
            except discord.Forbidden:
                print(
                    f"Não foi possível enviar DM de confirmação de exclusão "
                    f"para {interaction.user.id}."
                )

            # Atualiza o arquivo público depois da exclusão.
            await sincronizar_json_github()

            # Desabilita todos os botões desta lista depois da exclusão.
            for item in self.view.children:
                item.disabled = True

            try:
                await interaction.message.edit(view=self.view)
            except discord.HTTPException:
                pass

        except Exception as erro:
            print(f"Erro ao excluir evento {self.evento_id}: {erro}")

            try:
                confirmacao = discord.Embed(
                    description="❌ Não foi possível excluir o evento.",
                    color=discord.Color.red()
                )
                await interaction.user.send(embed=confirmacao)
            except discord.Forbidden:
                pass


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
                embed=discord.Embed(
                    description="❌ Não foi possível consultar seus eventos.",
                    color=discord.Color.red()
                )
            )
        except discord.Forbidden:
            pass
        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
            pass
        return

    if not eventos:
        print(
            f"/meuseventos: nenhum evento futuro encontrado para "
            f"discord_user_id={interaction.user.id}"
        )
        try:
            await interaction.user.send(
                embed=discord.Embed(
                    description="📅 Você não tem eventos futuros ativos.",
                    color=discord.Color.blue()
                )
            )
        except discord.Forbidden:
            pass
        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
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

        # Remove completamente o "Shekyra está pensando..." do canal.
        # A resposta da interação foi usada apenas para dar tempo ao bot
        # de processar o comando; ela não precisa permanecer visível.
        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
            pass

    except discord.Forbidden:
        print(
            f"Não foi possível enviar DM para {interaction.user.id}. "
            "Mensagens diretas podem estar bloqueadas."
        )
        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
            pass


@tasks.loop(minutes=5)
async def verificar_lembretes_eventos():
    """
    A cada 5 minutos, verifica eventos que estão a até 15 minutos de começar.
    Para cada evento, busca as reações ✅ no #lfg e envia uma DM para cada
    participante que reagiu. Cada evento recebe o lembrete apenas uma vez.
    """
    try:
        eventos = buscar_eventos_para_lembrete()

        if not eventos:
            return

        channel = bot.get_channel(LFG_CHANNEL_ID)

        if channel is None:
            print("Lembretes: canal #lfg não encontrado.")
            return

        for evento in eventos:
            event_id = evento["id"]
            message_id = evento["discord_message_id"]
            titulo = evento["titulo"]
            gw2_id = evento["gw2_id"]
            event_date = evento["event_date"]
            event_time = evento["event_time"]

            try:
                mensagem = await channel.fetch_message(message_id)
            except discord.NotFound:
                print(
                    f"Lembrete ignorado: mensagem não existe mais. "
                    f"id={event_id}, mensagem={message_id}"
                )
                # Se a mensagem já não existe, não há participantes para avisar.
                marcar_lembrete_enviado(event_id)
                continue
            except discord.Forbidden:
                print(
                    f"Sem permissão para consultar mensagem do evento "
                    f"id={event_id}, mensagem={message_id}."
                )
                continue
            except discord.HTTPException as erro:
                print(
                    f"Erro ao consultar mensagem do evento "
                    f"id={event_id}: {erro}"
                )
                continue

            participantes = set()

            for reaction in mensagem.reactions:
                if str(reaction.emoji) != "✅":
                    continue

                try:
                    async for usuario in reaction.users():
                        if usuario.bot:
                            continue
                        participantes.add(usuario)
                except discord.HTTPException as erro:
                    print(
                        f"Erro ao consultar reações do evento "
                        f"id={event_id}: {erro}"
                    )

            data = event_date.strftime("%d/%m/%Y")
            horario = event_time.strftime("%H:%M")
            link_evento = (
                f"https://discord.com/channels/"
                f"{GUILD_ID}/{LFG_CHANNEL_ID}/{message_id}"
            )

            for usuario in participantes:
                try:
                    lembrete = discord.Embed(
                        description=(
                            f"# {titulo}\n"
                            f"📅 **{data}**\u00A0\u00A0\u00A0\u00A0"
                            f"🕐 **{horario}**\n\n"
                            f"**Entre no squad usando:** "
                            f"`/sqjoin {gw2_id}`"
                        ),
                        color=discord.Color.gold()
                    )

                    lembrete.set_author(
                        name="Lembrete de evento",
                        url=link_evento
                    )

                    await usuario.send(embed=lembrete)

                    print(
                        f"Lembrete enviado: evento={event_id}, "
                        f"usuario={usuario.id}, titulo={titulo}"
                    )

                except discord.Forbidden:
                    print(
                        f"Não foi possível enviar DM para {usuario.id} "
                        f"no lembrete do evento {event_id}."
                    )
                except discord.HTTPException as erro:
                    print(
                        f"Erro ao enviar lembrete para {usuario.id} "
                        f"no evento {event_id}: {erro}"
                    )

            # Mesmo que algum usuário esteja com DM bloqueada, o evento é
            # marcado como processado para não ficar reenviando aos demais.
            marcar_lembrete_enviado(event_id)

    except Exception as erro:
        print(f"Erro na verificação de lembretes: {erro}")


@verificar_lembretes_eventos.before_loop
async def antes_de_verificar_lembretes():
    await bot.wait_until_ready()


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

        houve_expiracao = False

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
                houve_expiracao = True
            except Exception as erro:
                print(
                    f"Mensagem removida, mas não foi possível marcar "
                    f"evento {event_id} como expirado: {erro}"
                )

        # Uma única atualização do JSON para todos os eventos expirados
        # processados nesta execução.
        if houve_expiracao:
            await sincronizar_json_github()

    except Exception as erro:
        print(f"Erro na verificação automática de eventos: {erro}")


@verificar_eventos_expirados.before_loop
async def antes_de_verificar_eventos():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)

    if not verificar_lembretes_eventos.is_running():
        verificar_lembretes_eventos.start()

    if not verificar_eventos_expirados.is_running():
        verificar_eventos_expirados.start()

    # Garante que o JSON público esteja sincronizado mesmo após um restart.
    await sincronizar_json_github()

    print(f"Bot conectado como {bot.user}")
    print("Comandos /criarevento e /meuseventos sincronizados.")
    print("Verificação automática de lembretes ativada (a cada 5 minutos).")
    print("Verificação automática de eventos expirados ativada (a cada 5 minutos).")


app = Flask(__name__)

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot online!"


@app.route("/terms")
def terms():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Termos de Serviço — Shekyra</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 40px auto;
                padding: 0 20px;
                line-height: 1.6;
                color: #222;
            }
            h1 {
                margin-bottom: 5px;
            }
            h2 {
                margin-top: 30px;
            }
            .date {
                color: #666;
            }
        </style>
    </head>
    <body>

        <h1>Termos de Serviço — Shekyra</h1>
        <p class="date"><strong>Última atualização:</strong> 10 de setembro de 2026</p>

        <h2>1. Sobre a Shekyra</h2>
        <p>
            A Shekyra é um bot desenvolvido para a comunidade
            Sociedade do Dragão [BR], voltado à organização e
            gerenciamento de eventos de Guild Wars 2 dentro do Discord.
        </p>

        <h2>2. Uso do serviço</h2>
        <p>
            A Shekyra deve ser utilizada de maneira responsável e de
            acordo com as regras do servidor Discord da Sociedade do Dragão [BR].
        </p>

        <p>Não é permitido utilizar a Shekyra para:</p>

        <ul>
            <li>Praticar assédio, ameaças ou discriminação;</li>
            <li>Enviar conteúdo ilegal ou malicioso;</li>
            <li>Criar eventos com o objetivo de prejudicar outros usuários;</li>
            <li>Utilizar o bot para spam ou abuso de suas funcionalidades;</li>
            <li>Tentar explorar, interromper ou comprometer o funcionamento da Shekyra.</li>
        </ul>

        <h2>3. Conteúdo enviado pelos usuários</h2>
        <p>
            Os usuários são responsáveis pelas informações e conteúdos
            inseridos ao criar eventos.
        </p>

        <p>
            A administração da Sociedade do Dragão [BR] poderá remover
            eventos ou restringir o acesso ao bot quando necessário para
            manter a organização e segurança da comunidade.
        </p>

        <h2>4. Disponibilidade</h2>
        <p>
            A Shekyra é um projeto comunitário e pode sofrer interrupções,
            falhas, manutenção ou indisponibilidade sem aviso prévio.
        </p>

        <h2>5. Discord e Guild Wars 2</h2>
        <p>
            A Shekyra funciona através da plataforma Discord e não é um
            produto oficial da ArenaNet ou da NCSoft.
        </p>

        <p>
            Guild Wars 2 e suas respectivas marcas pertencem aos seus
            respectivos proprietários.
        </p>

        <h2>6. Alterações nos termos</h2>
        <p>
            Estes Termos de Serviço podem ser atualizados ou modificados
            quando necessário. A versão mais recente estará sempre
            disponível nesta página.
        </p>

        <h2>7. Encerramento do serviço</h2>
        <p>
            A Sociedade do Dragão [BR] poderá interromper, modificar ou
            encerrar a Shekyra a qualquer momento.
        </p>

        <h2>8. Contato</h2>
        <p>
            Para dúvidas, sugestões ou problemas relacionados à Shekyra,
            entre em contato com Brócolis da Sociedade do Dragão [BR]
            através do servidor oficial da comunidade.
        </p>

        <hr>

        <p>© 2026 Sociedade do Dragão [BR].</p>

    </body>
    </html>
    """


@app.route("/privacy")
def privacy():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Política de Privacidade — Shekyra</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 40px auto;
                padding: 0 20px;
                line-height: 1.6;
                color: #222;
            }
            h1 {
                margin-bottom: 5px;
            }
            h2 {
                margin-top: 30px;
            }
            .date {
                color: #666;
            }
        </style>
    </head>
    <body>

        <h1>Política de Privacidade — Shekyra</h1>
        <p class="date"><strong>Última atualização:</strong> 10 de setembro de 2026</p>

        <h2>1. Informações coletadas</h2>
        <p>
            Ao utilizar determinadas funcionalidades da Shekyra, podemos
            armazenar:
        </p>

        <ul>
            <li>ID do usuário no Discord;</li>
            <li>Nome de usuário ou nome de exibição no Discord;</li>
            <li>ID do Guild Wars 2 informado pelo próprio usuário;</li>
            <li>Informações dos eventos criados pelo usuário;</li>
            <li>Identificação da mensagem correspondente ao evento no Discord.</li>
        </ul>

        <h2>2. Como as informações são utilizadas</h2>
        <p>
            As informações são utilizadas exclusivamente para o funcionamento
            das funcionalidades da Shekyra, incluindo criação e gerenciamento
            de eventos, consulta de eventos, exclusão de eventos e envio de
            lembretes relacionados aos eventos.
        </p>

        <h2>3. Mensagens privadas</h2>
        <p>
            Quando um usuário demonstra interesse em um evento através da
            reação utilizada no LFG, a Shekyra poderá enviar uma mensagem
            direta no Discord para lembrar o usuário sobre o evento.
        </p>

        <h2>4. Compartilhamento de informações</h2>
        <p>
            A Shekyra não vende, aluga ou comercializa informações pessoais
            dos usuários.
        </p>

        <p>
            Para funcionar, a Shekyra utiliza serviços de terceiros,
            incluindo Discord, Supabase e Render.
        </p>

        <h2>5. Armazenamento e segurança</h2>
        <p>
            As informações são armazenadas em banco de dados utilizado pela
            Shekyra. São adotadas medidas razoáveis para proteger essas
            informações contra acesso, alteração ou divulgação não autorizada.
        </p>

        <h2>6. Retenção das informações</h2>
        <p>
            As informações são mantidas enquanto forem necessárias para o
            funcionamento da Shekyra e de suas funcionalidades.
        </p>

        <p>
            Eventos excluídos deixam de ser considerados eventos ativos,
            embora algumas informações possam permanecer armazenadas por
            questões técnicas ou de integridade do banco de dados.
        </p>

        <h2>7. Controle e exclusão</h2>
        <p>
            O usuário pode solicitar esclarecimentos sobre as informações
            associadas ao seu uso da Shekyra ou solicitar sua exclusão.
        </p>

        <p>
            Solicitações podem ser encaminhadas à administração da
            Sociedade do Dragão [BR] através do servidor oficial da comunidade.
        </p>

        <h2>8. Alterações nesta política</h2>
        <p>
            Esta Política de Privacidade poderá ser atualizada quando
            necessário. A versão mais recente estará sempre disponível
            nesta página.
        </p>

        <h2>9. Contato</h2>
        <p>
            Para dúvidas ou solicitações relacionadas à privacidade,
            entre em contato com Brócolis da Sociedade do Dragão [BR].
        </p>

        <hr>

        <p>© 2026 Sociedade do Dragão [BR].</p>

    </body>
    </html>
    """


def iniciar_servidor():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


Thread(target=iniciar_servidor, daemon=True).start()

bot.run(TOKEN)
