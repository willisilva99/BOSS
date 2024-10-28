import discord
from discord.ext import commands
import os
import asyncio

# Configuração de intents e prefixo
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="n!", intents=intents)

# Lista de cogs
cogs = ["boss_cog"]  # Cog do boss

async def load_cogs():
    """Carrega os cogs da lista."""
    for cog in cogs:
        try:
            bot.load_extension(f'cogs.{cog}')
            print(f'Cog {cog} carregado com sucesso.')
        except Exception as e:
            print(f'Erro ao carregar o cog {cog}: {e}')

@bot.event
async def on_ready():
    print(f'{bot.user} está online!')

# Função de setup principal
async def setup():
    await load_cogs()  # Carrega os cogs
    await bot.start(os.getenv("TOKEN"))

# Iniciar o bot
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup())
