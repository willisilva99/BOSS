# bot.py

import discord
from discord.ext import commands, tasks
import os
import asyncio
import asyncpg
from dotenv import load_dotenv
import random

# Carrega variáveis de ambiente do arquivo .env (se estiver usando localmente)
load_dotenv()

# Configuração de intents e prefixo
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Lista de cogs para carregar
cogs = [
    "boss",  # Adicionando o boss cog
]

# Conexão com o banco de dados
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Erro: DATABASE_URL não está definida.")
    exit(1)
else:
    print("DATABASE_URL está definida.")

async def setup_database():
    """Configura a conexão com o banco de dados e cria as tabelas necessárias."""
    try:
        bot.pool = await asyncpg.create_pool(DATABASE_URL)
        print("Banco de dados conectado com sucesso.")
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        exit(1)

    async with bot.pool.acquire() as connection:
        try:
            # Cria a tabela 'players' se não existir
            await connection.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id BIGINT PRIMARY KEY,
                wounds INTEGER DEFAULT 0,
                money INTEGER DEFAULT 1000,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1
            );
            """)

            # Cria a tabela 'inventory' se não existir
            await connection.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES players(user_id) ON DELETE CASCADE,
                item TEXT NOT NULL
            );
            """)

            print("Tabelas criadas ou já existentes.")
        except Exception as e:
            print(f"Erro ao criar tabelas: {e}")
            exit(1)

async def load_cogs():
    """Carrega os cogs da lista."""
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"Cog {cog} carregado com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar o cog {cog}: {e}")

@tasks.loop(minutes=5)  # Alterna o status a cada 5 minutos
async def change_status():
    statuses = [
        "Matando sobreviventes",
        "Armando arapucas",
        "Caçando novos desafiantes",
        "Protegendo o território",
        "Preparando armadilhas"
    ]
    new_status = random.choice(statuses)
    await bot.change_presence(activity=discord.Game(name=new_status))

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    change_status.start()  # Inicia a tarefa para alternar o status

# Função de setup principal
async def main():
    await setup_database()  # Configura o banco de dados e cria as tabelas
    await load_cogs()       # Carrega os cogs
    await bot.start(os.getenv("TOKEN"))

# Iniciar o bot
if __name__ == "__main__":
    asyncio.run(main())
