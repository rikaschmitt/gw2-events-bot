import discord

from bot_modals import (
    RaidModal,
    FractalModal,
    MetaModal,
    HeroPointModal,
    OutroModal,
)


# ==========================================
# PAINEL DE CRIAÇÃO DE EVENTOS
# ==========================================

class EventoView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Raid",
        emoji="⚔️",
        style=discord.ButtonStyle.primary,
        custom_id="evento_raid"
    )
    async def raid(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            RaidModal()
        )

    @discord.ui.button(
        label="Fractal",
        emoji="🌀",
        style=discord.ButtonStyle.primary,
        custom_id="evento_fractal"
    )
    async def fractal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            FractalModal()
        )

    @discord.ui.button(
        label="Meta",
        emoji="🐉",
        style=discord.ButtonStyle.primary,
        custom_id="evento_meta"
    )
    async def meta(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            MetaModal()
        )

    @discord.ui.button(
        label="Hero Point",
        emoji="🗺️",
        style=discord.ButtonStyle.primary,
        custom_id="evento_hero_point"
    )
    async def hero_point(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            HeroPointModal()
        )

    @discord.ui.button(
        label="Outro",
        emoji="✨",
        style=discord.ButtonStyle.secondary,
        custom_id="evento_outro"
    )
    async def outro(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            OutroModal()
        )




# ============================================================
# PUBLICAÇÃO DOS EVENTOS
# ============================================================

EVENTS_CHANNEL_ID = 1546643357718020148

# Armazenamento temporário.
# Será substituído por banco de dados em uma próxima etapa.
eventos = {}


async def publicar_evento(
    interaction: discord.Interaction,
    embed: discord.Embed
):
    """Publica o evento no canal #eventos."""

    if interaction.guild is None:
        raise RuntimeError(
            "O evento precisa ser criado dentro de um servidor."
        )

    channel = interaction.guild.get_channel(EVENTS_CHANNEL_ID)

    if channel is None:
        raise RuntimeError(
            f"O canal #eventos ({EVENTS_CHANNEL_ID}) não foi encontrado."
        )

    message = await channel.send(
        embed=embed
    )

    evento_id = message.id

    eventos[evento_id] = {
        "participantes": set(),
        "interessados": set(),
    }

    await message.edit(
        view=EventoParticipacaoView(evento_id)
    )


# ============================================================
# BOTÕES DE PARTICIPAÇÃO
# ============================================================

class EventoParticipacaoView(discord.ui.View):

    def __init__(self, evento_id):
        super().__init__(timeout=None)
        self.evento_id = evento_id

    def obter_evento(self):
        return eventos.setdefault(
            self.evento_id,
            {
                "participantes": set(),
                "interessados": set(),
            }
        )

    @discord.ui.button(
        label="EU VOU • 0",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="participar_evento"
    )
    async def eu_vou(self, interaction, button):

        evento = self.obter_evento()
        user_id = interaction.user.id

        evento["interessados"].discard(user_id)
        evento["participantes"].add(user_id)

        await interaction.response.send_message(
            "🟢 Você está participando deste evento!",
            ephemeral=True
        )

        await self.atualizar_botoes(interaction)

    @discord.ui.button(
        label="TENHO INTERESSE • 0",
        emoji="👀",
        style=discord.ButtonStyle.primary,
        custom_id="interesse_evento"
    )
    async def tenho_interesse(self, interaction, button):

        evento = self.obter_evento()
        user_id = interaction.user.id

        evento["participantes"].discard(user_id)
        evento["interessados"].add(user_id)

        await interaction.response.send_message(
            "👀 Você demonstrou interesse neste evento!",
            ephemeral=True
        )

        await self.atualizar_botoes(interaction)

    @discord.ui.button(
        label="SAIR",
        emoji="❌",
        style=discord.ButtonStyle.secondary,
        custom_id="sair_evento"
    )
    async def sair(self, interaction, button):

        evento = self.obter_evento()
        user_id = interaction.user.id

        evento["participantes"].discard(user_id)
        evento["interessados"].discard(user_id)

        await interaction.response.send_message(
            "❌ Você saiu deste evento.",
            ephemeral=True
        )

        await self.atualizar_botoes(interaction)

    async def atualizar_botoes(self, interaction):

        evento = self.obter_evento()

        participantes = len(evento["participantes"])
        interessados = len(evento["interessados"])

        self.children[0].label = f"EU VOU • {participantes}"
        self.children[1].label = f"TENHO INTERESSE • {interessados}"

        await interaction.message.edit(
            view=self
        )
