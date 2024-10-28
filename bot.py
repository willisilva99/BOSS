import discord
from discord.ext import commands, tasks
import os
import asyncpg
import asyncio
import random
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
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
    "boss",  # Adicionando o cog do boss

]

# Mensagens de status aleatórias
status_messages = [
    "sobrevivendo ao apocalipse",
    "explorando novas bases",
    "caçando zumbis",
    "coletando recursos",
    "protegendo os sobreviventes",
    "negociando embers",
    "construindo alianças",
    "lutando contra hordas",
    "explorando o mapa",
    "realizando missões"
]

async def setup_database():
    # Configura a conexão com o banco de dados e cria as tabelas necessárias
    try:
        bot.pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
        print("Conexão com o banco de dados estabelecida com sucesso.")

        async with bot.pool.acquire() as connection:
            # Criação das tabelas se não existirem
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id BIGINT PRIMARY KEY,
                    wounds INTEGER DEFAULT 0,
                    money INTEGER DEFAULT 1000,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1
                );
            """)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES players(user_id) ON DELETE CASCADE,
                    item TEXT NOT NULL
                );
            """)
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")

async def load_cogs():
    # Carrega os cogs
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"Cog {cog} carregado com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar o cog {cog}: {e}")

@tasks.loop(minutes=10)
async def change_status():
    # Muda o status do bot periodicamente
    new_status = random.choice(status_messages)
    await bot.change_presence(activity=discord.Game(new_status))

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    print("Bot está pronto e todos os cogs foram carregados.")
    change_status.start()  # Inicia a tarefa de status aleatório

@bot.event
async def on_command_error(ctx, error):
    # Captura erros de comando
    await ctx.send(f"Ocorreu um erro: {error}")
    print(f"Erro detectado: {error}")

@bot.event
async def on_message(message):
    # Ignora mensagens do próprio bot
    if message.author == bot.user:
        return
    # Processa comandos nas mensagens
    await bot.process_commands(message)

async def setup():
    await setup_database()  # Configura o banco de dados
    await load_cogs()       # Carrega os cogs
    await bot.start(os.getenv("TOKEN"))  # Inicia o bot

if __name__ == "__main__":
    asyncio.run(setup())
