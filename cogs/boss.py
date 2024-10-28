# cogs/boss.py

import discord
from discord.ext import commands, tasks
import random
import asyncio
import asyncpg
import time

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_boss = None
        self.cooldown_time = 3600  # 1 hora em segundos
        self.last_spawn_time = 0
        self.boss_attack_task.start()

    def cog_unload(self):
        self.boss_attack_task.cancel()

    # Definição dos bosses e armas
    bosses = [
        {"name": "Zumbi Sádico", "hp": 1500, "description": "Um zumbi incrivelmente forte e resistente!", "attack_power": 100},
        {"name": "Zumbi Ancião", "hp": 2000, "description": "Um zumbi com habilidades místicas.", "attack_power": 150},
        {"name": "Zumbi Destruidor", "hp": 2500, "description": "O mais poderoso dos zumbis, destruidor de mundos!", "attack_power": 200}
    ]

    weapons = ["SNIPER ADAMANTY", "SNIPER EMBERIUM", "SNIPER BOSS LENDÁRIA"]

    @commands.command(name="boss")
    async def spawn_or_attack_boss(self, ctx):
        user_id = ctx.author.id
        async with self.bot.pool.acquire() as connection:
            # Verifica se o usuário está ferido
            row = await connection.fetchrow("SELECT wounds, money, xp, level FROM players WHERE user_id = $1", user_id)
            if row:
                wounds = row['wounds']
                if wounds > 0:
                    await ctx.send(f"{ctx.author.mention}, você está ferido e precisa se curar antes de atacar o boss! Use `!heal` na loja.")
                    return
            else:
                # Se o usuário não existe no banco, cria um registro
                await connection.execute(
                    "INSERT INTO players(user_id, wounds, money, xp, level) VALUES($1, $2, $3, $4, $5)",
                    user_id, 0, 1000, 0, 1
                )

        # Se não há boss ativo, invoca um novo
        if not self.current_boss:
            current_time = time.time()
            if current_time - self.last_spawn_time < self.cooldown_time:
                remaining = int(self.cooldown_time - (current_time - self.last_spawn_time))
                await ctx.send(f"O boss ainda está descansando! Tente novamente em {remaining // 60} minutos e {remaining % 60} segundos.")
                return

            # Escolhe um boss aleatório
            self.current_boss = random.choice(self.bosses)
            self.current_boss["current_hp"] = self.current_boss["hp"]
            self.last_spawn_time = current_time

            await ctx.send(f"🔥 Um novo boss apareceu! **{self.current_boss['name']}** - {self.current_boss['description']} 🔥")
            await self.announce_boss_attack(ctx.guild)
        else:
            # Caso já exista um boss, o comando !boss é usado para atacar
            damage = random.randint(50, 150)  # Dano aumentado para refletir boss forte
            async with self.bot.pool.acquire() as connection:
                # Atualiza XP e nível do jogador
                await connection.execute("UPDATE players SET xp = xp + $1 WHERE user_id = $2", damage, user_id)
                # Ganha dinheiro baseado no dano
                await connection.execute("UPDATE players SET money = money + $1 WHERE user_id = $2", damage * 2, user_id)

                # Verifica se o usuário subiu de nível
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

            await ctx.send(f"{ctx.author.display_name} atacou o boss e causou {damage} de dano! 💥")
            await ctx.send(f"**{self.current_boss['name']}** tem {self.current_boss['current_hp']} de HP restante.")

            # Chance de o jogador morrer
            death_chance = random.randint(1, 100)
            if death_chance <= 5:  # 5% de chance de morte
                await ctx.send(f"💀 {ctx.author.mention} foi morto pelo boss! Você sofreu ferimentos graves.")
                async with self.bot.pool.acquire() as connection:
                    await connection.execute("UPDATE players SET wounds = wounds + 1 WHERE user_id = $1", user_id)

            if self.current_boss["current_hp"] <= 0:
                # Boss derrotado
                weapon_reward = random.choice(self.weapons)
                await ctx.send(f"🏆 O boss **{self.current_boss['name']}** foi derrotado! Recompensa: **{weapon_reward}** 🎁")
                
                # Anuncia que o boss está zombando do jogador
                await self.announce_boss_mock(ctx.guild, ctx.author.display_name)

                async with self.bot.pool.acquire() as connection:
                    # Concede a arma ao jogador
                    await connection.execute(
                        "INSERT INTO inventory(user_id, item) VALUES($1, $2)",
                        user_id, weapon_reward
                    )
                    # Concede dinheiro adicional
                    await connection.execute(
                        "UPDATE players SET money = money + 500 WHERE user_id = $1",
                        user_id
                    )

                self.current_boss = None  # Reseta o boss para a próxima vez

    @tasks.loop(seconds=60)
    async def boss_attack_task(self):
        if self.current_boss:
            # Escolhe um canal aleatório para anunciar o ataque
            guilds = self.bot.guilds
            if guilds:
                guild = random.choice(guilds)
                if guild.text_channels:
                    channel = random.choice(guild.text_channels)
                    damage = self.current_boss.get("attack_power", 100)
                    # Escolhe um jogador aleatório para atacar
                    async with self.bot.pool.acquire() as connection:
                        row = await connection.fetchrow("SELECT user_id FROM players ORDER BY random() LIMIT 1")
                        if row:
                            user_id = row['user_id']
                            await connection.execute("UPDATE players SET wounds = wounds + 1 WHERE user_id = $1", user_id)
                            user = guild.get_member(user_id)
                            if user:
                                await channel.send(f"⚔️ **{self.current_boss['name']}** atacou {user.mention} causando {damage} de dano! Você está ferido!")

    @boss_attack_task.before_loop
    async def before_boss_attack(self):
        await self.bot.wait_until_ready()

    async def announce_boss_attack(self, guild):
        if guild.text_channels:
            channel = random.choice(guild.text_channels)
            await channel.send(f"⚔️ **{self.current_boss['name']}** está atacando todos os jogadores! Preparem-se para a batalha! ⚔️")

    async def announce_boss_mock(self, guild, player_name):
        if guild.text_channels:
            channel = random.choice(guild.text_channels)
            await channel.send(f"😈 **{self.current_boss['name']}** está zombando de {player_name}! Você realmente acha que pode me derrotar? 😈")

    @commands.command(name="shop")
    async def shop(self, ctx):
        """Exibe a loja onde os jogadores podem comprar itens."""
        shop_items = {
            "🍎 Potion": 100,      # Cura 1 ferimento
            "🔫 Sniper Adamanty": 1000,
            "🔥 Sniper Emberium": 2000,
            "💣 Sniper Boss Lendária": 5000
        }
        embed = discord.Embed(title="🏪 Loja do Boss", color=discord.Color.blue())
        for item, price in shop_items.items():
            embed.add_field(name=item, value=f"Preço: {price} coins", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="buy")
    async def buy(self, ctx, *, item: str):
        """Permite que os jogadores comprem itens na loja."""
        shop_items = {
            "potion": {"name": "🍎 Potion", "price": 100},
            "sniper adamanty": {"name": "🔫 Sniper Adamanty", "price": 1000},
            "sniper emberium": {"name": "🔥 Sniper Emberium", "price": 2000},
            "sniper boss lendária": {"name": "💣 Sniper Boss Lendária", "price": 5000}
        }
        item_key = item.lower()
        if item_key not in shop_items:
            await ctx.send("Esse item não está disponível na loja.")
            return

        async with self.bot.pool.acquire() as connection:
            row = await connection.fetchrow("SELECT money FROM players WHERE user_id = $1", ctx.author.id)
            if not row:
                await connection.execute(
                    "INSERT INTO players(user_id, wounds, money, xp, level) VALUES($1, $2, $3, $4, $5)",
                    ctx.author.id, 0, 1000, 0, 1
                )
                row = await connection.fetchrow("SELECT money FROM players WHERE user_id = $1", ctx.author.id)

            money = row['money']
            price = shop_items[item_key]['price']
            if money < price:
                await ctx.send("Você não tem dinheiro suficiente para comprar esse item.")
                return

            # Deduz o preço do dinheiro do jogador
            await connection.execute("UPDATE players SET money = money - $1 WHERE user_id = $2", price, ctx.author.id)
            # Adiciona o item ao inventário
            await connection.execute("INSERT INTO inventory(user_id, item) VALUES($1, $2)", ctx.author.id, shop_items[item_key]['name'])
            await ctx.send(f"Você comprou **{shop_items[item_key]['name']}** por {price} coins!")

    @commands.command(name="heal")
    async def heal(self, ctx):
        """Permite que os jogadores curem seus ferimentos."""
        async with self.bot.pool.acquire() as connection:
            row = await connection.fetchrow("SELECT wounds, money FROM players WHERE user_id = $1", ctx.author.id)
            if not row:
                await connection.execute(
                    "INSERT INTO players(user_id, wounds, money, xp, level) VALUES($1, $2, $3, $4, $5)",
                    ctx.author.id, 0, 1000, 0, 1
                )
                row = await connection.fetchrow("SELECT wounds, money FROM players WHERE user_id = $1", ctx.author.id)

            wounds = row['wounds']
            money = row['money']

            if wounds <= 0:
                await ctx.send("Você não está ferido no momento.")
                return

            potion_price = 100
            if money < potion_price:
                await ctx.send("Você não tem dinheiro suficiente para comprar uma poção.")
                return

            # Deduz o preço e cura o ferimento
            await connection.execute(
                "UPDATE players SET money = money - $1, wounds = wounds - 1 WHERE user_id = $2",
                potion_price, ctx.author.id
            )
            await ctx.send(f"Você comprou uma **🍎 Potion** e curou 1 ferimento por {potion_price} coins!")

    @commands.command(name="inventory")
    async def inventory(self, ctx):
        """Exibe o inventário do jogador."""
        async with self.bot.pool.acquire() as connection:
            rows = await connection.fetch("SELECT item FROM inventory WHERE user_id = $1", ctx.author.id)
            if not rows:
                await ctx.send("Seu inventário está vazio.")
                return

            items = [row['item'] for row in rows]
            embed = discord.Embed(title=f"{ctx.author.display_name}'s Inventário", color=discord.Color.green())
            for item in items:
                embed.add_field(name=item, value="---", inline=False)
            await ctx.send(embed=embed)

    @commands.command(name="stats")
    async def stats(self, ctx):
        """Exibe as estatísticas do jogador."""
        async with self.bot.pool.acquire() as connection:
            row = await connection.fetchrow("SELECT xp, level, money, wounds FROM players WHERE user_id = $1", ctx.author.id)
            if not row:
                await connection.execute(
                    "INSERT INTO players(user_id, wounds, money, xp, level) VALUES($1, $2, $3, $4, $5)",
                    ctx.author.id, 0, 1000, 0, 1
                )
                row = await connection.fetchrow("SELECT xp, level, money, wounds FROM players WHERE user_id = $1", ctx.author.id)

            xp = row['xp']
            level = row['level']
            money = row['money']
            wounds = row['wounds']

            embed = discord.Embed(title=f"📊 Estatísticas de {ctx.author.display_name}", color=discord.Color.purple())
            embed.add_field(name="Nível", value=level, inline=True)
            embed.add_field(name="XP", value=xp, inline=True)
            embed.add_field(name="Dinheiro", value=f"{money} coins", inline=True)
            embed.add_field(name="Ferimentos", value=wounds, inline=True)
            await ctx.send(embed=embed)

    # Eventos adicionais podem ser adicionados aqui (como destruição de recompensas pelo boss)

# Configuração para adicionar o cog
def setup(bot):
    bot.add_cog(BossCog(bot))
