import discord
from discord.ext import commands, tasks
import random
import time

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_boss = None
        self.cooldown_time = 3600  # 1 hora em segundos
        self.last_spawn_time = 0
        self.boss_attack_task.start()

        # Definição de bosses e recompensas
        self.bosses = [
            {"name": "Zumbi Sádico", "hp": 1500, "attack_power": 100},
            {"name": "Zumbi Ancião", "hp": 2000, "attack_power": 150},
            {"name": "Zumbi Destruidor", "hp": 2500, "attack_power": 200}
        ]
        self.weapons = ["SNIPER ADAMANTY", "SNIPER EMBERIUM", "SNIPER BOSS LENDÁRIA"]

    @commands.command(name="boss")
    async def spawn_or_attack_boss(self, ctx):
        user_id = ctx.author.id
        current_time = time.time()

        if not self.current_boss:
            if current_time - self.last_spawn_time < self.cooldown_time:
                remaining = int(self.cooldown_time - (current_time - self.last_spawn_time))
                await ctx.send(f"O boss ainda está descansando! Tente novamente em {remaining // 60} minutos e {remaining % 60} segundos.")
                return

            self.current_boss = random.choice(self.bosses)
            self.current_boss["current_hp"] = self.current_boss["hp"]
            self.last_spawn_time = current_time
            await ctx.send(f"⚔️ Um novo boss **{self.current_boss['name']}** apareceu com {self.current_boss['current_hp']} HP!")

        else:
            damage = random.randint(50, 150)
            self.current_boss["current_hp"] -= damage
            await ctx.send(f"{ctx.author.display_name} atacou o boss e causou {damage} de dano!")
            await ctx.send(f"**{self.current_boss['name']}** tem {self.current_boss['current_hp']} de HP restante.")

            if self.current_boss["current_hp"] <= 0:
                weapon_reward = random.choice(self.weapons)
                await ctx.send(f"🏆 O boss **{self.current_boss['name']}** foi derrotado! Recompensa: **{weapon_reward}** 🎁")
                self.current_boss = None  # Reseta o boss

    @tasks.loop(seconds=60)
    async def boss_attack_task(self):
        if self.current_boss:
            # Lógica para o ataque do boss pode ser implementada aqui
            pass

    @boss_attack_task.before_loop
    async def before_boss_attack(self):
        await self.bot.wait_until_ready()

# Função para configurar o cog
def setup(bot):
    bot.add_cog(BossCog(bot))  # Adiciona o cog de forma síncrona
