# bot.py

import discord
from discord.ext import commands
import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATABASE_URL = os.getenv("DATABASE_URL")

async def setup_database():
    bot.pool = await asyncpg.create_pool(DATABASE_URL)
    async with bot.pool.acquire() as connection:
        # Criação de tabelas
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

# Função assíncrona para carregar o cog
async def load_cogs():
    await bot.load_extension("cogs.boss")  # Carrega o cog de forma assíncrona

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

async def main():
    await setup_database()
    await load_cogs()  # Garante que o carregamento do cog é assíncrono
    await bot.start(os.getenv("TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
