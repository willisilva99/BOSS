import discord
from discord.ext import commands, tasks
import random
import time
import asyncio

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown_time = 3600  # 1 hora de cooldown por usuário
        self.current_boss = None
        self.current_event = None
        self.horda_infinita_active = False
        self.panico_geral_active = False

        # ID do Administrador Específico
        self.admin_id = 470628393272999948  # 🔥 Substitua pelo ID correto

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
        self.status_channel_id = 1186636197934661632  # 🔥 Substitua pelo ID correto
        self.commands_channel_id = 1299092242673303552  # 🔥 Substitua pelo ID correto
        self.exempt_role_id = 1296631135442309160  # 🔥 Substitua pelo ID correto
        self.minions = ["Minion 1 🧟", "Minion 2 🧟", "Minion 3 🧟"]

        # Configuração da Loja Ember
        self.shop_ember_items = {
            "armadura_de_zumbi": {
                "name": "🛡️ Armadura de Zumbi",
                "price": 800,
                "description": "Reduz o dano recebido em 20% durante combates."
            },
            "explosivo_viral": {
                "name": "💥 Explosivo Viral",
                "price": 1200,
                "description": "Causa 300 de dano ao boss."
            },
            "remedio_antiviral": {
                "name": self.consumables['antiviral'],
                "price": 500,
                "description": "Cura sua infecção instantaneamente."
            },
            "soro_de_forca": {
                "name": self.consumables['soro'],
                "price": 600,
                "description": "Remove o debuff de dano e aumenta sua força."
            }
        }

        # 🔥 **Definição dos Tipos de Snipers e Armas Associadas**
        self.snipers = {
            "adamanty": {
                "name": "Sniper Adamanty",
                "weapon": "🔫 Rifle Adamanty"
            },
            "emberium": {
                "name": "Sniper Emberium",
                "weapon": "🔥 Rifle Emberium"
            },
            "boss": {
                "name": "Sniper Boss",
                "weapon": "💣 Rifle Boss"
            }
        }

        # 🔥 **Variável para controlar o cooldown das mensagens de sniper**
        self.last_sniper_announcement = 0  # Armazena o timestamp da última mensagem

        # Configuração de Missões Diárias
        self.daily_mission = {}

        # Iniciar as tarefas
        self.boss_attack_task.start()
        self.rank_update.start()
        self.change_status.start()

    # 🔥 **Definição das Tarefas Antes do Método __init__**

    @tasks.loop(minutes=5)
    async def boss_attack_task(self):
        """Tarefa que faz o boss atacar periodicamente."""
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

    @boss_attack_task.before_loop
    async def before_boss_attack_task(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=2)
    async def rank_update(self):
        """Atualiza o ranking dos melhores jogadores a cada 2 horas."""
        async with self.bot.pool.acquire() as connection:
            top_players = await connection.fetch(
                "SELECT user_id, xp FROM players ORDER BY xp DESC LIMIT 10"
            )
        if not top_players:
            await self.bot.get_channel(self.status_channel_id).send("🏆 Ainda não há jogadores no ranking.")
            return
        ranking = "\n".join([f"<@{p['user_id']}> - {p['xp']} XP" for p in top_players])
        embed = discord.Embed(
            title="🏆 Ranking de Sobreviventes",
            description=ranking,
            color=discord.Color.gold()
        )
        await self.bot.get_channel(self.status_channel_id).send(embed=embed)

    @rank_update.before_loop
    async def before_rank_update_before_loop(self):
        await self.bot.wait_until_ready()

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
    async def before_change_status_before_loop(self):
        await self.bot.wait_until_ready()

    # Métodos de Utilidade

    async def ensure_player(self, user_id):
        """Garante que o usuário tenha uma entrada na tabela 'players'."""
        async with self.bot.pool.acquire() as connection:
            # Tenta buscar o jogador
            result = await connection.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not result:
                # Se não existir, insere com valores padrão
                await connection.execute("""
                    INSERT INTO players (user_id, wounds, money, ember, xp, level, infected, damage_debuff)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, user_id, 0, 1000, 0, 0, 1, False, False)
                print(f"Jogador {user_id} adicionado à tabela 'players'.")

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
        reward_item = self.generate_loot()
        reward_money = random.randint(1000, 2000)  # Define uma faixa para a recompensa em dinheiro
        reward_ember = random.randint(500, 1000)  # Ember como recompensa adicional

        await self.add_item_to_inventory(user_id, reward_item)
        await self.add_money_to_player(user_id, reward_money)
        await self.award_ember(user_id, reward_ember)

        # 🔥 **Sistema de Drop de Snipers**
        await self.sniper_drop(ctx, user_id)

        embed = discord.Embed(
            title="🏆 Boss Derrotado!",
            description=(
                f"O boss **{self.current_boss['name']}** foi vencido!\n"
                f"Recompensas: **{reward_item}** 🎁, **{reward_money}** 💰 e **{reward_ember}** Ember 🔥"
            ),
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
        if self.panico_geral_active:
            chance += 10  # Aumenta a chance de infecção em 10% durante Pânico Geral
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
        if self.panico_geral_active:
            chance += 10  # Aumenta a chance de debuff em 10% durante Pânico Geral
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
        await self.check_level_up(user_id)

    async def award_wounds(self, user_id, amount):
        """Concede ferimentos ao jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "UPDATE players SET wounds = wounds + $1 WHERE user_id = $2",
                amount, user_id
            )
            # Aqui você pode adicionar lógica para verificar se o jogador está morto ou outras condições

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

    async def award_ember(self, user_id, amount):
        """Concede Ember ao jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "UPDATE players SET ember = ember + $1 WHERE user_id = $2",
                amount, user_id
            )

    async def add_money_to_player(self, user_id, amount):
        """Adiciona dinheiro ao jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "UPDATE players SET money = money + $1 WHERE user_id = $2",
                amount, user_id
            )

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

    # 🔥 **Sistema de Drop de Snipers ao Derrotar o Boss**

    async def sniper_drop(self, ctx, user_id):
        """Sistema de drop para Snipers ao derrotar o boss."""
        drop_chance = random.randint(1, 100)
        if drop_chance <= 10:  # 🔥 Drop mais raro: 10% de chance total
            # Definir as chances individuais
            sniper_roll = random.randint(1, 100)
            if sniper_roll <= 5:  # 5% para Sniper Boss
                sniper_type = "boss"
            elif sniper_roll <= 25:  # 20% para Sniper Adamanty
                sniper_type = "adamanty"
            else:  # 10% para Sniper Emberium
                sniper_type = "emberium"

            sniper = self.snipers[sniper_type]

            # 🔥 **Adicionar a Sniper ao banco de dados**
            async with self.bot.pool.acquire() as connection:
                # Verificar se o usuário já possui uma Sniper
                existing_sniper = await connection.fetchrow("SELECT * FROM snipers WHERE user_id = $1", user_id)
                if existing_sniper:
                    await ctx.send(f"⚠️ Você já possui uma Sniper: **{self.snipers[existing_sniper['sniper_type']]['name']}**.")
                    return
                # Inserir a nova Sniper
                await connection.execute(
                    "INSERT INTO snipers (user_id, sniper_type) VALUES ($1, $2)",
                    user_id, sniper_type
                )

            # 🔥 **Implementar chance do Boss destruir a Sniper**
            destroy_chance = random.randint(1, 100)
            if destroy_chance <= 20:  # 20% de chance de o Boss destruir a Sniper
                async with self.bot.pool.acquire() as connection:
                    await connection.execute("DELETE FROM snipers WHERE user_id = $1", user_id)
                await ctx.send(f"😒 **{ctx.author.display_name}**, o Boss não gostou da sua Sniper e a destruiu!")

                return  # Termina a função, já que a Sniper foi destruída

            # 🔥 **Verificar o cooldown de 40 minutos para anúncios**
            current_time = time.time()
            if current_time - self.last_sniper_announcement >= 2400:  # 40 minutos = 2400 segundos
                # 🔥 **Notificar o usuário sobre o drop com mensagem sarcástica**
                embed = discord.Embed(
                    title="🎁 Drop de Sniper!",
                    description=(
                        f"Parabéns **{ctx.author.display_name}**! Você finalmente conseguiu uma **{sniper['name']}** com a arma **{sniper['weapon']}**.\n"
                        f"Use o comando `!boss notify_admin` para informar o administrador e receber sua recompensa."
                    ),
                    color=discord.Color.purple()
                )
                await ctx.send(embed=embed)

                # Atualizar o timestamp da última mensagem
                self.last_sniper_announcement = current_time
            else:
                # Não enviar a mensagem se o cooldown ainda não expirou
                pass
        else:
            # Sem drop de Sniper
            pass

    # 🔥 **Comandos Relacionados às Snipers**

    @commands.group(invoke_without_command=True, name="boss")
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hora de cooldown por usuário
    async def boss_group(self, ctx):
        """Comando principal para interagir com o boss."""
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
                await self.invocar_boss(ctx, user_id)
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

                # Recompensa em Ember (opcional)
                ember_reward = random.randint(50, 100)
                await self.award_ember(user_id, ember_reward)

                # Mensagem do Ataque com Sarcasmo
                embed = discord.Embed(
                    title="💥 Ataque ao Boss",
                    description=f"{ctx.author.display_name} causou {damage} de dano!\n**HP Restante do Boss:** {self.current_boss['current_hp']}",
                    color=discord.Color.orange()
                )
                # Adicionar tom sarcástico na mensagem
                sarcasm_phrases = [
                    f"Bom trabalho, {ctx.author.display_name}! Você quase derrubou o boss...",
                    f"Wow, {ctx.author.display_name}, isso foi... interessante.",
                    f"Não sei como o boss resistiu, {ctx.author.display_name}. Foi um esforço heróico!"
                ]
                embed.set_footer(text=random.choice(sarcasm_phrases))
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

    @boss_group.command(name="notify_admin")
    async def boss_notify_admin(self, ctx):
        """Permite que o jogador notifique o administrador sobre a obtenção de uma Sniper."""
        user_id = ctx.author.id

        # Verificar se o usuário possui uma Sniper
        async with self.bot.pool.acquire() as connection:
            sniper = await connection.fetchrow("SELECT * FROM snipers WHERE user_id = $1", user_id)

        if not sniper:
            await ctx.send("⚠️ Você não possui nenhuma Sniper para notificar.")
            return

        sniper_info = self.snipers[sniper['sniper_type']]

        # Obter o administrador específico pelo ID
        admin = self.bot.get_user(self.admin_id)
        if not admin:
            await ctx.send("⚠️ Administrador não encontrado. Verifique o ID configurado.")
            return

        # Enviar mensagem privada para o administrador
        try:
            embed = discord.Embed(
                title="📢 Notificação de Sniper Obtida",
                description=(
                    f"**{ctx.author.display_name}** obteve uma **{sniper_info['name']}** com a arma **{sniper_info['weapon']}**.\n"
                    f"Por favor, conceda a recompensa manualmente."
                ),
                color=discord.Color.blue()
            )
            await admin.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("⚠️ Não foi possível enviar uma mensagem privada ao administrador. Verifique as configurações de privacidade dele.")

        await ctx.send("📩 Notificação enviada ao administrador. Aguarde a concessão de sua recompensa.")

    @boss_group.command(name="claim_sniper")
    async def boss_claim_sniper(self, ctx):
        """Permite que o jogador reivindique a recompensa da Sniper obtida."""
        user_id = ctx.author.id

        async with self.bot.pool.acquire() as connection:
            sniper = await connection.fetchrow("SELECT * FROM snipers WHERE user_id = $1", user_id)

        if not sniper:
            await ctx.send("⚠️ Você não possui nenhuma Sniper para reivindicar.")
            return

        sniper_info = self.snipers[sniper['sniper_type']]

        # Simular a recompensa (personalize conforme desejado)
        reward = f"Recompensa especial para **{sniper_info['name']}** com **{sniper_info['weapon']}**!"

        embed = discord.Embed(
            title="🎉 Recompensa Reivindicada!",
            description=(
                f"**{ctx.author.display_name}** reivindicou a recompensa da **{sniper_info['name']}**.\n{reward}"
            ),
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

        # 🔥 **Remover a Sniper do banco de dados após reivindicação**
        async with self.bot.pool.acquire() as connection:
            await connection.execute("DELETE FROM snipers WHERE user_id = $1", user_id)

    @boss_group.command(name="steal_sniper")
    @commands.check(lambda ctx: ctx.author.id == 470628393272999948)  # 🔥 Novo: Restrição ao admin específico
    async def steal_sniper(self, ctx, member: discord.Member = None):
        """Permite que o admin roube a Sniper de um usuário."""
        if member is None:
            await ctx.send("⚠️ Por favor, mencione o usuário de quem deseja roubar a Sniper. Exemplo: `!boss steal_sniper @User`")
            return

        user_id = member.id
        async with self.bot.pool.acquire() as connection:
            sniper = await connection.fetchrow("SELECT * FROM snipers WHERE user_id = $1", user_id)
            if not sniper:
                await ctx.send(f"⚠️ **{member.display_name}** não possui nenhuma Sniper para ser roubada.")
                return
            sniper_type = sniper['sniper_type']
            sniper_info = self.snipers[sniper_type]
            # Remover a Sniper do banco de dados
            await connection.execute("DELETE FROM snipers WHERE user_id = $1", user_id)

        # Notificar o admin sobre o roubo
        embed = discord.Embed(
            title="🚨 Sniper Roubada!",
            description=(
                f"**{ctx.author.display_name}** roubou a **{sniper_info['name']}** de **{member.display_name}**.\n"
                f"Arma: **{sniper_info['weapon']}**"
            ),
            color=discord.Color.dark_red()
        )
        await ctx.send(embed=embed)

        # Notificar o usuário que sua Sniper foi roubada
        try:
            user_embed = discord.Embed(
                title="⚠️ Sniper Roubada!",
                description=(
                    f"Sua **{sniper_info['name']}** foi roubada por **{ctx.author.display_name}**.\n"
                    f"Arma: **{sniper_info['weapon']}**"
                ),
                color=discord.Color.dark_red()
            )
            await member.send(embed=user_embed)
        except discord.Forbidden:
            await ctx.send(f"⚠️ Não foi possível enviar uma mensagem privada para **{member.display_name}**.")

    @steal_sniper.error
    async def steal_sniper_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("⚠️ Você não possui permissão para usar este comando.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("⚠️ Usuário inválido. Por favor, mencione o usuário corretamente.")
        else:
            await ctx.send("⚠️ Ocorreu um erro ao tentar roubar a Sniper.")

    @boss_group.command(name="destroy_sniper")
    @commands.check(lambda ctx: ctx.author.id == 470628393272999948)  # 🔥 Novo: Restrição ao admin específico
    async def destroy_sniper(self, ctx, member: discord.Member = None):
        """Permite que o admin destrua a Sniper de um usuário."""
        if member is None:
            await ctx.send("⚠️ Por favor, mencione o usuário de quem deseja destruir a Sniper. Exemplo: `!boss destroy_sniper @User`")
            return

        user_id = member.id
        async with self.bot.pool.acquire() as connection:
            sniper = await connection.fetchrow("SELECT * FROM snipers WHERE user_id = $1", user_id)
            if not sniper:
                await ctx.send(f"⚠️ **{member.display_name}** não possui nenhuma Sniper para ser destruída.")
                return
            sniper_type = sniper['sniper_type']
            sniper_info = self.snipers[sniper_type]
            # Remover a Sniper do banco de dados
            await connection.execute("DELETE FROM snipers WHERE user_id = $1", user_id)

        # Notificar o admin sobre a destruição
        embed = discord.Embed(
            title="🔥 Sniper Destruída!",
            description=(
                f"**{ctx.author.display_name}** destruiu a **{sniper_info['name']}** de **{member.display_name}**.\n"
                f"Arma: **{sniper_info['weapon']}**"
            ),
            color=discord.Color.dark_red()
        )
        await ctx.send(embed=embed)

        # Notificar o usuário que sua Sniper foi destruída
        try:
            user_embed = discord.Embed(
                title="🔥 Sniper Destruída!",
                description=(
                    f"Sua **{sniper_info['name']}** foi destruída por **{ctx.author.display_name}**.\n"
                    f"Arma: **{sniper_info['weapon']}**"
                ),
                color=discord.Color.dark_red()
            )
            await member.send(embed=user_embed)
        except discord.Forbidden:
            await ctx.send(f"⚠️ Não foi possível enviar uma mensagem privada para **{member.display_name}**.")

    @destroy_sniper.error
    async def destroy_sniper_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("⚠️ Você não possui permissão para usar este comando.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("⚠️ Usuário inválido. Por favor, mencione o usuário corretamente.")
        else:
            await ctx.send("⚠️ Ocorreu um erro ao tentar destruir a Sniper.")

    # Listener para Quando o Cog Está Pronto

    @commands.Cog.listener()
    async def on_ready(self):
        """Evento que é chamado quando o cog está pronto."""
        print(f"Cog '{self.__class__.__name__}' está pronto!")

# Setup do Cog

async def setup(bot):
    await bot.add_cog(BossCog(bot))
