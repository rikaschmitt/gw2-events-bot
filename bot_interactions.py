import discord

from bot_modals import (
    RaidModal,
    FractalModal,
    MetaModal,
    HeroPointModal,
    OutroModal,
)

from bot_database import (
    criar_evento,
    definir_participacao,
    remover_participacao,
    buscar_contagem_participacao,
    buscar_evento_por_mensagem,
)


EVENTS_CHANNEL_ID = 1546643357718020148


async def publicar_evento(interaction, embed):
    """Publica o evento no #eventos e grava o evento no PostgreSQL."""

    if interaction.guild is None:
        raise RuntimeError(
            "O evento precisa ser criado dentro de um servidor."
        )

    channel = interaction.guild.get_channel(EVENTS_CHANNEL_ID)

    if channel is None:
        raise RuntimeError(
            f"O canal #eventos ({EVENTS_CHANNEL_ID}) não foi encontrado."
        )

    message = await channel.send(embed=embed)

    # Recupera os dados básicos do embed para persistência.
    campos = {field.name: field.value for field in embed.fields}

    tipo_nome = embed.title.split(" • ", 1)
    event_type = tipo_nome[0] if tipo_nome else "OUTRO"
    name = tipo_nome[1] if len(tipo_nome) > 1 else embed.title

    event_date = campos.get("📅 Data")
    event_time = campos.get("🕐 Horário")
    organizer = interaction.user

    # O banco usa a data ISO. O embed usa DD/MM/AAAA.
    from datetime import datetime

    event_date_db = datetime.strptime(
        event_date,
        "%d/%m/%Y"
    ).date()

    event_time_db = datetime.strptime(
        event_time,
        "%H:%M"
    ).time()

    description = campos.get("📝 Descrição") or embed.description or ""
    requirements = campos.get("📋 Requisitos")

    lfg_value = campos.get("📢 LFG", "")
    lfg = lfg_value.startswith("✅")

    await criar_evento(
        discord_message_id=message.id,
        discord_channel_id=channel.id,
        discord_guild_id=interaction.guild.id,
        event_type=event_type,
        name=name,
        event_date=event_date_db,
        event_time=event_time_db,
        description=description,
        requirements=requirements,
        lfg=lfg,
        organizer_discord_id=organizer.id,
        organizer_name=organizer.display_name,
    )

    await message.edit(
        view=EventoParticipacaoView(message.id)
    )


class EventoView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Raid",
        emoji="⚔️",
        style=discord.ButtonStyle.primary,
        custom_id="evento_raid"
    )
    async def raid(self, interaction, button):
        await interaction.response.send_modal(RaidModal())

    @discord.ui.button(
        label="Fractal",
        emoji="🌀",
        style=discord.ButtonStyle.primary,
        custom_id="evento_fractal"
    )
    async def fractal(self, interaction, button):
        await interaction.response.send_modal(FractalModal())

    @discord.ui.button(
        label="Meta",
        emoji="🐉",
        style=discord.ButtonStyle.primary,
        custom_id="evento_meta"
    )
    async def meta(self, interaction, button):
        await interaction.response.send_modal(MetaModal())

    @discord.ui.button(
        label="Hero Point",
        emoji="🗺️",
        style=discord.ButtonStyle.primary,
        custom_id="evento_hero_point"
    )
    async def hero_point(self, interaction, button):
        await interaction.response.send_modal(HeroPointModal())

    @discord.ui.button(
        label="Outro",
        emoji="✨",
        style=discord.ButtonStyle.secondary,
        custom_id="evento_outro"
    )
    async def outro(self, interaction, button):
        await interaction.response.send_modal(OutroModal())


class EventoParticipacaoView(discord.ui.View):

    def __init__(self, evento_id):
        super().__init__(timeout=None)
        self.evento_id = evento_id

    async def carregar_evento(self):
        return await buscar_evento_por_mensagem(self.evento_id)

    @discord.ui.button(
        label="EU VOU • 0",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="participar_evento"
    )
    async def eu_vou(self, interaction, button):

        evento = await self.carregar_evento()

        if evento is None:
            await interaction.response.send_message(
                "⚠️ Não encontrei este evento no banco de dados.",
                ephemeral=True
            )
            return

        await definir_participacao(
            event_id=evento["id"],
            discord_user_id=interaction.user.id,
            discord_username=interaction.user.display_name,
            participation_type="participant",
        )

        await interaction.response.send_message(
            "🟢 Você está participando deste evento!",
            ephemeral=True
        )

        await self.atualizar_botoes(interaction, evento["id"])

    @discord.ui.button(
        label="TENHO INTERESSE • 0",
        emoji="👀",
        style=discord.ButtonStyle.primary,
        custom_id="interesse_evento"
    )
    async def tenho_interesse(self, interaction, button):

        evento = await self.carregar_evento()

        if evento is None:
            await interaction.response.send_message(
                "⚠️ Não encontrei este evento no banco de dados.",
                ephemeral=True
            )
            return

        await definir_participacao(
            event_id=evento["id"],
            discord_user_id=interaction.user.id,
            discord_username=interaction.user.display_name,
            participation_type="interested",
        )

        await interaction.response.send_message(
            "👀 Você demonstrou interesse neste evento!",
            ephemeral=True
        )

        await self.atualizar_botoes(interaction, evento["id"])

    @discord.ui.button(
        label="SAIR",
        emoji="❌",
        style=discord.ButtonStyle.secondary,
        custom_id="sair_evento"
    )
    async def sair(self, interaction, button):

        evento = await self.carregar_evento()

        if evento is None:
            await interaction.response.send_message(
                "⚠️ Não encontrei este evento no banco de dados.",
                ephemeral=True
            )
            return

        await remover_participacao(
            event_id=evento["id"],
            discord_user_id=interaction.user.id,
        )

        await interaction.response.send_message(
            "❌ Você saiu deste evento.",
            ephemeral=True
        )

        await self.atualizar_botoes(interaction, evento["id"])

    async def atualizar_botoes(self, interaction, event_id):

        contagem = await buscar_contagem_participacao(event_id)

        self.children[0].label = (
            f"EU VOU • {contagem['participantes']}"
        )

        self.children[1].label = (
            f"TENHO INTERESSE • {contagem['interessados']}"
        )

        await interaction.message.edit(view=self)


def registrar_views_persistentes(bot):
    bot.add_view(EventoView())
