import discord
from discord.ext import commands, tasks
import random
import time

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown_time = 3600  # 1 hora de cooldown global
        self.current_boss = None
        self.boss_attack_task.start()
        self.rank_update.start()
        
        # Configuração de bosses sem imagens
        self.bosses = [
            {"name": "Zumbi Sádico 🧟", "hp": 1500, "attack_power": 100},
            {"name": "Zumbi Ancião 🧟‍♂️", "hp": 2000, "attack_power": 150},
            {"name": "Zumbi Destruidor 💀", "hp": 2500, "attack_power": 200}
        ]
        self.weapons = ["🪓 Machado Lendário", "🔫 Pistola Rugida", "🔪 Faca Sombria"]
        self.rare_loot = {
            "comum": ["🔧 Kit Básico", "📦 Suprimentos"],
            "raro": ["💎 Pedra Rara", "🔫 Arma Especial"],
            "épico": ["🔥 Arma Lendária"]
        }
        self.consumables = {
            "antiviral": "💊 Remédio Antiviral",
            "soro": "💉 Soro de Força"
        }
        self.status_channel_id = 1186636197934661632
        self.commands_channel_id = 1299092242673303552
        self.exempt_role_id = 1296631135442309160  # Cargo com permissão de ignorar cooldown

    async def ensure_player(self, user_id):
        """Garante que o usuário tenha uma entrada na tabela 'players'."""
        async with self.bot.pool.acquire() as connection:
            # Tenta buscar o jogador
            result = await connection.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not result:
                # Se não existir, insere com valores padrão
                await connection.execute("""
                    INSERT INTO players (user_id, wounds, money, xp, level, infected, damage_debuff)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, user_id, 0, 1000, 0, 1, False, False)
                print(f"Jogador {user_id} adicionado à tabela 'players'.")

    @commands.command(name="boss")
    @commands.cooldown(1, 3600, commands.BucketType.default)  # 1 hora de cooldown global
    async def boss_command(self, ctx):
        if ctx.channel.id != self.commands_channel_id:
            await ctx.send("⚠️ Este comando só pode ser usado no canal designado para combates.")
            return

        user_id = ctx.author.id

        # Garante que o jogador existe no banco de dados
        await self.ensure_player(user_id)

        # Verifica se o jogador tem o cargo que ignora o cooldown global
        has_exempt_role = any(role.id == self.exempt_role_id for role in ctx.author.roles)

        if has_exempt_role:
            # Executa a lógica sem aplicar o cooldown
            await self.invocar_boss(ctx, user_id)
        else:
            if not self.current_boss:
                # Invocação do Boss
                self.current_boss = random.choice(self.bosses)
                self.current_boss["current_hp"] = self.current_boss["hp"]
                self.current_boss["last_attack_time"] = time.time()
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
                else:
                    # Habilidade especial do boss quando HP está baixo
                    await self.boss_special_ability()

    async def invocar_boss(self, ctx, user_id):
        """Lógica para invocar o boss."""
        if not self.current_boss:
            # Invocação do Boss
            self.current_boss = random.choice(self.bosses)
            self.current_boss["current_hp"] = self.current_boss["hp"]
            self.current_boss["last_attack_time"] = time.time()
            embed = discord.Embed(
                title="⚔️ Um Boss Apareceu!",
                description=f"**{self.current_boss['name']}** surgiu com {self.current_boss['current_hp']} HP! Preparem-se para a batalha.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚔️ Já há um boss ativo no momento!")

    async def defeat_boss(self, ctx, user_id):
        # Recompensa e reset do boss após derrota
        reward = self.generate_loot()
        await self.add_item_to_inventory(user_id, reward)
        embed = discord.Embed(
            title="🏆 Boss Derrotado!",
            description=f"O boss **{self.current_boss['name']}** foi vencido! Recompensa: **{reward}** 🎁",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        self.current_boss = None  # Reseta o boss

    def generate_loot(self):
        """Gera loot baseado em raridade."""
        loot_type = random.choices(["comum", "raro", "épico"], weights=(60, 30, 10), k=1)[0]
        return random.choice(self.rare_loot[loot_type])

    async def boss_special_ability(self):
        """Muda a habilidade do boss conforme o HP reduz e aplica ataques especiais."""
        if self.current_boss:
            hp_ratio = self.current_boss["current_hp"] / self.current_boss["hp"]
            
            # Fase 1 (60% - 100% HP)
            if 0.6 <= hp_ratio <= 1.0 and not self.current_boss.get("phase_one"):
                self.current_boss["phase_one"] = True
                embed = discord.Embed(
                    title="⚠️ Fase 1",
                    description=f"O boss **{self.current_boss['name']}** começou a batalha com ataques básicos!",
                    color=discord.Color.blue()
                )
                await self.bot.get_channel(self.status_channel_id).send(embed=embed)
            
            # Fase 2 (30% - 60% HP)
            elif 0.3 <= hp_ratio < 0.6 and not self.current_boss.get("phase_two"):
                self.current_boss["phase_two"] = True
                self.current_boss["attack_power"] *= 1.2  # Aumenta o ataque em 20%
                embed = discord.Embed(
                    title="🔥 Fase 2",
                    description=f"🔥 **{self.current_boss['name']}** se enfureceu e aumentou seu ataque!",
                    color=discord.Color.dark_red()
                )
                await self.bot.get_channel(self.status_channel_id).send(embed=embed)
                await self.summon_minions()  # Invoca minions

            # Fase 3 (0% - 30% HP)
            elif hp_ratio < 0.3 and not self.current_boss.get("phase_three"):
                self.current_boss["phase_three"] = True
                self.current_boss["attack_power"] *= 1.5  # Aumenta o ataque em 50%
                embed = discord.Embed(
                    title="💀 Fase 3",
                    description=f"💀 **{self.current_boss['name']}** entrou em sua fase final! Ataques devastadores à frente!",
                    color=discord.Color.dark_purple()
                )
                await self.bot.get_channel(self.status_channel_id).send(embed=embed)
                await self.apply_group_penalty()

    async def summon_minions(self):
        """Invoca minions durante o combate como fase de desafio."""
        minions_count = random.randint(3, 5)
        minions = [f"Minion {i+1} 🧟" for i in range(minions_count)]
        embed = discord.Embed(
            title="🧟 Minions Invocados!",
            description=f"**{self.current_boss['name']}** invocou minions! Eles estão atacando jogadores: {', '.join(minions)}.",
            color=discord.Color.dark_blue()
        )
        await self.bot.get_channel(self.status_channel_id).send(embed=embed)
        
    async def apply_group_penalty(self):
        """Aplica uma penalidade de infecção a todos os jogadores no combate."""
        channel = self.bot.get_channel(self.commands_channel_id)
        if channel is None:
            print(f"Canal com ID {self.commands_channel_id} não encontrado.")
            return
        infected_players = []
        for member in channel.members:
            if member.id != self.bot.user.id:
                infected_players.append(member.display_name)
                await self.apply_infection(member.id)  # Aplica infecção ao jogador

        if infected_players:
            embed = discord.Embed(
                title="💉 Penalty de Grupo",
                description=f"O boss infectou: {', '.join(infected_players)}!",
                color=discord.Color.dark_red()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)

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
            member = self.bot.get_user(user_id)
            if member:
                await self.bot.get_channel(self.status_channel_id).send(
                    f"⚠️ {member.display_name} foi infectado durante o combate!"
                )

    # Aplicação de debuff de dano
    async def apply_damage_debuff(self, user_id):
        chance = random.randint(1, 100)
        if chance <= 15:  # 15% de chance de debuff
            async with self.bot.pool.acquire() as connection:
                await connection.execute("UPDATE players SET damage_debuff = TRUE WHERE user_id = $1", user_id)
            member = self.bot.get_user(user_id)
            if member:
                await self.bot.get_channel(self.status_channel_id).send(
                    f"⚠️ {member.display_name} recebeu um debuff de dano!"
                )

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
            if channel is None:
                print(f"Canal com ID {self.status_channel_id} não encontrado.")
                return
            members = [member.display_name for member in channel.members if member.id != self.bot.user.id]
            if members:
                embed = discord.Embed(
                    title="😈 Zombaria do Boss",
                    description=f"{random.choice(taunts)} {random.choice(members)}, você será o próximo!",
                    color=discord.Color.dark_purple()
                )
                await channel.send(embed=embed)

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
        await self.bot.get_channel(self.status_channel_id).send(embed=embed)

    @boss_attack_task.before_loop
    async def before_boss_attack(self):
        await self.bot.wait_until_ready()

    @rank_update.before_loop
    async def before_rank_update(self):
        await self.bot.wait_until_ready()

# Configuração do cog
async def setup(bot):
    await bot.add_cog(BossCog(bot))
