import discord
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


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


# ==========================================
# MODAL BASE
# ==========================================

class EventoModalBase(discord.ui.Modal):

    async def enviar_evento(
        self,
        interaction: discord.Interaction,
        tipo: str,
        nome: str,
        data: str,
        horario: str,
        descricao: str = "",
        requisitos: str = "",
        lfg: bool = False
    ):

        data_obj = datetime.strptime(
            data,
            "%Y-%m-%d"
        )

        data_formatada = data_obj.strftime(
            "%d/%m/%Y"
        )

        # --------------------------------------
        # EMBED DO EVENTO
        # --------------------------------------

        embed = discord.Embed(
            title=f"{tipo} • {nome}",
            description=descricao or "Sem descrição."
        )

        embed.add_field(
            name="📅 Data",
            value=data_formatada,
            inline=True
        )

        embed.add_field(
            name="🕐 Horário",
            value=horario,
            inline=True
        )

        if requisitos:

            embed.add_field(
                name="📋 Requisitos",
                value=requisitos,
                inline=False
            )

        embed.add_field(
            name="👤 Organizador",
            value=interaction.user.mention,
            inline=False
        )

        if lfg:

            embed.add_field(
                name="🎮 LFG",
                value="✅ Este evento será listado no LFG.",
                inline=False
            )

        else:

            embed.add_field(
                name="🎮 LFG",
                value="❌ Não será listado no LFG.",
                inline=False
            )

        embed.set_footer(
            text="GW2 Events • Evento criado pela comunidade"
        )

        # --------------------------------------
        # RESPOSTA PRIVADA
        # --------------------------------------

        await interaction.response.send_message(
            "✅ **Evento criado com sucesso!**",
            ephemeral=True
        )

        # --------------------------------------
        # PUBLICAÇÃO
        # --------------------------------------

        from bot_interactions import publicar_evento

        await publicar_evento(
            interaction=interaction,
            embed=embed
        )


# ==========================================
# RAID
# ==========================================

class RaidModal(EventoModalBase):

    def __init__(self):

        super().__init__(
            title="⚔️ Criar evento • Raid"
        )

        # Wing / Boss

        self.wing_boss = discord.ui.TextInput(
            custom_id="raid_wing_boss",
            placeholder="Ex.: Wing 1 / Vale Guardian",
            required=True,
            max_length=100
        )

        # Data

        self.data = discord.ui.Select(
            custom_id="raid_data",
            placeholder="Escolha uma data...",
            options=criar_opcoes_datas()
        )

        # Horário

        self.horario = discord.ui.Select(
            custom_id="raid_horario",
            placeholder="Escolha um horário...",
            options=criar_opcoes_horarios()
        )

        # Requisitos

        self.requisitos = discord.ui.TextInput(
            custom_id="raid_requisitos",
            placeholder="Ex.: DPS, experiência, build específica...",
            required=False,
            max_length=500
        )

        # Descrição

        self.descricao = discord.ui.TextInput(
            custom_id="raid_descricao",
            placeholder="Informações adicionais sobre o evento...",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )

        self.add_item(
            discord.ui.Label(
                text="Wing / Boss",
                component=self.wing_boss
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Data",
                component=self.data
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Horário",
                component=self.horario
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Requisitos",
                component=self.requisitos
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Descrição",
                component=self.descricao
            )
        )

    async def on_submit(self, interaction):

        await self.enviar_evento(
            interaction=interaction,
            tipo="⚔️ RAID",
            nome=self.wing_boss.value,
            data=self.data.values[0],
            horario=self.horario.values[0],
            requisitos=self.requisitos.value,
            descricao=self.descricao.value
        )


# ==========================================
# FRACTAL
# ==========================================

class FractalModal(EventoModalBase):

    def __init__(self):

        super().__init__(
            title="🌀 Criar evento • Fractal"
        )

        # Tier / Fractal

        self.tier_fractal = discord.ui.TextInput(
            custom_id="fractal_nome",
            placeholder="Ex.: T4 / Nightmare",
            required=True,
            max_length=100
        )

        # Data

        self.data = discord.ui.Select(
            custom_id="fractal_data",
            placeholder="Escolha uma data...",
            options=criar_opcoes_datas()
        )

        # Horário

        self.horario = discord.ui.Select(
            custom_id="fractal_horario",
            placeholder="Escolha um horário...",
            options=criar_opcoes_horarios()
        )

        # Requisitos

        self.requisitos = discord.ui.TextInput(
            custom_id="fractal_requisitos",
            placeholder="Ex.: AR 150, DPS, experiência...",
            required=False,
            max_length=500
        )

        # Descrição

        self.descricao = discord.ui.TextInput(
            custom_id="fractal_descricao",
            placeholder="Informações adicionais sobre o evento...",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )

        self.add_item(
            discord.ui.Label(
                text="Tier / Fractal",
                component=self.tier_fractal
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Data",
                component=self.data
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Horário",
                component=self.horario
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Requisitos",
                component=self.requisitos
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Descrição",
                component=self.descricao
            )
        )

    async def on_submit(self, interaction):

        await self.enviar_evento(
            interaction=interaction,
            tipo="🌀 FRACTAL",
            nome=self.tier_fractal.value,
            data=self.data.values[0],
            horario=self.horario.values[0],
            requisitos=self.requisitos.value,
            descricao=self.descricao.value
        )


# ==========================================
# META EVENT
# ==========================================

class MetaModal(EventoModalBase):

    def __init__(self):

        super().__init__(
            title="🐉 Criar evento • Meta"
        )

        # Nome do Meta

        self.nome_meta = discord.ui.TextInput(
            custom_id="meta_nome",
            placeholder="Ex.: Dragonstorm",
            required=True,
            max_length=100
        )

        # Data

        self.data = discord.ui.Select(
            custom_id="meta_data",
            placeholder="Escolha uma data...",
            options=criar_opcoes_datas()
        )

        # Horário

        self.horario = discord.ui.Select(
            custom_id="meta_horario",
            placeholder="Escolha um horário...",
            options=criar_opcoes_horarios()
        )

        # Descrição

        self.descricao = discord.ui.TextInput(
            custom_id="meta_descricao",
            placeholder="Informações adicionais sobre o evento...",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )

        # LFG

        self.lfg = discord.ui.Checkbox(
            custom_id="meta_lfg",
            default=False
        )

        self.add_item(
            discord.ui.Label(
                text="Nome do Meta",
                component=self.nome_meta
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Data",
                component=self.data
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Horário",
                component=self.horario
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Descrição",
                component=self.descricao
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Listar no LFG?",
                description="Marque se o evento será listado no LFG do jogo.",
                component=self.lfg
            )
        )

    async def on_submit(self, interaction):

        await self.enviar_evento(
            interaction=interaction,
            tipo="🐉 META EVENT",
            nome=self.nome_meta.value,
            data=self.data.values[0],
            horario=self.horario.values[0],
            descricao=self.descricao.value,
            lfg=self.lfg.value
        )


# ==========================================
# HERO POINT
# ==========================================

class HeroPointModal(EventoModalBase):

    def __init__(self):

        super().__init__(
            title="🗺️ Criar evento • Hero Point"
        )

        # Expansões

        expansoes = [
            discord.SelectOption(
                label="Heart of Thorns",
                value="Heart of Thorns"
            ),
            discord.SelectOption(
                label="Path of Fire",
                value="Path of Fire"
            ),
            discord.SelectOption(
                label="End of Dragons",
                value="End of Dragons"
            ),
            discord.SelectOption(
                label="Secrets of the Obscure",
                value="Secrets of the Obscure"
            ),
            discord.SelectOption(
                label="Janthir Wilds",
                value="Janthir Wilds"
            ),
            discord.SelectOption(
                label="Visions of Eternity",
                value="Visions of Eternity"
            )
        ]

        self.expansao = discord.ui.Select(
            custom_id="hero_expansao",
            placeholder="Escolha uma expansão...",
            options=expansoes
        )

        # Data

        self.data = discord.ui.Select(
            custom_id="hero_data",
            placeholder="Escolha uma data...",
            options=criar_opcoes_datas()
        )

        # Horário

        self.horario = discord.ui.Select(
            custom_id="hero_horario",
            placeholder="Escolha um horário...",
            options=criar_opcoes_horarios()
        )

        # Descrição

        self.descricao = discord.ui.TextInput(
            custom_id="hero_descricao",
            placeholder="Informações adicionais sobre a run...",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )

        # LFG

        self.lfg = discord.ui.Checkbox(
            custom_id="hero_lfg",
            default=False
        )

        self.add_item(
            discord.ui.Label(
                text="Expansão",
                component=self.expansao
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Data",
                component=self.data
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Horário",
                component=self.horario
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Descrição",
                component=self.descricao
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Listar no LFG?",
                description="Marque se o evento será listado no LFG do jogo.",
                component=self.lfg
            )
        )

    async def on_submit(self, interaction):

        await self.enviar_evento(
            interaction=interaction,
            tipo="🗺️ HERO POINT",
            nome=self.expansao.values[0],
            data=self.data.values[0],
            horario=self.horario.values[0],
            descricao=self.descricao.value,
            lfg=self.lfg.value
        )


# ==========================================
# OUTRO
# ==========================================

class OutroModal(EventoModalBase):

    def __init__(self):

        super().__init__(
            title="✨ Criar evento • Outro"
        )

        # Nome

        self.nome = discord.ui.TextInput(
            custom_id="outro_nome",
            placeholder="Ex.: Achievement Hunt",
            required=True,
            max_length=100
        )

        # Data

        self.data = discord.ui.Select(
            custom_id="outro_data",
            placeholder="Escolha uma data...",
            options=criar_opcoes_datas()
        )

        # Horário

        self.horario = discord.ui.Select(
            custom_id="outro_horario",
            placeholder="Escolha um horário...",
            options=criar_opcoes_horarios()
        )

        # Descrição

        self.descricao = discord.ui.TextInput(
            custom_id="outro_descricao",
            placeholder="Explique o que será feito...",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )

        # LFG

        self.lfg = discord.ui.Checkbox(
            custom_id="outro_lfg",
            default=False
        )

        self.add_item(
            discord.ui.Label(
                text="Nome",
                component=self.nome
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Data",
                component=self.data
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Horário",
                component=self.horario
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Descrição",
                component=self.descricao
            )
        )

        self.add_item(
            discord.ui.Label(
                text="Listar no LFG?",
                description="Marque se o evento será listado no LFG do jogo.",
                component=self.lfg
            )
        )

    async def on_submit(self, interaction):

        await self.enviar_evento(
            interaction=interaction,
            tipo="✨ OUTRO",
            nome=self.nome.value,
            data=self.data.values[0],
            horario=self.horario.values[0],
            descricao=self.descricao.value,
            lfg=self.lfg.value
        )


