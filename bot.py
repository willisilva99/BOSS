import discord
from discord.ext import commands
import os
import asyncio

# Configuração de intents e prefixo
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Carrega os cogs
async def load_cogs():
    """Carrega os cogs da pasta cogs."""
    bot.load_extension("cogs.boss")

@bot.event
async def on_ready():
    print(f'{bot.user} está online!')

# Função de setup principal
async def setup():
    await load_cogs()  # Carrega o cog do boss
    await bot.start(os.getenv("TOKEN"))

# Iniciar o bot
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup())
