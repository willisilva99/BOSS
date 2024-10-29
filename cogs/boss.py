import discord
from discord.ext import commands, tasks
import random
import time
from datetime import datetime, timedelta

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown_time = 3600  # 1 hora de cooldown
        self.last_attack_time = {}
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
        self.exempt_role_id = 1296631135442309160  # Cargo com permissão de ignorar cooldown

    @commands.command(name="boss")
    @commands.cooldown(1, 30, commands.BucketType.user)  # Cooldown pessoal de 30 segundos
    async def boss_command(self, ctx):
        if ctx.channel.id != self.commands_channel_id:
            await ctx.send("⚠️ Este comando só pode ser usado no canal designado para combates.")
            return

        user_id = ctx.author.id
        current_time = time.time()
        
        # Verifica se o jogador tem o cargo que ignora o cooldown global
        has_exempt_role = any(role.id == self.exempt_role_id for role in ctx.author.roles)
        
        # Cooldown global para jogadores sem o cargo
        if not self.current_boss and not has_exempt_role:
            if current_time - self.last_attack_time.get(user_id, 0) < self.cooldown_time:
                remaining = int(self.cooldown_time - (current_time - self.last_attack_time.get(user_id, 0)))
                await ctx.send(f"💤 O boss está descansando! Tente novamente em {remaining // 60} minutos.")
                return
            
            # Invocação do Boss
            self.current_boss = random.choice(self.bosses)
            self.current_boss["current_hp"] = self.current_boss["hp"]
            self.last_attack_time[user_id] = current_time
            embed = discord.Embed(
                title="⚔️ Um Boss Apareceu!",
                description=f"**{self.current_boss['name']}** surgiu com {self.current_boss['current_hp']} HP! Preparem-se para a batalha.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

        else:
            # Verifica se o jogador está infectado
            if await self.is_infected(user_id):
                await ctx.send("❌ Você está infectado e não pode atacar o boss. Encontre uma cura primeiro!")
                return
            
            # Ataque ao Boss
            damage = random.randint(50, 150)
            if await self.has_damage_debuff(user_id):
                damage = int(damage * 0.75)  # Reduz o dano em 25% se o jogador tiver debuff
                await ctx.send(f"💀 {ctx.author.display_name} está enfraquecido e causou menos dano!")

            self.current_boss["current_hp"] -= damage
            await self.award_xp(user_id, 10)  # Sistema de XP ao atacar

            # Mensagem do Ataque
            embed = discord.Embed(
                title="💥 Ataque ao Boss",
                description=f"{ctx.author.display_name} causou {damage} de dano!\n**HP Restante do Boss:** {self.current_boss['current_hp']}",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)

            # Aplica infecção aleatória e penalidade
            await self.apply_infection(user_id)
            await self.apply_damage_debuff(user_id)

            # Checa se o boss foi derrotado
            if self.current_boss["current_hp"] <= 0:
                await self.defeat_boss(ctx, user_id)

    async def defeat_boss(self, ctx, user_id):
        # Recompensa e reset do boss após derrota
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

    # Função para verificar infecção
    async def is_infected(self, user_id):
        async with self.bot.pool.acquire() as connection:
            result = await connection.fetchrow("SELECT infected FROM players WHERE user_id = $1", user_id)
            return result['infected'] if result else False

    # Sistema de infecção
    async def apply_infection(self, user_id):
        chance = random.randint(1, 100)
        if chance <= 20:  # 20% de chance de infecção
            async with self.bot.pool.acquire() as connection:
                await connection.execute("UPDATE players SET infected = TRUE WHERE user_id = $1", user_id)
            await self.bot.get_channel(self.status_channel_id).send(f"⚠️ {self.bot.get_user(user_id).display_name} foi infectado durante o combate!")

    # Aplicação de debuff de dano
    async def apply_damage_debuff(self, user_id):
        chance = random.randint(1, 100)
        if chance <= 15:  # 15% de chance de debuff
            async with self.bot.pool.acquire() as connection:
                await connection.execute("UPDATE players SET damage_debuff = TRUE WHERE user_id = $1", user_id)

    # Função para verificar se o jogador possui debuff de dano
    async def has_damage_debuff(self, user_id):
        async with self.bot.pool.acquire() as connection:
            result = await connection.fetchrow("SELECT damage_debuff FROM players WHERE user_id = $1", user_id)
            return result['damage_debuff'] if result else False

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
            members = [member.display_name for member in channel.members if member.id != self.bot.user.id]
            if members:
                await channel.send(f"{random.choice(taunts)} {random.choice(members)}, você será o próximo! 😈")

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
