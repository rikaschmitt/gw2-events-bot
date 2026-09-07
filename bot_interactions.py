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


