# cogs/boss.py

import discord
from discord.ext import commands, tasks
import random
import time

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_boss = None
        self.cooldown_time = 3600
        self.last_spawn_time = 0
        self.boss_attack_task.start()

        # IDs de canal para anúncios e comandos
        self.announcement_channel_id = 1186636197934661632
        self.commands_channel_id = 1299092242673303552

    def cog_unload(self):
        self.boss_attack_task.cancel()

    bosses = [
        {"name": "Zumbi Sádico", "hp": 1500, "description": "Um zumbi incrivelmente forte e resistente!", "attack_power": 100},
        {"name": "Zumbi Ancião", "hp": 2000, "description": "Um zumbi com habilidades místicas.", "attack_power": 150},
        {"name": "Zumbi Destruidor", "hp": 2500, "description": "O mais poderoso dos zumbis, destruidor de mundos!", "attack_power": 200}
    ]

    weapons = ["SNIPER ADAMANTY", "SNIPER EMBERIUM", "SNIPER BOSS LENDÁRIA"]

    @commands.command(name="boss")
    async def spawn_or_attack_boss(self, ctx):
        if ctx.channel.id != self.commands_channel_id:
            await ctx.send(f"{ctx.author.mention}, use os comandos do boss apenas no canal designado.")
            return

        user_id = ctx.author.id
        async with self.bot.pool.acquire() as connection:
            row = await connection.fetchrow("SELECT wounds, money, xp, level FROM players WHERE user_id = $1", user_id)
            if row:
                wounds = row['wounds']
                if wounds > 0:
                    await ctx.send(f"{ctx.author.mention}, você está ferido e precisa se curar antes de atacar o boss! Use `!heal` na loja.")
                    return
            else:
                await connection.execute(
                    "INSERT INTO players(user_id, wounds, money, xp, level) VALUES($1, $2, $3, $4, $5)",
                    user_id, 0, 1000, 0, 1
                )

        if not self.current_boss:
            current_time = time.time()
            if current_time - self.last_spawn_time < self.cooldown_time:
                remaining = int(self.cooldown_time - (current_time - self.last_spawn_time))
                await ctx.send(f"O boss ainda está descansando! Tente novamente em {remaining // 60} minutos e {remaining % 60} segundos.")
                return

            self.current_boss = random.choice(self.bosses)
            self.current_boss["current_hp"] = self.current_boss["hp"]
            self.last_spawn_time = current_time

            await self.announce_boss_attack(ctx.guild)
        else:
            damage = random.randint(50, 150)
            async with self.bot.pool.acquire() as connection:
                await connection.execute("UPDATE players SET xp = xp + $1 WHERE user_id = $2", damage, user_id)
                await connection.execute("UPDATE players SET money = money + $1 WHERE user_id = $2", damage * 2, user_id)

                row = await connection.fetchrow("SELECT xp, level FROM players WHERE user_id = $1", user_id)
                xp = row['xp']
                level = row['level']
                if xp >= level * 1000:
                    await connection.execute(
                        "UPDATE players SET level = level + 1, xp = xp - $1 WHERE user_id = $2",
                        level * 1000, user_id
                    )
                    await ctx.send(f"🎉 Parabéns {ctx.author.mention}! Você subiu para o nível {level + 1}!")

            self.current_boss["current_hp"] -= damage

            await ctx.send(f"{ctx.author.display_name} atacou o boss e causou {damage} de dano!")
            await ctx.send(f"**{self.current_boss['name']}** tem {self.current_boss['current_hp']} de HP restante.")

            death_chance = random.randint(1, 100)
            if death_chance <= 5:
                await ctx.send(f"💀 {ctx.author.mention} foi morto pelo boss!")
                async with self.bot.pool.acquire() as connection:
                    await connection.execute("UPDATE players SET wounds = wounds + 1 WHERE user_id = $1", user_id)

            if self.current_boss["current_hp"] <= 0:
                weapon_reward = random.choice(self.weapons)
                await ctx.send(f"🏆 O boss **{self.current_boss['name']}** foi derrotado! Recompensa: **{weapon_reward}** 🎁")
                await self.announce_boss_mock(ctx.guild, ctx.author.display_name)

                async with self.bot.pool.acquire() as connection:
                    await connection.execute(
                        "INSERT INTO inventory(user_id, item) VALUES($1, $2)",
                        user_id, weapon_reward
                    )
                    await connection.execute(
                        "UPDATE players SET money = money + 500 WHERE user_id = $1",
                        user_id
                    )

                self.current_boss = None

    @tasks.loop(seconds=60)
    async def boss_attack_task(self):
        if self.current_boss:
            guilds = self.bot.guilds
            if guilds:
                guild = random.choice(guilds)
                channel = guild.get_channel(self.announcement_channel_id)
                damage = self.current_boss.get("attack_power", 100)
                async with self.bot.pool.acquire() as connection:
                    row = await connection.fetchrow("SELECT user_id FROM players ORDER BY random() LIMIT 1")
                    if row:
                        user_id = row['user_id']
                        await connection.execute("UPDATE players SET wounds = wounds + 1 WHERE user_id = $1", user_id)
                        user = guild.get_member(user_id)
                        if user and channel:
                            await channel.send(f"⚔️ **{self.current_boss['name']}** atacou {user.mention} causando {damage} de dano!")

    @boss_attack_task.before_loop
    async def before_boss_attack(self):
        await self.bot.wait_until_ready()

    async def announce_boss_attack(self, guild):
        channel = guild.get_channel(self.announcement_channel_id)
        if channel:
            await channel.send(f"⚔️ **{self.current_boss['name']}** está atacando todos os jogadores! Preparem-se para a batalha! ⚔️")

    async def announce_boss_mock(self, guild, player_name):
        channel = guild.get_channel(self.announcement_channel_id)
        if channel:
            await channel.send(f"😈 **{self.current_boss['name']}** está zombando de {player_name}! Você realmente acha que pode me derrotar? 😈")

def setup(bot: commands.Bot):
    bot.add_cog(BossCog(bot))  # Remove o 'await' e deixe como uma função síncrona
