import os
import discord
from discord.ext import commands

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")


@bot.tree.command(name="teste", description="Testa se o bot está funcionando")
async def teste(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🐉 **Bot funcionando!**\n"
        "O GW2 Events está online."
    )


TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("A variável DISCORD_TOKEN não foi configurada.")

bot.run(TOKEN)
