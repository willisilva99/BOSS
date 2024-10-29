import discord
from discord.ext import commands
import random

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_boss = None  # Inicialmente, sem boss ativo
        self.cooldown_time = 3600  # 1 hora de cooldown por usuário
        self.last_attack_time = {}
        self.snipers = ["SNIPER BOSS RARA", "SNIPER EMBERIUM", "SNIPER DAMANTY"]

    async def ensure_player(self, user_id):
        # Função para garantir que o jogador tenha uma entrada de dados no banco (pode ser customizado)
        pass  # Aqui inseriríamos a lógica de banco de dados

    def generate_sniper_drop(self):
        """Define a premiação com risco de ser quebrada."""
        drop_chance = random.randint(1, 100)
        if drop_chance <= 10:  # Chance de dropar sniper rara (10%)
            selected_sniper = random.choice(self.snipers)
            destroy_chance = random.randint(1, 100)
            if destroy_chance <= 20:  # 20% de chance do boss quebrar o prêmio
                return f"O boss quebrou a {selected_sniper}!"
            else:
                return f"Parabéns! Você ganhou uma {selected_sniper}!"
        return "O boss não deixou nenhuma sniper desta vez."

    @commands.command(name="boss")
    async def boss_attack(self, ctx):
        """Permite atacar o boss e, se derrotado, concede uma premiação."""
        user_id = ctx.author.id
        if not self.current_boss:
            # Invoca o boss com 1000 HP, configurável
            self.current_boss = {"name": "Mega Boss", "hp": 1000}
            await ctx.send(f"⚔️ O {self.current_boss['name']} foi invocado com {self.current_boss['hp']} HP!")
            # Permite que o invocador ataque imediatamente sem cooldown
            damage = random.randint(50, 150)
            self.current_boss["hp"] -= damage
            await ctx.send(f"{ctx.author.display_name} atacou o boss causando {damage} de dano! HP restante do boss: {self.current_boss['hp']}")

            if self.current_boss["hp"] <= 0:
                # Boss derrotado imediatamente
                await ctx.send("🏆 O boss foi derrotado!")
                reward_message = self.generate_sniper_drop()
                await ctx.send(reward_message)
                self.current_boss = None  # Reinicia o boss para próxima invocação
        else:
            # Caso o boss já tenha sido invocado, aplica o cooldown padrão
            if ctx.author.id not in self.last_attack_time or (ctx.message.created_at.timestamp() - self.last_attack_time[ctx.author.id]) >= self.cooldown_time:
                damage = random.randint(50, 150)
                self.current_boss["hp"] -= damage
                self.last_attack_time[ctx.author.id] = ctx.message.created_at.timestamp()
                await ctx.send(f"{ctx.author.display_name} atacou o boss causando {damage} de dano! HP restante do boss: {self.current_boss['hp']}")

                if self.current_boss["hp"] <= 0:
                    # Boss derrotado
                    await ctx.send("🏆 O boss foi derrotado!")
                    reward_message = self.generate_sniper_drop()
                    await ctx.send(reward_message)
                    self.current_boss = None  # Reinicia o boss para próxima invocação
            else:
                # Usuário está em cooldown
                time_remaining = self.cooldown_time - (ctx.message.created_at.timestamp() - self.last_attack_time[ctx.author.id])
                await ctx.send(f"⏳ {ctx.author.display_name}, você precisa esperar mais {time_remaining:.0f} segundos para atacar o boss novamente!")

    @commands.Cog.listener()
    async def on_ready(self):
        """Evento chamado quando o bot está pronto."""
        print("BossCog está pronto!")

# Função de setup para adicionar o cog ao bot
async def setup(bot):
    await bot.add_cog(BossCog(bot))
