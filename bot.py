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
    "boss",  # Cog do boss com funcionalidades avançadas
]

# Mensagens de status aleatórias para dar mais imersão ao bot
status_messages = [
    "sobrevivendo ao apocalipse...",
    "explorando novas bases...",
    "caçando zumbis...",
    "coletando recursos...",
    "protegendo os sobreviventes...",
    "negociando embers...",
    "construindo alianças...",
    "lutando contra hordas...",
    "explorando o mapa...",
    "realizando missões..."
]

async def setup_database():
    # Conecta ao banco de dados e cria as tabelas, se não existirem
    try:
        bot.pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
        print("Conexão com o banco de dados estabelecida com sucesso.")

        async with bot.pool.acquire() as connection:
            # Criação das tabelas no banco de dados
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id BIGINT PRIMARY KEY,
                    wounds INTEGER DEFAULT 0,
                    money INTEGER DEFAULT 1000,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    infected BOOLEAN DEFAULT FALSE,
                    damage_debuff BOOLEAN DEFAULT FALSE
                );
            """)

            await connection.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES players(user_id) ON DELETE CASCADE,
                    item TEXT NOT NULL
                );
            """)

            # Tabela para Classes
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS classes (
                    class_id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT
                );
            """)

            # Tabela para Associar Jogadores às Classes
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS player_classes (
                    user_id BIGINT REFERENCES players(user_id) ON DELETE CASCADE,
                    class_id INTEGER REFERENCES classes(class_id) ON DELETE SET NULL,
                    PRIMARY KEY (user_id)
                );
            """)

            # Tabela para Itens da Loja
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS shop_items (
                    item_id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    cost INTEGER NOT NULL,
                    rarity TEXT CHECK (rarity IN ('comum', 'raro', 'épico')) NOT NULL
                );
            """)

            # Tabela para Debuffs (Caso queira gerenciar múltiplos debuffs)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS debuffs (
                    debuff_id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    duration INTEGER NOT NULL  -- duração em segundos
                );
            """)

            # Tabela para Gerenciar Debuffs Aplicados aos Jogadores
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS player_debuffs (
                    user_id BIGINT REFERENCES players(user_id) ON DELETE CASCADE,
                    debuff_id INTEGER REFERENCES debuffs(debuff_id) ON DELETE CASCADE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, debuff_id)
                );
            """)
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")

async def load_cogs():
    # Carrega todos os cogs listados
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"Cog {cog} carregado com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar o cog {cog}: {e}")

@tasks.loop(minutes=10)
async def change_status():
    # Atualiza o status do bot aleatoriamente a cada 10 minutos
    new_status = random.choice(status_messages)
    await bot.change_presence(activity=discord.Game(new_status))

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    print("Bot está pronto e todos os cogs foram carregados.")
    change_status.start()  # Inicia a tarefa de mudança de status

@bot.event
async def on_command_error(ctx, error):
    # Captura e exibe erros de comando
    embed = discord.Embed(
        title="⚠️ Erro de Comando",
        description=f"Ocorreu um erro ao executar `{ctx.command}`:\n{error}",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)
    print(f"Erro detectado: {error}")

@bot.event
async def on_message(message):
    # Ignora mensagens do próprio bot e processa comandos nas mensagens
    if message.author == bot.user:
        return
    await bot.process_commands(message)

async def setup():
    await setup_database()  # Configura e conecta o banco de dados
    await load_cogs()       # Carrega os cogs
    await bot.start(os.getenv("TOKEN"))  # Inicia o bot com o token do .env

if __name__ == "__main__":
    asyncio.run(setup())
