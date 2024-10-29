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
        
        # Configuração de bosses
        self.bosses = [
            {
                "name": "Zumbi Sádico 🧟",
                "hp": 1500,
                "attack_power": 100,
                "phase_two_trigger": 0.6,
                "phase_three_trigger": 0.3,
                "abilities": {
                    "phase_one": ["Ataque Básico"],
                    "phase_two": ["Fúria Zumbi", "Invocação de Minions"],
                    "phase_three": ["Ataque Devastador", "Explosão Viral"]
                }
            },
            {
                "name": "Zumbi Ancião 🧟‍♂️",
                "hp": 2000,
                "attack_power": 150,
                "phase_two_trigger": 0.6,
                "phase_three_trigger": 0.3,
                "abilities": {
                    "phase_one": ["Ataque Sônico"],
                    "phase_two": ["Lança Sanguínea", "Invocação de Minions"],
                    "phase_three": ["Rugido Mortal", "Explosão Viral"]
                }
            },
            {
                "name": "Zumbi Destruidor 💀",
                "hp": 2500,
                "attack_power": 200,
                "phase_two_trigger": 0.6,
                "phase_three_trigger": 0.3,
                "abilities": {
                    "phase_one": ["Ataque Devastador"],
                    "phase_two": ["Chama Zumbi", "Invocação de Minions"],
                    "phase_three": ["Espiral de Morte", "Explosão Viral"]
                }
            }
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
        self.minions = ["Minion 1 🧟", "Minion 2 🧟", "Minion 3 🧟"]
        self.boss_phases = ["fase_one", "fase_two", "fase_three"]

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
                self.current_boss["phase"] = 1
                self.current_boss["minions_active"] = False
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
                    # Atualiza fase do boss se necessário
                    await self.update_boss_phase()

    async def invocar_boss(self, ctx, user_id):
        """Lógica para invocar o boss."""
        if not self.current_boss:
            # Invocação do Boss
            self.current_boss = random.choice(self.bosses)
            self.current_boss["current_hp"] = self.current_boss["hp"]
            self.current_boss["last_attack_time"] = time.time()
            self.current_boss["phase"] = 1
            self.current_boss["minions_active"] = False
            embed = discord.Embed(
                title="⚔️ Um Boss Apareceu!",
                description=f"**{self.current_boss['name']}** surgiu com {self.current_boss['current_hp']} HP! Preparem-se para a batalha.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚔️ Já há um boss ativo no momento!")

    async def defeat_boss(self, ctx, user_id):
        """Recompensa e reset do boss após derrota."""
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

    async def add_item_to_inventory(self, user_id, item):
        """Adiciona um item ao inventário do jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO inventory(user_id, item) VALUES($1, $2)",
                user_id, item
            )

    async def is_infected(self, user_id):
        """Verifica se o jogador está infectado."""
        async with self.bot.pool.acquire() as connection:
            result = await connection.fetchrow("SELECT infected FROM players WHERE user_id = $1", user_id)
            return result['infected'] if result else False

    async def has_damage_debuff(self, user_id):
        """Verifica se o jogador possui debuff de dano."""
        async with self.bot.pool.acquire() as connection:
            result = await connection.fetchrow("SELECT damage_debuff FROM players WHERE user_id = $1", user_id)
            return result['damage_debuff'] if result else False

    async def apply_infection(self, user_id):
        """Aplica infecção ao jogador com base em chance."""
        chance = random.randint(1, 100)
        if chance <= 20:  # 20% de chance de infecção
            async with self.bot.pool.acquire() as connection:
                await connection.execute("UPDATE players SET infected = TRUE WHERE user_id = $1", user_id)
            member = self.bot.get_user(user_id)
            if member:
                await self.bot.get_channel(self.status_channel_id).send(
                    f"⚠️ {member.display_name} foi infectado durante o combate!"
                )

    async def apply_damage_debuff(self, user_id):
        """Aplica debuff de dano ao jogador com base em chance."""
        chance = random.randint(1, 100)
        if chance <= 15:  # 15% de chance de debuff
            async with self.bot.pool.acquire() as connection:
                await connection.execute("UPDATE players SET damage_debuff = TRUE WHERE user_id = $1", user_id)
            member = self.bot.get_user(user_id)
            if member:
                await self.bot.get_channel(self.status_channel_id).send(
                    f"⚠️ {member.display_name} recebeu um debuff de dano!"
                )

    async def award_xp(self, user_id, amount):
        """Concede XP ao jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "UPDATE players SET xp = xp + $1 WHERE user_id = $2",
                amount, user_id
            )

    async def update_boss_phase(self):
        """Atualiza a fase do boss com base no HP restante."""
        if not self.current_boss:
            return

        hp_ratio = self.current_boss["current_hp"] / self.current_boss["hp"]

        # Fase 2
        if hp_ratio <= self.current_boss["phase_two_trigger"] and self.current_boss["phase"] < 2:
            self.current_boss["phase"] = 2
            embed = discord.Embed(
                title="🔥 Fase 2 do Boss!",
                description=f"O boss **{self.current_boss['name']}** entrou na Fase 2! Habilidades mais poderosas à vista.",
                color=discord.Color.orange()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)
            await self.activate_phase_two()

        # Fase 3
        elif hp_ratio <= self.current_boss["phase_three_trigger"] and self.current_boss["phase"] < 3:
            self.current_boss["phase"] = 3
            embed = discord.Embed(
                title="💀 Fase 3 do Boss!",
                description=f"O boss **{self.current_boss['name']}** entrou na Fase 3! Preparem-se para ataques devastadores.",
                color=discord.Color.dark_purple()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)
            await self.activate_phase_three()

    async def activate_phase_two(self):
        """Ativa as habilidades da fase 2 do boss."""
        abilities = self.current_boss["abilities"]["phase_two"]
        for ability in abilities:
            if ability == "Invocação de Minions" and not self.current_boss["minions_active"]:
                await self.summon_minions()
            elif ability == "Fúria Zumbi":
                self.current_boss["attack_power"] += 50
                await self.bot.get_channel(self.status_channel_id).send(
                    f"🔥 **{self.current_boss['name']}** aumentou seu poder de ataque!"
                )

    async def activate_phase_three(self):
        """Ativa as habilidades da fase 3 do boss."""
        abilities = self.current_boss["abilities"]["phase_three"]
        for ability in abilities:
            if ability == "Explosão Viral":
                await self.bot.get_channel(self.status_channel_id).send(
                    f"💉 **{self.current_boss['name']}** lançou uma Explosão Viral! Todos os jogadores receberão uma infecção."
                )
                await self.apply_group_infection()
            elif ability == "Ataque Devastador":
                self.current_boss["attack_power"] += 100
                await self.bot.get_channel(self.status_channel_id).send(
                    f"💀 **{self.current_boss['name']}** lançou um Ataque Devastador!"
                )
                # Aqui você pode implementar danos aos jogadores

    async def summon_minions(self):
        """Invoca minions durante o combate."""
        self.current_boss["minions_active"] = True
        minion_count = random.randint(2, 4)
        summoned_minions = random.sample(self.minions, minion_count)
        embed = discord.Embed(
            title="🧟 Minions Invocados!",
            description=f"**{self.current_boss['name']}** invocou os seguintes minions: {', '.join(summoned_minions)}.",
            color=discord.Color.dark_blue()
        )
        await self.bot.get_channel(self.status_channel_id).send(embed=embed)
        # Você pode adicionar lógica para que os minions ataquem os jogadores

    async def apply_group_infection(self):
        """Aplica infecção a todos os jogadores ativos no combate."""
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
                title="💉 Infecção em Grupo",
                description=f"**{self.current_boss['name']}** infectou os seguintes jogadores: {', '.join(infected_players)}!",
                color=discord.Color.dark_red()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)

    async def boss_attack_task_loop(self):
        """Task que faz o boss atacar periodicamente."""
        if self.current_boss:
            channel = self.bot.get_channel(self.status_channel_id)
            if channel is None:
                print(f"Canal com ID {self.status_channel_id} não encontrado.")
                return

            # Seleciona um jogador aleatório para atacar
            channel_combat = self.bot.get_channel(self.commands_channel_id)
            if channel_combat is None:
                print(f"Canal com ID {self.commands_channel_id} não encontrado.")
                return

            combat_members = [member for member in channel_combat.members if member.id != self.bot.user.id]
            if combat_members:
                target = random.choice(combat_members)
                damage = self.current_boss["attack_power"]
                # Aqui você pode implementar a lógica para aplicar dano ao jogador
                # Por exemplo, atualizar a coluna 'wounds' no banco de dados

                # Simulação de dano
                await self.award_wounds(target.id, damage)

                embed = discord.Embed(
                    title="🔨 Ataque do Boss",
                    description=f"**{self.current_boss['name']}** atacou **{target.display_name}** causando {damage} de dano!",
                    color=discord.Color.dark_red()
                )
                await channel.send(embed=embed)

    @tasks.loop(minutes=5)
    async def boss_attack_task(self):
        """Tarefa que faz o boss atacar periodicamente."""
        await self.boss_attack_task_loop()

    async def award_wounds(self, user_id, amount):
        """Concede ferimentos ao jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "UPDATE players SET wounds = wounds + $1 WHERE user_id = $2",
                amount, user_id
            )
            # Verificar se o jogador está morto ou outras condições
            # Você pode adicionar lógica adicional aqui

    async def update_boss_phase(self):
        """Atualiza a fase do boss com base no HP restante."""
        if not self.current_boss:
            return

        hp_ratio = self.current_boss["current_hp"] / self.current_boss["hp"]

        # Fase 2
        if hp_ratio <= self.current_boss["phase_two_trigger"] and self.current_boss["phase"] < 2:
            self.current_boss["phase"] = 2
            embed = discord.Embed(
                title="🔥 Fase 2 do Boss!",
                description=f"O boss **{self.current_boss['name']}** entrou na Fase 2! Habilidades mais poderosas à vista.",
                color=discord.Color.orange()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)
            await self.activate_phase_two()

        # Fase 3
        elif hp_ratio <= self.current_boss["phase_three_trigger"] and self.current_boss["phase"] < 3:
            self.current_boss["phase"] = 3
            embed = discord.Embed(
                title="💀 Fase 3 do Boss!",
                description=f"O boss **{self.current_boss['name']}** entrou na Fase 3! Preparem-se para ataques devastadores.",
                color=discord.Color.dark_purple()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)
            await self.activate_phase_three()

    async def activate_phase_two(self):
        """Ativa as habilidades da fase 2 do boss."""
        abilities = self.current_boss["abilities"]["phase_two"]
        for ability in abilities:
            if ability == "Invocação de Minions" and not self.current_boss["minions_active"]:
                await self.summon_minions()
            elif ability == "Fúria Zumbi":
                self.current_boss["attack_power"] += 50
                await self.bot.get_channel(self.status_channel_id).send(
                    f"🔥 **{self.current_boss['name']}** aumentou seu poder de ataque!"
                )

    async def activate_phase_three(self):
        """Ativa as habilidades da fase 3 do boss."""
        abilities = self.current_boss["abilities"]["phase_three"]
        for ability in abilities:
            if ability == "Explosão Viral":
                await self.bot.get_channel(self.status_channel_id).send(
                    f"💉 **{self.current_boss['name']}** lançou uma Explosão Viral! Todos os jogadores receberão uma infecção."
                )
                await self.apply_group_infection()
            elif ability == "Ataque Devastador":
                self.current_boss["attack_power"] += 100
                await self.bot.get_channel(self.status_channel_id).send(
                    f"💀 **{self.current_boss['name']}** lançou um Ataque Devastador!"
                )
                # Aqui você pode implementar danos aos jogadores

    async def summon_minions(self):
        """Invoca minions durante o combate."""
        self.current_boss["minions_active"] = True
        minion_count = random.randint(2, 4)
        summoned_minions = random.sample(self.minions, minion_count)
        embed = discord.Embed(
            title="🧟 Minions Invocados!",
            description=f"**{self.current_boss['name']}** invocou os seguintes minions: {', '.join(summoned_minions)}.",
            color=discord.Color.dark_blue()
        )
        await self.bot.get_channel(self.status_channel_id).send(embed=embed)
        # Você pode adicionar lógica para que os minions ataquem os jogadores

    async def apply_group_infection(self):
        """Aplica infecção a todos os jogadores ativos no combate."""
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
                title="💉 Infecção em Grupo",
                description=f"**{self.current_boss['name']}** infectou os seguintes jogadores: {', '.join(infected_players)}!",
                color=discord.Color.dark_red()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)

    async def boss_attack_task_loop(self):
        """Task que faz o boss atacar periodicamente."""
        if self.current_boss:
            channel = self.bot.get_channel(self.status_channel_id)
            if channel is None:
                print(f"Canal com ID {self.status_channel_id} não encontrado.")
                return

            # Seleciona um jogador aleatório para atacar
            channel_combat = self.bot.get_channel(self.commands_channel_id)
            if channel_combat is None:
                print(f"Canal com ID {self.commands_channel_id} não encontrado.")
                return

            combat_members = [member for member in channel_combat.members if member.id != self.bot.user.id]
            if combat_members:
                target = random.choice(combat_members)
                damage = self.current_boss["attack_power"]
                # Aqui você pode implementar a lógica para aplicar dano ao jogador
                # Por exemplo, atualizar a coluna 'wounds' no banco de dados

                # Simulação de dano
                await self.award_wounds(target.id, damage)

                embed = discord.Embed(
                    title="🔨 Ataque do Boss",
                    description=f"**{self.current_boss['name']}** atacou **{target.display_name}** causando {damage} de dano!",
                    color=discord.Color.dark_red()
                )
                await channel.send(embed=embed)

    @tasks.loop(minutes=5)
    async def boss_attack_task(self):
        """Tarefa que faz o boss atacar periodicamente."""
        await self.boss_attack_task_loop()

    async def award_wounds(self, user_id, amount):
        """Concede ferimentos ao jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "UPDATE players SET wounds = wounds + $1 WHERE user_id = $2",
                amount, user_id
            )
            # Verificar se o jogador está morto ou outras condições
            # Você pode adicionar lógica adicional aqui

    async def update_boss_phase(self):
        """Atualiza a fase do boss com base no HP restante."""
        if not self.current_boss:
            return

        hp_ratio = self.current_boss["current_hp"] / self.current_boss["hp"]

        # Fase 2
        if hp_ratio <= self.current_boss["phase_two_trigger"] and self.current_boss["phase"] < 2:
            self.current_boss["phase"] = 2
            embed = discord.Embed(
                title="🔥 Fase 2 do Boss!",
                description=f"O boss **{self.current_boss['name']}** entrou na Fase 2! Habilidades mais poderosas à vista.",
                color=discord.Color.orange()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)
            await self.activate_phase_two()

        # Fase 3
        elif hp_ratio <= self.current_boss["phase_three_trigger"] and self.current_boss["phase"] < 3:
            self.current_boss["phase"] = 3
            embed = discord.Embed(
                title="💀 Fase 3 do Boss!",
                description=f"O boss **{self.current_boss['name']}** entrou na Fase 3! Preparem-se para ataques devastadores.",
                color=discord.Color.dark_purple()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)
            await self.activate_phase_three()

    async def activate_phase_two(self):
        """Ativa as habilidades da fase 2 do boss."""
        abilities = self.current_boss["abilities"]["phase_two"]
        for ability in abilities:
            if ability == "Invocação de Minions" and not self.current_boss["minions_active"]:
                await self.summon_minions()
            elif ability == "Fúria Zumbi":
                self.current_boss["attack_power"] += 50
                await self.bot.get_channel(self.status_channel_id).send(
                    f"🔥 **{self.current_boss['name']}** aumentou seu poder de ataque!"
                )

    async def activate_phase_three(self):
        """Ativa as habilidades da fase 3 do boss."""
        abilities = self.current_boss["abilities"]["phase_three"]
        for ability in abilities:
            if ability == "Explosão Viral":
                await self.bot.get_channel(self.status_channel_id).send(
                    f"💉 **{self.current_boss['name']}** lançou uma Explosão Viral! Todos os jogadores receberão uma infecção."
                )
                await self.apply_group_infection()
            elif ability == "Ataque Devastador":
                self.current_boss["attack_power"] += 100
                await self.bot.get_channel(self.status_channel_id).send(
                    f"💀 **{self.current_boss['name']}** lançou um Ataque Devastador!"
                )
                # Aqui você pode implementar danos aos jogadores

    async def summon_minions(self):
        """Invoca minions durante o combate."""
        self.current_boss["minions_active"] = True
        minion_count = random.randint(2, 4)
        summoned_minions = random.sample(self.minions, minion_count)
        embed = discord.Embed(
            title="🧟 Minions Invocados!",
            description=f"**{self.current_boss['name']}** invocou os seguintes minions: {', '.join(summoned_minions)}.",
            color=discord.Color.dark_blue()
        )
        await self.bot.get_channel(self.status_channel_id).send(embed=embed)
        # Você pode adicionar lógica para que os minions ataquem os jogadores

    async def apply_group_infection(self):
        """Aplica infecção a todos os jogadores ativos no combate."""
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
                title="💉 Infecção em Grupo",
                description=f"**{self.current_boss['name']}** infectou os seguintes jogadores: {', '.join(infected_players)}!",
                color=discord.Color.dark_red()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)

    async def boss_attack_task_loop(self):
        """Task que faz o boss atacar periodicamente."""
        if self.current_boss:
            channel = self.bot.get_channel(self.status_channel_id)
            if channel is None:
                print(f"Canal com ID {self.status_channel_id} não encontrado.")
                return

            # Seleciona um jogador aleatório para atacar
            channel_combat = self.bot.get_channel(self.commands_channel_id)
            if channel_combat is None:
                print(f"Canal com ID {self.commands_channel_id} não encontrado.")
                return

            combat_members = [member for member in channel_combat.members if member.id != self.bot.user.id]
            if combat_members:
                target = random.choice(combat_members)
                damage = self.current_boss["attack_power"]
                # Aqui você pode implementar a lógica para aplicar dano ao jogador
                # Por exemplo, atualizar a coluna 'wounds' no banco de dados

                # Simulação de dano
                await self.award_wounds(target.id, damage)

                embed = discord.Embed(
                    title="🔨 Ataque do Boss",
                    description=f"**{self.current_boss['name']}** atacou **{target.display_name}** causando {damage} de dano!",
                    color=discord.Color.dark_red()
                )
                await channel.send(embed=embed)

    @tasks.loop(minutes=5)
    async def boss_attack_task(self):
        """Tarefa que faz o boss atacar periodicamente."""
        await self.boss_attack_task_loop()

    async def award_wounds(self, user_id, amount):
        """Concede ferimentos ao jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "UPDATE players SET wounds = wounds + $1 WHERE user_id = $2",
                amount, user_id
            )
            # Verificar se o jogador está morto ou outras condições
            # Você pode adicionar lógica adicional aqui

    async def update_boss_phase(self):
        """Atualiza a fase do boss com base no HP restante."""
        if not self.current_boss:
            return

        hp_ratio = self.current_boss["current_hp"] / self.current_boss["hp"]

        # Fase 2
        if hp_ratio <= self.current_boss["phase_two_trigger"] and self.current_boss["phase"] < 2:
            self.current_boss["phase"] = 2
            embed = discord.Embed(
                title="🔥 Fase 2 do Boss!",
                description=f"O boss **{self.current_boss['name']}** entrou na Fase 2! Habilidades mais poderosas à vista.",
                color=discord.Color.orange()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)
            await self.activate_phase_two()

        # Fase 3
        elif hp_ratio <= self.current_boss["phase_three_trigger"] and self.current_boss["phase"] < 3:
            self.current_boss["phase"] = 3
            embed = discord.Embed(
                title="💀 Fase 3 do Boss!",
                description=f"O boss **{self.current_boss['name']}** entrou na Fase 3! Preparem-se para ataques devastadores.",
                color=discord.Color.dark_purple()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)
            await self.activate_phase_three()

    async def activate_phase_two(self):
        """Ativa as habilidades da fase 2 do boss."""
        abilities = self.current_boss["abilities"]["phase_two"]
        for ability in abilities:
            if ability == "Invocação de Minions" and not self.current_boss["minions_active"]:
                await self.summon_minions()
            elif ability == "Fúria Zumbi":
                self.current_boss["attack_power"] += 50
                await self.bot.get_channel(self.status_channel_id).send(
                    f"🔥 **{self.current_boss['name']}** aumentou seu poder de ataque!"
                )

    async def activate_phase_three(self):
        """Ativa as habilidades da fase 3 do boss."""
        abilities = self.current_boss["abilities"]["phase_three"]
        for ability in abilities:
            if ability == "Explosão Viral":
                await self.bot.get_channel(self.status_channel_id).send(
                    f"💉 **{self.current_boss['name']}** lançou uma Explosão Viral! Todos os jogadores receberão uma infecção."
                )
                await self.apply_group_infection()
            elif ability == "Ataque Devastador":
                self.current_boss["attack_power"] += 100
                await self.bot.get_channel(self.status_channel_id).send(
                    f"💀 **{self.current_boss['name']}** lançou um Ataque Devastador!"
                )
                # Aqui você pode implementar danos aos jogadores

    async def summon_minions(self):
        """Invoca minions durante o combate."""
        self.current_boss["minions_active"] = True
        minion_count = random.randint(2, 4)
        summoned_minions = random.sample(self.minions, minion_count)
        embed = discord.Embed(
            title="🧟 Minions Invocados!",
            description=f"**{self.current_boss['name']}** invocou os seguintes minions: {', '.join(summoned_minions)}.",
            color=discord.Color.dark_blue()
        )
        await self.bot.get_channel(self.status_channel_id).send(embed=embed)
        # Você pode adicionar lógica para que os minions ataquem os jogadores

    async def apply_group_infection(self):
        """Aplica infecção a todos os jogadores ativos no combate."""
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
                title="💉 Infecção em Grupo",
                description=f"**{self.current_boss['name']}** infectou os seguintes jogadores: {', '.join(infected_players)}!",
                color=discord.Color.dark_red()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)

    async def boss_attack_task_loop(self):
        """Task que faz o boss atacar periodicamente."""
        if self.current_boss:
            channel = self.bot.get_channel(self.status_channel_id)
            if channel is None:
                print(f"Canal com ID {self.status_channel_id} não encontrado.")
                return

            # Seleciona um jogador aleatório para atacar
            channel_combat = self.bot.get_channel(self.commands_channel_id)
            if channel_combat is None:
                print(f"Canal com ID {self.commands_channel_id} não encontrado.")
                return

            combat_members = [member for member in channel_combat.members if member.id != self.bot.user.id]
            if combat_members:
                target = random.choice(combat_members)
                damage = self.current_boss["attack_power"]
                # Aqui você pode implementar a lógica para aplicar dano ao jogador
                # Por exemplo, atualizar a coluna 'wounds' no banco de dados

                # Simulação de dano
                await self.award_wounds(target.id, damage)

                embed = discord.Embed(
                    title="🔨 Ataque do Boss",
                    description=f"**{self.current_boss['name']}** atacou **{target.display_name}** causando {damage} de dano!",
                    color=discord.Color.dark_red()
                )
                await channel.send(embed=embed)

    @tasks.loop(minutes=5)
    async def boss_attack_task(self):
        """Tarefa que faz o boss atacar periodicamente."""
        await self.boss_attack_task_loop()

    async def award_wounds(self, user_id, amount):
        """Concede ferimentos ao jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "UPDATE players SET wounds = wounds + $1 WHERE user_id = $2",
                amount, user_id
            )
            # Verificar se o jogador está morto ou outras condições
            # Você pode adicionar lógica adicional aqui

    async def update_boss_phase(self):
        """Atualiza a fase do boss com base no HP restante."""
        if not self.current_boss:
            return

        hp_ratio = self.current_boss["current_hp"] / self.current_boss["hp"]

        # Fase 2
        if hp_ratio <= self.current_boss["phase_two_trigger"] and self.current_boss["phase"] < 2:
            self.current_boss["phase"] = 2
            embed = discord.Embed(
                title="🔥 Fase 2 do Boss!",
                description=f"O boss **{self.current_boss['name']}** entrou na Fase 2! Habilidades mais poderosas à vista.",
                color=discord.Color.orange()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)
            await self.activate_phase_two()

        # Fase 3
        elif hp_ratio <= self.current_boss["phase_three_trigger"] and self.current_boss["phase"] < 3:
            self.current_boss["phase"] = 3
            embed = discord.Embed(
                title="💀 Fase 3 do Boss!",
                description=f"O boss **{self.current_boss['name']}** entrou na Fase 3! Preparem-se para ataques devastadores.",
                color=discord.Color.dark_purple()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)
            await self.activate_phase_three()

    async def activate_phase_two(self):
        """Ativa as habilidades da fase 2 do boss."""
        abilities = self.current_boss["abilities"]["phase_two"]
        for ability in abilities:
            if ability == "Invocação de Minions" and not self.current_boss["minions_active"]:
                await self.summon_minions()
            elif ability == "Fúria Zumbi":
                self.current_boss["attack_power"] += 50
                await self.bot.get_channel(self.status_channel_id).send(
                    f"🔥 **{self.current_boss['name']}** aumentou seu poder de ataque!"
                )

    async def activate_phase_three(self):
        """Ativa as habilidades da fase 3 do boss."""
        abilities = self.current_boss["abilities"]["phase_three"]
        for ability in abilities:
            if ability == "Explosão Viral":
                await self.bot.get_channel(self.status_channel_id).send(
                    f"💉 **{self.current_boss['name']}** lançou uma Explosão Viral! Todos os jogadores receberão uma infecção."
                )
                await self.apply_group_infection()
            elif ability == "Ataque Devastador":
                self.current_boss["attack_power"] += 100
                await self.bot.get_channel(self.status_channel_id).send(
                    f"💀 **{self.current_boss['name']}** lançou um Ataque Devastador!"
                )
                # Aqui você pode implementar danos aos jogadores

    async def summon_minions(self):
        """Invoca minions durante o combate."""
        self.current_boss["minions_active"] = True
        minion_count = random.randint(2, 4)
        summoned_minions = random.sample(self.minions, minion_count)
        embed = discord.Embed(
            title="🧟 Minions Invocados!",
            description=f"**{self.current_boss['name']}** invocou os seguintes minions: {', '.join(summoned_minions)}.",
            color=discord.Color.dark_blue()
        )
        await self.bot.get_channel(self.status_channel_id).send(embed=embed)
        # Você pode adicionar lógica para que os minions ataquem os jogadores

    async def apply_group_infection(self):
        """Aplica infecção a todos os jogadores ativos no combate."""
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
                title="💉 Infecção em Grupo",
                description=f"**{self.current_boss['name']}** infectou os seguintes jogadores: {', '.join(infected_players)}!",
                color=discord.Color.dark_red()
            )
            await self.bot.get_channel(self.status_channel_id).send(embed=embed)

    async def boss_attack_task_loop(self):
        """Task que faz o boss atacar periodicamente."""
        if self.current_boss:
            channel = self.bot.get_channel(self.status_channel_id)
            if channel is None:
                print(f"Canal com ID {self.status_channel_id} não encontrado.")
                return

            # Seleciona um jogador aleatório para atacar
            channel_combat = self.bot.get_channel(self.commands_channel_id)
            if channel_combat is None:
                print(f"Canal com ID {self.commands_channel_id} não encontrado.")
                return

            combat_members = [member for member in channel_combat.members if member.id != self.bot.user.id]
            if combat_members:
                target = random.choice(combat_members)
                damage = self.current_boss["attack_power"]
                # Aqui você pode implementar a lógica para aplicar dano ao jogador
                # Por exemplo, atualizar a coluna 'wounds' no banco de dados

                # Simulação de dano
                await self.award_wounds(target.id, damage)

                embed = discord.Embed(
                    title="🔨 Ataque do Boss",
                    description=f"**{self.current_boss['name']}** atacou **{target.display_name}** causando {damage} de dano!",
                    color=discord.Color.dark_red()
                )
                await channel.send(embed=embed)

    @tasks.loop(minutes=5)
    async def boss_attack_task(self):
        """Tarefa que faz o boss atacar periodicamente."""
        await self.boss_attack_task_loop()

    async def award_wounds(self, user_id, amount):
        """Concede ferimentos ao jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "UPDATE players SET wounds = wounds + $1 WHERE user_id = $2",
                amount, user_id
            )
            # Aqui você pode adicionar lógica para verificar se o jogador está morto ou outras condições

    async def apply_infection(self, user_id):
        """Aplica infecção ao jogador com base em chance."""
        chance = random.randint(1, 100)
        if chance <= 20:  # 20% de chance de infecção
            async with self.bot.pool.acquire() as connection:
                await connection.execute("UPDATE players SET infected = TRUE WHERE user_id = $1", user_id)
            member = self.bot.get_user(user_id)
            if member:
                await self.bot.get_channel(self.status_channel_id).send(
                    f"⚠️ {member.display_name} foi infectado durante o combate!"
                )

    async def apply_damage_debuff(self, user_id):
        """Aplica debuff de dano ao jogador com base em chance."""
        chance = random.randint(1, 100)
        if chance <= 15:  # 15% de chance de debuff
            async with self.bot.pool.acquire() as connection:
                await connection.execute("UPDATE players SET damage_debuff = TRUE WHERE user_id = $1", user_id)
            member = self.bot.get_user(user_id)
            if member:
                await self.bot.get_channel(self.status_channel_id).send(
                    f"⚠️ {member.display_name} recebeu um debuff de dano!"
                )

    async def award_xp(self, user_id, amount):
        """Concede XP ao jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "UPDATE players SET xp = xp + $1 WHERE user_id = $2",
                amount, user_id
            )

    async def award_money(self, user_id, amount):
        """Concede dinheiro ao jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "UPDATE players SET money = money + $1 WHERE user_id = $2",
                amount, user_id
            )

    @commands.command(name="boss status")
    async def boss_status(self, ctx):
        """Exibe o status atual do boss."""
        if not self.current_boss:
            await ctx.send("⚔️ Não há nenhum boss ativo no momento.")
            return

        embed = discord.Embed(
            title=f"⚔️ Status do Boss: {self.current_boss['name']}",
            description=f"**HP:** {self.current_boss['current_hp']}/{self.current_boss['hp']}\n"
                        f"**Fase:** {self.current_boss['phase']}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.command(name="boss stats")
    async def boss_stats(self, ctx):
        """Exibe as estatísticas do jogador."""
        user_id = ctx.author.id
        await self.ensure_player(user_id)

        async with self.bot.pool.acquire() as connection:
            result = await connection.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)

        if not result:
            await ctx.send("⚠️ Não foi possível encontrar seu perfil. Tente novamente.")
            return

        embed = discord.Embed(
            title=f"📊 Estatísticas de {ctx.author.display_name}",
            color=discord.Color.purple()
        )
        embed.add_field(name="Nível", value=result['level'], inline=True)
        embed.add_field(name="XP", value=result['xp'], inline=True)
        embed.add_field(name="Dinheiro", value=result['money'], inline=True)
        embed.add_field(name="Ferimentos", value=result['wounds'], inline=True)
        embed.add_field(name="Infectado", value="Sim" if result['infected'] else "Não", inline=True)
        embed.add_field(name="Debuff de Dano", value="Sim" if result['damage_debuff'] else "Não", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="boss inventory")
    async def boss_inventory(self, ctx):
        """Exibe o inventário do jogador."""
        user_id = ctx.author.id
        await self.ensure_player(user_id)

        async with self.bot.pool.acquire() as connection:
            items = await connection.fetch("SELECT item FROM inventory WHERE user_id = $1", user_id)

        if not items:
            await ctx.send("📦 Seu inventário está vazio.")
            return

        inventory_list = "\n".join([f"- {item['item']}" for item in items])
        embed = discord.Embed(
            title=f"📦 Inventário de {ctx.author.display_name}",
            description=inventory_list,
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="boss use")
    async def boss_use_item(self, ctx, *, item_name: str = None):
        """Permite que o jogador use um item do inventário."""
        if not item_name:
            await ctx.send("⚠️ Por favor, especifique o item que deseja usar. Exemplo: `n!boss use Remédio Antiviral`")
            return

        user_id = ctx.author.id
        await self.ensure_player(user_id)

        async with self.bot.pool.acquire() as connection:
            # Verifica se o jogador possui o item
            item = await connection.fetchrow(
                "SELECT * FROM inventory WHERE user_id = $1 AND item ILIKE $2",
                user_id, f"%{item_name}%"
            )

            if not item:
                await ctx.send(f"⚠️ Você não possui o item **{item_name}** no seu inventário.")
                return

            # Remove o item do inventário
            await connection.execute(
                "DELETE FROM inventory WHERE id = $1",
                item['id']
            )

            # Aplica o efeito do item
            if item['item'] == self.consumables['antiviral']:
                # Remove infecção
                await connection.execute(
                    "UPDATE players SET infected = FALSE WHERE user_id = $1",
                    user_id
                )
                await ctx.send(f"💊 **{ctx.author.display_name}** usou **{item['item']}** e curou a infecção!")
            elif item['item'] == self.consumables['soro']:
                # Remove debuff de dano
                await connection.execute(
                    "UPDATE players SET damage_debuff = FALSE WHERE user_id = $1",
                    user_id
                )
                await ctx.send(f"💉 **{ctx.author.display_name}** usou **{item['item']}** e removeu o debuff de dano!")
            else:
                await ctx.send(f"🔮 **{ctx.author.display_name}** usou **{item['item']}**, mas não há efeitos definidos para este item.")

    @commands.command(name="boss help")
    async def boss_help(self, ctx):
        """Exibe a ajuda dos comandos relacionados ao boss."""
        embed = discord.Embed(
            title="📜 Ajuda dos Comandos do Boss",
            color=discord.Color.gold()
        )
        embed.add_field(name="!boss", value="Invoca ou ataca o boss. Use no canal designado para combates.", inline=False)
        embed.add_field(name="!boss status", value="Exibe o status atual do boss.", inline=False)
        embed.add_field(name="!boss stats", value="Exibe suas estatísticas pessoais.", inline=False)
        embed.add_field(name="!boss inventory", value="Exibe seu inventário de itens.", inline=False)
        embed.add_field(name="!boss use <item>", value="Usa um item do seu inventário. Exemplo: `n!boss use Remédio Antiviral`", inline=False)
        embed.add_field(name="!boss help", value="Exibe esta mensagem de ajuda.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="profile")
    async def profile_command(self, ctx):
        """Exibe o perfil do jogador."""
        await self.boss_stats(ctx)  # Reutiliza a função de stats

    @commands.command(name="inventory")
    async def inventory_command(self, ctx):
        """Exibe o inventário do jogador."""
        await self.boss_inventory(ctx)  # Reutiliza a função de inventário

    @commands.command(name="use")
    async def use_item_command(self, ctx, *, item_name: str = None):
        """Permite que o jogador use um item do inventário."""
        await self.boss_use_item(ctx, item_name=item_name)  # Reutiliza a função de usar item

    @commands.command(name="stats")
    async def stats_command(self, ctx):
        """Exibe as estatísticas do jogador."""
        await self.boss_stats(ctx)  # Reutiliza a função de stats

    @commands.command(name="help")
    async def help_command(self, ctx):
        """Exibe a ajuda dos comandos do bot."""
        await self.boss_help(ctx)  # Reutiliza a função de ajuda

    # Sistema de XP e Level
    async def check_level_up(self, user_id):
        """Verifica se o jogador subiu de nível."""
        async with self.bot.pool.acquire() as connection:
            result = await connection.fetchrow("SELECT xp, level FROM players WHERE user_id = $1", user_id)
            if result:
                xp = result['xp']
                level = result['level']
                # Define a fórmula de XP para subir de nível (exemplo: 100 * level)
                xp_for_next_level = 100 * level
                if xp >= xp_for_next_level:
                    await connection.execute(
                        "UPDATE players SET level = level + 1, xp = xp - $1 WHERE user_id = $2",
                        xp_for_next_level, user_id
                    )
                    member = self.bot.get_user(user_id)
                    if member:
                        await self.bot.get_channel(self.status_channel_id).send(
                            f"🎉 Parabéns {member.display_name}! Você subiu para o nível {level + 1}!"
                        )

    # Sistema de uso de consumíveis
    async def use_consumable(self, user_id, item_name):
        """Permite que o jogador use um consumível."""
        async with self.bot.pool.acquire() as connection:
            # Verifica se o jogador possui o item
            item = await connection.fetchrow(
                "SELECT * FROM inventory WHERE user_id = $1 AND item ILIKE $2",
                user_id, f"%{item_name}%"
            )

            if not item:
                return False, f"⚠️ Você não possui o item **{item_name}** no seu inventário."

            # Remove o item do inventário
            await connection.execute(
                "DELETE FROM inventory WHERE id = $1",
                item['id']
            )

            # Aplica o efeito do item
            if item['item'] == self.consumables['antiviral']:
                # Remove infecção
                await connection.execute(
                    "UPDATE players SET infected = FALSE WHERE user_id = $1",
                    user_id
                )
                return True, f"💊 Você usou **{item['item']}** e curou a infecção!"
            elif item['item'] == self.consumables['soro']:
                # Remove debuff de dano
                await connection.execute(
                    "UPDATE players SET damage_debuff = FALSE WHERE user_id = $1",
                    user_id
                )
                return True, f"💉 Você usou **{item['item']}** e removeu o debuff de dano!"
            else:
                return False, f"🔮 O item **{item['item']}** não possui efeitos definidos."

    # Verificar se há uma invocação de boss ativa e garantir que múltiplos usuários possam interagir
    @commands.command(name="boss")
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hora de cooldown por usuário
    async def boss_command(self, ctx):
        # ... (Manter o código existente conforme acima)
        pass  # O código já está detalhado anteriormente

    @commands.command(name="rank")
    async def rank_command(self, ctx):
        """Exibe o ranking dos melhores jogadores."""
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
        await ctx.send(embed=embed)

    # Sistema de inventário e uso de consumíveis
    @commands.command(name="use")
    async def use_item_command(self, ctx, *, item_name: str = None):
        """Permite que o jogador use um item do inventário."""
        if not item_name:
            await ctx.send("⚠️ Por favor, especifique o item que deseja usar. Exemplo: `n!use Remédio Antiviral`")
            return

        user_id = ctx.author.id
        await self.ensure_player(user_id)

        success, message = await self.use_consumable(user_id, item_name)
        await ctx.send(message)

    # Comandos de perfil e inventário
    @commands.command(name="profile")
    async def profile_command(self, ctx):
        """Exibe o perfil do jogador."""
        await self.boss_stats(ctx)  # Reutiliza a função de stats

    @commands.command(name="inventory")
    async def inventory_command(self, ctx):
        """Exibe o inventário do jogador."""
        await self.boss_inventory(ctx)  # Reutiliza a função de inventário

    @commands.command(name="stats")
    async def stats_command(self, ctx):
        """Exibe as estatísticas do jogador."""
        await self.boss_stats(ctx)  # Reutiliza a função de stats

    @commands.command(name="help")
    async def help_command(self, ctx):
        """Exibe a ajuda dos comandos do bot."""
        await self.boss_help(ctx)  # Reutiliza a função de ajuda

    @commands.command(name="boss help")
    async def boss_help_command(self, ctx):
        """Exibe a ajuda dos comandos relacionados ao boss."""
        await self.boss_help(ctx)  # Reutiliza a função de ajuda

    @commands.command(name="boss rank")
    async def boss_rank_command(self, ctx):
        """Exibe o ranking dos melhores jogadores."""
        await self.rank_command(ctx)

    @commands.command(name="boss use")
    async def boss_use_item_command(self, ctx, *, item_name: str = None):
        """Permite que o jogador use um item do inventário."""
        await self.boss_use_item(ctx, item_name=item_name)

    # Sistema de verificação e atualização de perfil
    @commands.command(name="boss profile")
    async def boss_profile_command(self, ctx):
        """Exibe o perfil do jogador."""
        await self.profile_command(ctx)

    # Sistema de verificação de inventário
    @commands.command(name="boss inventory")
    async def boss_inventory_command(self, ctx):
        """Exibe o inventário do jogador."""
        await self.inventory_command(ctx)

    # Sistema de exibição de estatísticas
    @commands.command(name="boss stats")
    async def boss_stats_command(self, ctx):
        """Exibe as estatísticas do jogador."""
        await self.stats_command(ctx)

    # Sistema de ajuda aprimorado
    @commands.command(name="boss help")
    async def boss_help_command(self, ctx):
        """Exibe a ajuda dos comandos relacionados ao boss."""
        await self.help_command(ctx)

    # Sistema de ranking aprimorado
    @commands.command(name="boss rank")
    async def boss_rank_command(self, ctx):
        """Exibe o ranking dos melhores jogadores."""
        await self.rank_command(ctx)

    # Sistema de uso de consumíveis aprimorado
    @commands.command(name="boss use")
    async def boss_use_item_command(self, ctx, *, item_name: str = None):
        """Permite que o jogador use um item do inventário."""
        await self.use_item_command(ctx, item_name=item_name)

    # Sistema de atualização de ranking a cada 2 horas
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

    @rank_update.before_loop
    async def before_rank_update(self):
        await self.bot.wait_until_ready()

    # Sistema de status do bot a cada 10 minutos
    @tasks.loop(minutes=10)
    async def change_status(self):
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
        new_status = random.choice(status_messages)
        await self.bot.change_presence(activity=discord.Game(new_status))

    @change_status.before_loop
    async def before_change_status(self):
        await self.bot.wait_until_ready()

    @commands.command(name="boss help")
    async def boss_help(self, ctx):
        """Exibe a ajuda dos comandos relacionados ao boss."""
        embed = discord.Embed(
            title="📜 Ajuda dos Comandos do Boss",
            color=discord.Color.gold()
        )
        embed.add_field(name="!boss", value="Invoca ou ataca o boss. Use no canal designado para combates.", inline=False)
        embed.add_field(name="!boss status", value="Exibe o status atual do boss.", inline=False)
        embed.add_field(name="!boss stats", value="Exibe suas estatísticas pessoais.", inline=False)
        embed.add_field(name="!boss inventory", value="Exibe seu inventário de itens.", inline=False)
        embed.add_field(name="!boss use <item>", value="Usa um item do seu inventário. Exemplo: `n!boss use Remédio Antiviral`", inline=False)
        embed.add_field(name="!boss rank", value="Exibe o ranking dos melhores jogadores.", inline=False)
        embed.add_field(name="!boss help", value="Exibe esta mensagem de ajuda.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="boss stats")
    async def boss_stats(self, ctx):
        """Exibe as estatísticas do jogador."""
        user_id = ctx.author.id
        await self.ensure_player(user_id)

        async with self.bot.pool.acquire() as connection:
            result = await connection.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)

        if not result:
            await ctx.send("⚠️ Não foi possível encontrar seu perfil. Tente novamente.")
            return

        embed = discord.Embed(
            title=f"📊 Estatísticas de {ctx.author.display_name}",
            color=discord.Color.purple()
        )
        embed.add_field(name="Nível", value=result['level'], inline=True)
        embed.add_field(name="XP", value=result['xp'], inline=True)
        embed.add_field(name="Dinheiro", value=result['money'], inline=True)
        embed.add_field(name="Ferimentos", value=result['wounds'], inline=True)
        embed.add_field(name="Infectado", value="Sim" if result['infected'] else "Não", inline=True)
        embed.add_field(name="Debuff de Dano", value="Sim" if result['damage_debuff'] else "Não", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="boss inventory")
    async def boss_inventory(self, ctx):
        """Exibe o inventário do jogador."""
        user_id = ctx.author.id
        await self.ensure_player(user_id)

        async with self.bot.pool.acquire() as connection:
            items = await connection.fetch("SELECT item FROM inventory WHERE user_id = $1", user_id)

        if not items:
            await ctx.send("📦 Seu inventário está vazio.")
            return

        inventory_list = "\n".join([f"- {item['item']}" for item in items])
        embed = discord.Embed(
            title=f"📦 Inventário de {ctx.author.display_name}",
            description=inventory_list,
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="boss use")
    async def boss_use_item(self, ctx, *, item_name: str = None):
        """Permite que o jogador use um item do inventário."""
        if not item_name:
            await ctx.send("⚠️ Por favor, especifique o item que deseja usar. Exemplo: `n!boss use Remédio Antiviral`")
            return

        user_id = ctx.author.id
        await self.ensure_player(user_id)

        success, message = await self.use_consumable(user_id, item_name)
        await ctx.send(message)

    @commands.command(name="boss stats")
    async def boss_stats_command(self, ctx):
        """Exibe as estatísticas do jogador."""
        await self.boss_stats(ctx)

    @commands.command(name="boss inventory")
    async def boss_inventory_command(self, ctx):
        """Exibe o inventário do jogador."""
        await self.boss_inventory(ctx)

    @commands.command(name="boss rank")
    async def boss_rank_command(self, ctx):
        """Exibe o ranking dos melhores jogadores."""
        await self.rank_command(ctx)

    @commands.command(name="boss help")
    async def boss_help_command(self, ctx):
        """Exibe a ajuda dos comandos relacionados ao boss."""
        await self.boss_help(ctx)

    # Sistema de ajuda aprimorado
    @commands.command(name="boss help")
    async def boss_help(self, ctx):
        """Exibe a ajuda dos comandos relacionados ao boss."""
        embed = discord.Embed(
            title="📜 Ajuda dos Comandos do Boss",
            color=discord.Color.gold()
        )
        embed.add_field(name="!boss", value="Invoca ou ataca o boss. Use no canal designado para combates.", inline=False)
        embed.add_field(name="!boss status", value="Exibe o status atual do boss.", inline=False)
        embed.add_field(name="!boss stats", value="Exibe suas estatísticas pessoais.", inline=False)
        embed.add_field(name="!boss inventory", value="Exibe seu inventário de itens.", inline=False)
        embed.add_field(name="!boss use <item>", value="Usa um item do seu inventário. Exemplo: `n!boss use Remédio Antiviral`", inline=False)
        embed.add_field(name="!boss rank", value="Exibe o ranking dos melhores jogadores.", inline=False)
        embed.add_field(name="!boss help", value="Exibe esta mensagem de ajuda.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="rank")
    async def rank_command(self, ctx):
        """Exibe o ranking dos melhores jogadores."""
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
        await ctx.send(embed=embed)

    @commands.command(name="help")
    async def help_command(self, ctx):
        """Exibe a ajuda dos comandos do bot."""
        embed = discord.Embed(
            title="📜 Ajuda dos Comandos do Bot",
            color=discord.Color.gold()
        )
        embed.add_field(name="!boss", value="Invoca ou ataca o boss. Use no canal designado para combates.", inline=False)
        embed.add_field(name="!boss status", value="Exibe o status atual do boss.", inline=False)
        embed.add_field(name="!boss stats", value="Exibe suas estatísticas pessoais.", inline=False)
        embed.add_field(name="!boss inventory", value="Exibe seu inventário de itens.", inline=False)
        embed.add_field(name="!boss use <item>", value="Usa um item do seu inventário. Exemplo: `n!boss use Remédio Antiviral`", inline=False)
        embed.add_field(name="!boss rank", value="Exibe o ranking dos melhores jogadores.", inline=False)
        embed.add_field(name="!boss help", value="Exibe esta mensagem de ajuda.", inline=False)
        await ctx.send(embed=embed)

    # Sistema de mudança de status do bot
    @tasks.loop(minutes=10)
    async def change_status(self):
        """Atualiza o status do bot aleatoriamente a cada 10 minutos."""
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
        new_status = random.choice(status_messages)
        await self.bot.change_presence(activity=discord.Game(new_status))

    @change_status.before_loop
    async def before_change_status(self):
        await self.bot.wait_until_ready()

    # Sistema de ranking a cada 2 horas
    @tasks.loop(hours=2)
    async def rank_update(self):
        """Atualiza o ranking dos melhores jogadores a cada 2 horas."""
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

    @rank_update.before_loop
    async def before_rank_update(self):
        await self.bot.wait_until_ready()

    # Sistema de atualização de status a cada 10 minutos
    @tasks.loop(minutes=10)
    async def status_update(self):
        """Atualiza o status do bot a cada 10 minutos."""
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
        new_status = random.choice(status_messages)
        await self.bot.change_presence(activity=discord.Game(new_status))

    @status_update.before_loop
    async def before_status_update(self):
        await self.bot.wait_until_ready()

    # Sistema de help do boss
    @commands.command(name="boss help")
    async def boss_help_command(self, ctx):
        """Exibe a ajuda dos comandos relacionados ao boss."""
        embed = discord.Embed(
            title="📜 Ajuda dos Comandos do Boss",
            color=discord.Color.gold()
        )
        embed.add_field(name="!boss", value="Invoca ou ataca o boss. Use no canal designado para combates.", inline=False)
        embed.add_field(name="!boss status", value="Exibe o status atual do boss.", inline=False)
        embed.add_field(name="!boss stats", value="Exibe suas estatísticas pessoais.", inline=False)
        embed.add_field(name="!boss inventory", value="Exibe seu inventário de itens.", inline=False)
        embed.add_field(name="!boss use <item>", value="Usa um item do seu inventário. Exemplo: `n!boss use Remédio Antiviral`", inline=False)
        embed.add_field(name="!boss rank", value="Exibe o ranking dos melhores jogadores.", inline=False)
        embed.add_field(name="!boss help", value="Exibe esta mensagem de ajuda.", inline=False)
        await ctx.send(embed=embed)

    # Sistema de perfil e inventário via comandos padrão
    @commands.command(name="profile")
    async def profile_command(self, ctx):
        """Exibe o perfil do jogador."""
        await self.boss_stats(ctx)  # Reutiliza a função de stats

    @commands.command(name="inventory")
    async def inventory_command(self, ctx):
        """Exibe o inventário do jogador."""
        await self.boss_inventory(ctx)  # Reutiliza a função de inventário

    @commands.command(name="use")
    async def use_item_command(self, ctx, *, item_name: str = None):
        """Permite que o jogador use um item do inventário."""
        await self.boss_use_item(ctx, item_name=item_name)  # Reutiliza a função de usar item

    @commands.command(name="stats")
    async def stats_command(self, ctx):
        """Exibe as estatísticas do jogador."""
        await self.boss_stats(ctx)  # Reutiliza a função de stats

    @commands.command(name="help")
    async def help_command(self, ctx):
        """Exibe a ajuda dos comandos do bot."""
        await self.boss_help(ctx)  # Reutiliza a função de ajuda

    # Sistema de atualização de status do bot
    @tasks.loop(minutes=10)
    async def change_status(self):
        """Atualiza o status do bot aleatoriamente a cada 10 minutos."""
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
        new_status = random.choice(status_messages)
        await self.bot.change_presence(activity=discord.Game(new_status))

    @change_status.before_loop
    async def before_change_status(self):
        await self.bot.wait_until_ready()

    # Sistema de atualização de ranking a cada 2 horas
    @tasks.loop(hours=2)
    async def rank_update(self):
        """Atualiza o ranking dos melhores jogadores a cada 2 horas."""
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

    @rank_update.before_loop
    async def before_rank_update(self):
        await self.bot.wait_until_ready()

    # Sistema de help aprimorado
    @commands.command(name="boss help")
    async def boss_help(self, ctx):
        """Exibe a ajuda dos comandos relacionados ao boss."""
        embed = discord.Embed(
            title="📜 Ajuda dos Comandos do Boss",
            color=discord.Color.gold()
        )
        embed.add_field(name="!boss", value="Invoca ou ataca o boss. Use no canal designado para combates.", inline=False)
        embed.add_field(name="!boss status", value="Exibe o status atual do boss.", inline=False)
        embed.add_field(name="!boss stats", value="Exibe suas estatísticas pessoais.", inline=False)
        embed.add_field(name="!boss inventory", value="Exibe seu inventário de itens.", inline=False)
        embed.add_field(name="!boss use <item>", value="Usa um item do seu inventário. Exemplo: `n!boss use Remédio Antiviral`", inline=False)
        embed.add_field(name="!boss rank", value="Exibe o ranking dos melhores jogadores.", inline=False)
        embed.add_field(name="!boss help", value="Exibe esta mensagem de ajuda.", inline=False)
        await ctx.send(embed=embed)

    # Sistema de profile e inventory via comandos padrão
    @commands.command(name="profile")
    async def profile_command(self, ctx):
        """Exibe o perfil do jogador."""
        await self.boss_stats(ctx)  # Reutiliza a função de stats

    @commands.command(name="inventory")
    async def inventory_command(self, ctx):
        """Exibe o inventário do jogador."""
        await self.boss_inventory(ctx)  # Reutiliza a função de inventário

    @commands.command(name="use")
    async def use_item_command(self, ctx, *, item_name: str = None):
        """Permite que o jogador use um item do inventário."""
        await self.boss_use_item(ctx, item_name=item_name)  # Reutiliza a função de usar item

    @commands.command(name="stats")
    async def stats_command(self, ctx):
        """Exibe as estatísticas do jogador."""
        await self.boss_stats(ctx)  # Reutiliza a função de stats

    @commands.command(name="help")
    async def help_command(self, ctx):
        """Exibe a ajuda dos comandos do bot."""
        await self.boss_help(ctx)  # Reutiliza a função de ajuda

    # Sistema de mudança de status do bot
    @tasks.loop(minutes=10)
    async def change_status(self):
        """Atualiza o status do bot aleatoriamente a cada 10 minutos."""
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
        new_status = random.choice(status_messages)
        await self.bot.change_presence(activity=discord.Game(new_status))

    @change_status.before_loop
    async def before_change_status(self):
        await self.bot.wait_until_ready()

    # Sistema de ranking a cada 2 horas
    @tasks.loop(hours=2)
    async def rank_update(self):
        """Atualiza o ranking dos melhores jogadores a cada 2 horas."""
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

    @rank_update.before_loop
    async def before_rank_update(self):
        await self.bot.wait_until_ready()

    # Sistema de ajuda aprimorado
    @commands.command(name="boss help")
    async def boss_help_command(self, ctx):
        """Exibe a ajuda dos comandos relacionados ao boss."""
        embed = discord.Embed(
            title="📜 Ajuda dos Comandos do Boss",
            color=discord.Color.gold()
        )
        embed.add_field(name="!boss", value="Invoca ou ataca o boss. Use no canal designado para combates.", inline=False)
        embed.add_field(name="!boss status", value="Exibe o status atual do boss.", inline=False)
        embed.add_field(name="!boss stats", value="Exibe suas estatísticas pessoais.", inline=False)
        embed.add_field(name="!boss inventory", value="Exibe seu inventário de itens.", inline=False)
        embed.add_field(name="!boss use <item>", value="Usa um item do seu inventário. Exemplo: `n!boss use Remédio Antiviral`", inline=False)
        embed.add_field(name="!boss rank", value="Exibe o ranking dos melhores jogadores.", inline=False)
        embed.add_field(name="!boss help", value="Exibe esta mensagem de ajuda.", inline=False)
        await ctx.send(embed=embed)

    async def setup(self, ctx):
        """Configurações iniciais do cog."""
        await self.ensure_player(ctx.author.id)

    # Comandos adicionais para melhorar a experiência do jogador
    @commands.command(name="use")
    async def use_item_command(self, ctx, *, item_name: str = None):
        """Permite que o jogador use um item do inventário."""
        if not item_name:
            await ctx.send("⚠️ Por favor, especifique o item que deseja usar. Exemplo: `n!use Remédio Antiviral`")
            return

        user_id = ctx.author.id
        await self.ensure_player(user_id)

        success, message = await self.use_consumable(user_id, item_name)
        await ctx.send(message)

    async def use_consumable(self, user_id, item_name):
        """Permite que o jogador use um consumível."""
        async with self.bot.pool.acquire() as connection:
            # Verifica se o jogador possui o item
            item = await connection.fetchrow(
                "SELECT * FROM inventory WHERE user_id = $1 AND item ILIKE $2",
                user_id, f"%{item_name}%"
            )

            if not item:
                return False, f"⚠️ Você não possui o item **{item_name}** no seu inventário."

            # Remove o item do inventário
            await connection.execute(
                "DELETE FROM inventory WHERE id = $1",
                item['id']
            )

            # Aplica o efeito do item
            if item['item'] == self.consumables['antiviral']:
                # Remove infecção
                await connection.execute(
                    "UPDATE players SET infected = FALSE WHERE user_id = $1",
                    user_id
                )
                return True, f"💊 Você usou **{item['item']}** e curou a infecção!"
            elif item['item'] == self.consumables['soro']:
                # Remove debuff de dano
                await connection.execute(
                    "UPDATE players SET damage_debuff = FALSE WHERE user_id = $1",
                    user_id
                )
                return True, f"💉 Você usou **{item['item']}** e removeu o debuff de dano!"
            else:
                return False, f"🔮 O item **{item['item']}** não possui efeitos definidos."

    # Sistema de status do boss
    @commands.command(name="boss status")
    async def boss_status_command(self, ctx):
        """Exibe o status atual do boss."""
        if not self.current_boss:
            await ctx.send("⚔️ Não há nenhum boss ativo no momento.")
            return

        embed = discord.Embed(
            title=f"⚔️ Status do Boss: {self.current_boss['name']}",
            description=f"**HP:** {self.current_boss['current_hp']}/{self.current_boss['hp']}\n"
                        f"**Fase:** {self.current_boss['phase']}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    # Sistema de estatísticas do jogador
    @commands.command(name="boss stats")
    async def boss_stats(self, ctx):
        """Exibe as estatísticas do jogador."""
        user_id = ctx.author.id
        await self.ensure_player(user_id)

        async with self.bot.pool.acquire() as connection:
            result = await connection.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)

        if not result:
            await ctx.send("⚠️ Não foi possível encontrar seu perfil. Tente novamente.")
            return

        embed = discord.Embed(
            title=f"📊 Estatísticas de {ctx.author.display_name}",
            color=discord.Color.purple()
        )
        embed.add_field(name="Nível", value=result['level'], inline=True)
        embed.add_field(name="XP", value=result['xp'], inline=True)
        embed.add_field(name="Dinheiro", value=result['money'], inline=True)
        embed.add_field(name="Ferimentos", value=result['wounds'], inline=True)
        embed.add_field(name="Infectado", value="Sim" if result['infected'] else "Não", inline=True)
        embed.add_field(name="Debuff de Dano", value="Sim" if result['damage_debuff'] else "Não", inline=True)
        await ctx.send(embed=embed)

    # Sistema de inventário do jogador
    @commands.command(name="boss inventory")
    async def boss_inventory(self, ctx):
        """Exibe o inventário do jogador."""
        user_id = ctx.author.id
        await self.ensure_player(user_id)

        async with self.bot.pool.acquire() as connection:
            items = await connection.fetch("SELECT item FROM inventory WHERE user_id = $1", user_id)

        if not items:
            await ctx.send("📦 Seu inventário está vazio.")
            return

        inventory_list = "\n".join([f"- {item['item']}" for item in items])
        embed = discord.Embed(
            title=f"📦 Inventário de {ctx.author.display_name}",
            description=inventory_list,
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # Sistema de uso de consumíveis
    @commands.command(name="boss use")
    async def boss_use_item(self, ctx, *, item_name: str = None):
        """Permite que o jogador use um item do inventário."""
        if not item_name:
            await ctx.send("⚠️ Por favor, especifique o item que deseja usar. Exemplo: `n!boss use Remédio Antiviral`")
            return

        user_id = ctx.author.id
        await self.ensure_player(user_id)

        success, message = await self.use_consumable(user_id, item_name)
        await ctx.send(message)

    # Sistema de ranking
    @commands.command(name="boss rank")
    async def boss_rank_command(self, ctx):
        """Exibe o ranking dos melhores jogadores."""
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
        await ctx.send(embed=embed)

    # Sistema de ajuda
    @commands.command(name="boss help")
    async def boss_help(self, ctx):
        """Exibe a ajuda dos comandos relacionados ao boss."""
        embed = discord.Embed(
            title="📜 Ajuda dos Comandos do Boss",
            color=discord.Color.gold()
        )
        embed.add_field(name="!boss", value="Invoca ou ataca o boss. Use no canal designado para combates.", inline=False)
        embed.add_field(name="!boss status", value="Exibe o status atual do boss.", inline=False)
        embed.add_field(name="!boss stats", value="Exibe suas estatísticas pessoais.", inline=False)
        embed.add_field(name="!boss inventory", value="Exibe seu inventário de itens.", inline=False)
        embed.add_field(name="!boss use <item>", value="Usa um item do seu inventário. Exemplo: `n!boss use Remédio Antiviral`", inline=False)
        embed.add_field(name="!boss rank", value="Exibe o ranking dos melhores jogadores.", inline=False)
        embed.add_field(name="!boss help", value="Exibe esta mensagem de ajuda.", inline=False)
        await ctx.send(embed=embed)

    # Sistema de help via comandos padrão
    @commands.command(name="help")
    async def help_command(self, ctx):
        """Exibe a ajuda dos comandos do bot."""
        embed = discord.Embed(
            title="📜 Ajuda dos Comandos do Bot",
            color=discord.Color.gold()
        )
        embed.add_field(name="!boss", value="Invoca ou ataca o boss. Use no canal designado para combates.", inline=False)
        embed.add_field(name="!boss status", value="Exibe o status atual do boss.", inline=False)
        embed.add_field(name="!boss stats", value="Exibe suas estatísticas pessoais.", inline=False)
        embed.add_field(name="!boss inventory", value="Exibe seu inventário de itens.", inline=False)
        embed.add_field(name="!boss use <item>", value="Usa um item do seu inventário. Exemplo: `n!boss use Remédio Antiviral`", inline=False)
        embed.add_field(name="!boss rank", value="Exibe o ranking dos melhores jogadores.", inline=False)
        embed.add_field(name="!boss help", value="Exibe esta mensagem de ajuda.", inline=False)
        await ctx.send(embed=embed)

    # Sistema de perfil via comandos padrão
    @commands.command(name="profile")
    async def profile_command(self, ctx):
        """Exibe o perfil do jogador."""
        await self.boss_stats(ctx)  # Reutiliza a função de stats

    # Sistema de inventário via comandos padrão
    @commands.command(name="inventory")
    async def inventory_command(self, ctx):
        """Exibe o inventário do jogador."""
        await self.boss_inventory(ctx)  # Reutiliza a função de inventário

    # Sistema de uso de consumíveis via comandos padrão
    @commands.command(name="use")
    async def use_item_command(self, ctx, *, item_name: str = None):
        """Permite que o jogador use um item do inventário."""
        await self.boss_use_item(ctx, item_name=item_name)  # Reutiliza a função de usar item

    # Sistema de estatísticas via comandos padrão
    @commands.command(name="stats")
    async def stats_command(self, ctx):
        """Exibe as estatísticas do jogador."""
        await self.boss_stats(ctx)  # Reutiliza a função de stats

    # Sistema de ajuda via comandos padrão
    @commands.command(name="help")
    async def help_command(self, ctx):
        """Exibe a ajuda dos comandos do bot."""
        await self.boss_help(ctx)  # Reutiliza a função de ajuda

    async def setup(self, ctx):
        """Configurações iniciais do cog."""
        await self.ensure_player(ctx.author.id)

    async def on_ready(self):
        """Evento que é chamado quando o bot está pronto."""
        print(f"Cog '{self.__class__.__name__}' está pronto!")

# Configuração do cog
async def setup(bot):
    await bot.add_cog(BossCog(bot))
