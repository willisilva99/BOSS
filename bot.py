import discord
from discord.ext import commands, tasks
import os
import asyncpg
import asyncio
import random
from dotenv import load_dotenv
import traceback  # Importa para obter detalhes completos dos erros

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

# ID do canal para relatórios de erros (defina no .env)
ERROR_CHANNEL_ID = int(os.getenv("ERROR_CHANNEL_ID", 0))

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
        await report_error(f"Erro ao conectar ao banco de dados: {e}")

async def load_cogs():
    # Carrega os cogs
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"Cog {cog} carregado com sucesso.")
        except Exception as e:
            await report_error(f"Erro ao carregar o cog {cog}: {e}")

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
    # Captura e exibe erros de comando, enviando ao canal de erro e ao console
    error_message = f"Ocorreu um erro no comando `{ctx.command}`:\n{error}"
    print(f"Erro detectado: {error_message}")
    await ctx.send(error_message)  # Envia mensagem ao usuário

    # Envia o relatório detalhado ao canal de erro, se configurado
    if ERROR_CHANNEL_ID:
        error_channel = bot.get_channel(ERROR_CHANNEL_ID)
        if error_channel:
            trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
            await error_channel.send(f"**Erro em {ctx.command}:**\n```{trace}```")

@bot.event
async def on_message(message):
    # Ignora mensagens do próprio bot
    if message.author == bot.user:
        return
    # Processa comandos nas mensagens
    await bot.process_commands(message)

async def report_error(error_message):
    # Reporta erros ao console e, se possível, a um canal específico no Discord
    print(error_message)  # Log no console
    if ERROR_CHANNEL_ID:
        error_channel = bot.get_channel(ERROR_CHANNEL_ID)
        if error_channel:
            await error_channel.send(f"**Erro detectado:**\n{error_message}")

async def setup():
    await setup_database()  # Configura o banco de dados
    await load_cogs()       # Carrega os cogs
    await bot.start(os.getenv("TOKEN"))  # Inicia o bot

if __name__ == "__main__":
    asyncio.run(setup())
