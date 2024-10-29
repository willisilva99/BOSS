import discord
from discord.ext import commands
import os
import asyncpg
import asyncio
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração de intents e prefixo
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="n!", intents=intents)

# URL de conexão com o banco de dados
DATABASE_URL = os.getenv("DATABASE_URL")

# Lista de cogs
cogs = [
    "boss",  # Cog do boss com funcionalidades avançadas
    "rank",  # Cog de ranking dos jogadores
]

async def setup_database():
    """Conecta ao banco de dados e cria as tabelas, se não existirem."""
    try:
        bot.pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
        print("Conexão com o banco de dados estabelecida com sucesso.")
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")

async def load_cogs():
    """Carrega todos os cogs listados."""
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"Cog '{cog}' carregado com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar o cog '{cog}': {e}")

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    await setup_database()  # Configura e conecta o banco de dados
    await load_cogs()       # Carrega os cogs

if __name__ == "__main__":
    asyncio.run(bot.start(os.getenv("TOKEN")))
