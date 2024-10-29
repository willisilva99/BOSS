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
    "rank",  # Cog de ranking dos jogadores
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
    """Conecta ao banco de dados e cria as tabelas, se não existirem."""
    try:
        bot.pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
        print("Conexão com o banco de dados estabelecida com sucesso.")

        async with bot.pool.acquire() as connection:
            # Criação da tabela de rankings, se não existir
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS player_rankings (
                    user_id BIGINT PRIMARY KEY,
                    total_damage INTEGER DEFAULT 0,
                    kills INTEGER DEFAULT 0,
                    snipers INTEGER DEFAULT 0
                );
            """)
            print("Tabela 'player_rankings' garantida no banco de dados.")
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

@tasks.loop(minutes=10)
async def change_status():
    """Atualiza o status do bot aleatoriamente a cada 10 minutos."""
    new_status = random.choice(status_messages)
    await bot.change_presence(activity=discord.Game(new_status))

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    print("Bot está pronto e todos os cogs foram carregados.")
    change_status.start()  # Inicia a tarefa de mudança de status

@bot.event
async def on_command_error(ctx, error):
    """Captura e exibe erros de comando."""
    if isinstance(error, commands.CommandOnCooldown):
        embed = discord.Embed(
            title="⏳ Cooldown Ativo",
            description=f"O comando `{ctx.command}` está em cooldown. Tente novamente em {error.retry_after:.2f} segundos.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="⚠️ Erro de Comando",
            description=f"Ocorreu um erro ao executar `{ctx.command}`:\n{error}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        print(f"Erro detectado: {error}")

@bot.event
async def on_message(message):
    """Ignora mensagens do próprio bot e processa comandos nas mensagens."""
    if message.author == bot.user:
        return
    await bot.process_commands(message)

async def setup_bot():
    await setup_database()  # Configura e conecta o banco de dados
    await load_cogs()       # Carrega os cogs
    await bot.start(os.getenv("TOKEN"))  # Inicia o bot com o token do .env

if __name__ == "__main__":
    asyncio.run(setup_bot())
