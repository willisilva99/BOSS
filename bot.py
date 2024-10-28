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

def load_cogs():
    # Carrega o cog de forma síncrona
    bot.load_extension("cogs.boss")

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

async def setup():
    await setup_database()  # Configura o banco de dados
    load_cogs()            # Carrega os cogs de forma síncrona

async def main():
    await setup()           # Chama a função setup assíncrona
    await bot.start(os.getenv("TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())

