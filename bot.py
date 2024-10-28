# bot.py

import discord
from discord.ext import commands
import os
import asyncio
import asyncpg
from dotenv import load_dotenv

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
    # Adicione outros cogs aqui, se houver
]

# Conexão com o banco de dados
DATABASE_URL = os.getenv("DATABASE_URL")

async def setup_database():
    """Configura a conexão com o banco de dados e cria as tabelas necessárias."""
    bot.pool = await asyncpg.create_pool(DATABASE_URL)
    print("Banco de dados conectado com sucesso.")

    async with bot.pool.acquire() as connection:
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

        # Cria a tabela 'weapons' se não existir (opcional)
        await connection.execute("""
        CREATE TABLE IF NOT EXISTS weapons (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES players(user_id) ON DELETE CASCADE,
            weapon TEXT NOT NULL
        );
        """)

    print("Tabelas criadas ou já existentes.")

# Carregar cada cog
async def load_cogs():
    """Carrega os cogs da lista."""
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"Cog {cog} carregado com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar o cog {cog}: {e}")

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# Função de setup principal
async def main():
    await setup_database()  # Configura o banco de dados e cria as tabelas
    await load_cogs()       # Carrega os cogs
    await bot.start(os.getenv("TOKEN"))

# Iniciar o bot
if __name__ == "__main__":
    asyncio.run(main())
