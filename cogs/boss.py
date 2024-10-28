import discord
from discord.ext import commands
import random
import time

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_boss = None
        self.cooldown_time = 3600  # 1 hora em segundos
        self.last_attack_time = 0

    # Definição dos bosses e armas
    bosses = [
        {"name": "Boss Zumbi 1", "hp": 500, "description": "Um zumbi assustador!"},
        {"name": "Boss Zumbi 2", "hp": 700, "description": "Mais forte, cuidado!"},
        {"name": "Boss Zumbi 3", "hp": 1000, "description": "Quase indestrutível!"}
    ]

    weapons = ["SNIPER ADAMANTY", "SNIPER EMBERIUM", "SNIPER BOSS RARA"]

    @commands.command(name="boss")
    async def spawn_or_attack_boss(self, ctx):
        # Se não há boss ativo, invoca um novo
        if not self.current_boss:
            # Verifica o cooldown
            if time.time() - self.last_attack_time < self.cooldown_time:
                await ctx.send("O boss ainda está descansando! Tente novamente mais tarde.")
                return

            # Escolhe um boss aleatório
            self.current_boss = random.choice(self.bosses)
            self.current_boss["current_hp"] = self.current_boss["hp"]
            self.last_attack_time = time.time()

            await ctx.send(f"Um novo boss apareceu! {self.current_boss['name']} - {self.current_boss['description']}")
        else:
            # Caso já exista um boss, o comando !boss é usado para atacar
            damage = random.randint(10, 50)
            self.current_boss["current_hp"] -= damage

            await ctx.send(f"{ctx.author.display_name} atacou o boss e causou {damage} de dano!")

            if self.current_boss["current_hp"] <= 0:
                # Boss derrotado
                weapon_reward = random.choice(self.weapons)
                await ctx.send(f"O boss {self.current_boss['name']} foi derrotado! Recompensa: {weapon_reward}")
                self.current_boss = None  # Reseta o boss para a próxima vez
            else:
                await ctx.send(f"O boss {self.current_boss['name']} tem {self.current_boss['current_hp']} de HP restante.")

# Configuração para adicionar o cog
def setup(bot):
    bot.add_cog(BossCog(bot))
