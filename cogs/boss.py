import discord
from discord.ext import commands, tasks
import random
import time

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown_time = 3600  # 1 hora em segundos
        self.last_attack_time = 0
        self.current_boss = None
        self.boss_attack_task.start()
        self.rank_update.start()
        
        # Configuração de bosses e emojis para um tema apocalíptico
        self.bosses = [
            {"name": "Zumbi Sádico 🧟", "hp": 1500, "attack_power": 100},
            {"name": "Zumbi Ancião 🧟‍♂️", "hp": 2000, "attack_power": 150},
            {"name": "Zumbi Destruidor 💀", "hp": 2500, "attack_power": 200}
        ]
        self.weapons = ["🪓 Machado Lendário", "🔫 Pistola Rugida", "🔪 Faca Sombria"]
        self.status_channel_id = 1186636197934661632
        self.commands_channel_id = 1299092242673303552

    # Comando para invocar ou atacar o boss
    @commands.command(name="boss")
    async def boss_command(self, ctx):
        # Verificação de canal correto
        if ctx.channel.id != self.commands_channel_id:
            await ctx.send("⚠️ Este comando só pode ser usado no canal designado para combates.")
            return

        user_id = ctx.author.id
        current_time = time.time()

        if not self.current_boss:
            # Cooldown
            if current_time - self.last_attack_time < self.cooldown_time:
                remaining = int(self.cooldown_time - (current_time - self.last_attack_time))
                await ctx.send(f"💤 O boss está descansando! Tente novamente em {remaining // 60} minutos.")
                return

            # Invocação do Boss
            self.current_boss = random.choice(self.bosses)
            self.current_boss["current_hp"] = self.current_boss["hp"]
            self.last_attack_time = current_time
            embed = discord.Embed(
                title="⚔️ Um Boss Apareceu!",
                description=f"**{self.current_boss['name']}** surgiu com {self.current_boss['current_hp']} HP! Preparem-se para a batalha.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

        else:
            # Ataque ao Boss
            damage = random.randint(50, 150)
            self.current_boss["current_hp"] -= damage
            await self.award_xp(user_id, 10)  # Sistema de XP ao atacar

            # Mensagem do Ataque
            embed = discord.Embed(
                title="💥 Ataque ao Boss",
                description=f"{ctx.author.display_name} causou {damage} de dano!\n**HP Restante do Boss:** {self.current_boss['current_hp']}",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)

            if self.current_boss["current_hp"] <= 0:
                await self.defeat_boss(ctx, user_id)

    async def defeat_boss(self, ctx, user_id):
        # Recompensa após derrota do Boss
        weapon_reward = random.choice(self.weapons)
        await self.add_item_to_inventory(user_id, weapon_reward)
        embed = discord.Embed(
            title="🏆 Boss Derrotado!",
            description=f"O boss **{self.current_boss['name']}** foi vencido! Recompensa: **{weapon_reward}** 🎁",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        self.current_boss = None  # Reseta o boss
    
    # Sistema de XP
    async def award_xp(self, user_id, amount):
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "UPDATE players SET xp = xp + $1 WHERE user_id = $2",
                amount, user_id
            )

    # Sistema de inventário
    async def add_item_to_inventory(self, user_id, item):
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO inventory(user_id, item) VALUES($1, $2)",
                user_id, item
            )

    # Função para zombaria periódica do boss
    @tasks.loop(minutes=5)
    async def boss_attack_task(self):
        if self.current_boss:
            taunts = [
                "Acham que podem me vencer? HAHAHA!",
                "Vocês só prolongam seu sofrimento...",
                "Eu sou o fim de tudo o que conhecem!",
                "Sentirão minha ira!"
            ]
            channel = self.bot.get_channel(self.status_channel_id)
            await channel.send(random.choice(taunts))

    # Atualização de ranking a cada 2 horas
    @tasks.loop(hours=2)
    async def rank_update(self):
        async with self.bot.pool.acquire() as connection:
            top_players = await connection.fetch(
                "SELECT user_id, xp FROM players ORDER BY xp DESC LIMIT 10"
            )
        ranking = "\n".join([f"<@{p['user_id']}> - {p['xp']} XP" for p in top_players])
        embed = discord.Embed(
            title="🏆 Ranking de Sobreviventes",
            description=ranking,
            color=discord.Color.gold()
        )
        channel = self.bot.get_channel(self.status_channel_id)
        await channel.send(embed=embed)

    @boss_attack_task.before_loop
    async def before_boss_attack(self):
        await self.bot.wait_until_ready()

    @rank_update.before_loop
    async def before_rank_update(self):
        await self.bot.wait_until_ready()

# Configuração do cog
async def setup(bot):
    await bot.add_cog(BossCog(bot))
