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

        # Iniciar as tarefas
        self.boss_attack_task.start()
        self.rank_update.start()
        self.daily_mission_task.start()
        
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
        self.status_channel_id = 1186636197934661632  # Substitua pelo ID correto
        self.commands_channel_id = 1299092242673303552  # Substitua pelo ID correto
        self.exempt_role_id = 1296631135442309160  # Substitua pelo ID correto
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
        
        # Configuração de Missões Diárias
        self.daily_mission = {}

        # Configuração dos IDs dos Cargos de Sniper
        self.sniper_adamanty_role_id = <ROLE_ID_Sniper_Adamanty>    # Substitua pelo ID real
        self.sniper_emberium_role_id = <ROLE_ID_Sniper_Emberium>    # Substitua pelo ID real
        self.sniper_boss_role_id = <ROLE_ID_Sniper_Boss>            # Substitua pelo ID real

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

    @commands.group(invoke_without_command=True, name="boss")
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hora de cooldown por usuário
    async def boss(self, ctx):
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

                # Recompensa em Ember (opcional)
                ember_reward = random.randint(50, 100)
                await self.award_ember(user_id, ember_reward)

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

    # Subcomandos do Grupo Boss

    @boss.command(name="status")
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

    @boss.command(name="stats")
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
        embed.add_field(name="Ember", value=result['ember'], inline=True)
        embed.add_field(name="Ferimentos", value=result['wounds'], inline=True)
        embed.add_field(name="Infectado", value="Sim" if result['infected'] else "Não", inline=True)
        embed.add_field(name="Debuff de Dano", value="Sim" if result['damage_debuff'] else "Não", inline=True)
        await ctx.send(embed=embed)

    @boss.command(name="inventory")
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

    @boss.command(name="use")
    async def boss_use_item(self, ctx, *, item_name: str = None):
        """Permite que o jogador use um item do inventário."""
        if not item_name:
            await ctx.send("⚠️ Por favor, especifique o item que deseja usar. Exemplo: `!boss use Remédio Antiviral`")
            return

        user_id = ctx.author.id
        await self.ensure_player(user_id)

        success, message = await self.use_consumable(user_id, item_name)
        await ctx.send(message)

    @boss.command(name="rank")
    async def boss_rank(self, ctx):
        """Exibe o ranking dos melhores jogadores."""
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
        await ctx.send(embed=embed)

    @boss.command(name="help")
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
        embed.add_field(name="!boss use <item>", value="Usa um item do seu inventário. Exemplo: `!boss use Remédio Antiviral`", inline=False)
        embed.add_field(name="!boss rank", value="Exibe o ranking dos melhores jogadores.", inline=False)
        embed.add_field(name="!boss help", value="Exibe esta mensagem de ajuda.", inline=False)
        embed.add_field(name="!boss shop_ember", value="Exibe os itens disponíveis para compra com Ember.", inline=False)
        embed.add_field(name="!boss buy_ember <item_key>", value="Compra um item usando Ember. Exemplo: `!boss buy_ember armadura_de_zumbi`", inline=False)
        embed.add_field(name="!boss balance", value="Exibe seu saldo atual de dinheiro.", inline=False)
        embed.add_field(name="!boss balance_ember", value="Exibe seu saldo atual de Ember.", inline=False)
        embed.add_field(name="!boss daily_mission", value="Participa da missão diária para ganhar Ember.", inline=False)
        embed.add_field(name="!boss event", value="Inicia um evento especial apocalíptico.", inline=False)
        await ctx.send(embed=embed)

    # Comandos da Loja Ember

    @boss.command(name="shop_ember")
    async def boss_shop_ember(self, ctx):
        """Exibe os itens disponíveis para compra com Ember."""
        embed = discord.Embed(
            title="🛒 Loja de Ember",
            description="Aqui você pode comprar itens exclusivos usando Ember.",
            color=discord.Color.blue()
        )
        
        for item_key, item in self.shop_ember_items.items():
            embed.add_field(
                name=item['name'],
                value=f"Custo: {item['price']} Ember\n{item['description']}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @boss.command(name="buy_ember")
    async def boss_buy_ember(self, ctx, *, item_key: str = None):
        """Permite que o jogador compre um item da loja usando Ember."""
        if not item_key:
            await ctx.send("⚠️ Por favor, especifique o item que deseja comprar. Exemplo: `!boss buy_ember armadura_de_zumbi`")
            return
        
        item_key = item_key.lower()
        
        if item_key not in self.shop_ember_items:
            await ctx.send("⚠️ Item não encontrado na loja de Ember. Use `!boss shop_ember` para ver os itens disponíveis.")
            return
        
        item = self.shop_ember_items[item_key]
        user_id = ctx.author.id
        
        # Garantir que o jogador exista no banco de dados
        await self.ensure_player(user_id)
        
        async with self.bot.pool.acquire() as connection:
            # Obter o saldo atual de Ember do jogador
            result = await connection.fetchrow("SELECT ember FROM players WHERE user_id = $1", user_id)
            current_ember = result['ember'] if result else 0
            
            if current_ember < item['price']:
                await ctx.send("⚠️ Você não tem Ember suficiente para comprar este item.")
                return
            
            # Deduzir o preço do item do saldo de Ember do jogador
            await connection.execute(
                "UPDATE players SET ember = ember - $1 WHERE user_id = $2",
                item['price'], user_id
            )
            
            # Adicionar o item ao inventário do jogador
            await self.add_item_to_inventory(user_id, item['name'])
            
        embed = discord.Embed(
            title="🛍️ Compra Realizada!",
            description=f"Você comprou **{item['name']}** por {item['price']} Ember.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # Comandos de Saldo

    @boss.command(name="balance")
    async def boss_balance(self, ctx):
        """Exibe o saldo atual de dinheiro do jogador."""
        user_id = ctx.author.id
        await self.ensure_player(user_id)
        
        async with self.bot.pool.acquire() as connection:
            result = await connection.fetchrow("SELECT money FROM players WHERE user_id = $1", user_id)
            current_money = result['money'] if result else 0
        
        embed = discord.Embed(
            title=f"💰 Saldo de {ctx.author.display_name}",
            description=f"Você possui **{current_money}** 💰.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

    @boss.command(name="balance_ember")
    async def boss_balance_ember(self, ctx):
        """Exibe o saldo atual de Ember do jogador."""
        user_id = ctx.author.id
        await self.ensure_player(user_id)
        
        async with self.bot.pool.acquire() as connection:
            result = await connection.fetchrow("SELECT ember FROM players WHERE user_id = $1", user_id)
            current_ember = result['ember'] if result else 0
        
        embed = discord.Embed(
            title=f"🔥 Saldo de Ember de {ctx.author.display_name}",
            description=f"Você possui **{current_ember}** Ember.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

    # Missão Diária

    @boss.command(name="daily_mission")
    async def boss_daily_mission(self, ctx):
        """Permite que o jogador participe da missão diária para ganhar Ember."""
        user_id = ctx.author.id
        await self.ensure_player(user_id)
        
        today = time.strftime("%Y-%m-%d")
        
        if self.daily_mission.get(user_id) == today:
            await ctx.send("⚠️ Você já completou a missão diária hoje. Tente novamente amanhã!")
            return
        
        # Definir a missão (exemplo: matar 10 minions)
        mission_goal = 10
        mission_reward = 500  # Ember
        
        # Simulação da missão (em um cenário real, você implementaria lógica de acompanhamento)
        # Aqui, automaticamente completamos a missão
        await self.award_ember(user_id, mission_reward)
        self.daily_mission[user_id] = today
        
        embed = discord.Embed(
            title="🎯 Missão Diária Completa!",
            description=f"Você completou a missão diária e ganhou **{mission_reward}** Ember!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # Evento Especial

    @boss.command(name="event")
    async def boss_event(self, ctx):
        """Inicia um evento especial apocalíptico."""
        if self.current_event:
            await ctx.send("⚠️ Já há um evento ativo no momento.")
            return
        
        # Definir um evento aleatório
        events = [
            {
                "name": "Tempestade Zumbi 🌪️",
                "description": "Uma tempestade zumbi está se aproximando! Aumente sua defesa temporariamente.",
                "effect": self.activate_tempestade_zumbi
            },
            {
                "name": "Horda Infinita 🧟‍♂️",
                "description": "Uma horda infinita de zumbis está atacando! Ganhe mais XP por ataques ao boss.",
                "effect": self.activate_horda_infinita
            },
            {
                "name": "Pânico Geral 😱",
                "description": "O pânico se espalha! Todos os jogadores têm uma chance maior de infecção.",
                "effect": self.activate_panico_geral
            }
        ]
        event = random.choice(events)
        self.current_event = event
        embed = discord.Embed(
            title=f"✨ Evento Especial: {event['name']}",
            description=event['description'],
            color=discord.Color.dark_purple()
        )
        await ctx.send(embed=embed)
        
        # Ativar o efeito do evento
        await event['effect']()

    async def activate_tempestade_zumbi(self):
        """Aumenta a defesa de todos os jogadores por um período."""
        channel = self.bot.get_channel(self.status_channel_id)
        if channel is None:
            print(f"Canal com ID {self.status_channel_id} não encontrado.")
            return

        embed = discord.Embed(
            title="🌪️ Tempestade Zumbi Ativada!",
            description="Aumente sua defesa em 20% por 30 minutos.",
            color=discord.Color.blue()
        )
        await channel.send(embed=embed)
        
        # Implementar lógica para aumentar a defesa dos jogadores (exemplo: adicionar debuff)
        # Aqui você pode adicionar flags ou alterar atributos no banco de dados

        # Esperar 30 minutos
        await asyncio.sleep(1800)

        # Reverter o efeito
        embed = discord.Embed(
            title="🌪️ Tempestade Zumbi Terminada!",
            description="Sua defesa voltou ao normal.",
            color=discord.Color.blue()
        )
        await channel.send(embed=embed)
        self.current_event = None

    async def activate_horda_infinita(self):
        """Aumenta o ganho de XP para os jogadores durante um período."""
        channel = self.bot.get_channel(self.status_channel_id)
        if channel is None:
            print(f"Canal com ID {self.status_channel_id} não encontrado.")
            return

        embed = discord.Embed(
            title="🧟‍♂️ Horda Infinita Ativada!",
            description="Ganhe 50% mais XP por ataques ao boss por 1 hora.",
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)
        
        # Implementar lógica para aumentar o ganho de XP dos jogadores
        self.horda_infinita_active = True

        # Esperar 1 hora
        await asyncio.sleep(3600)

        # Reverter o efeito
        embed = discord.Embed(
            title="🧟‍♂️ Horda Infinita Terminada!",
            description="O ganho de XP voltou ao normal.",
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)
        self.horda_infinita_active = False
        self.current_event = None

    async def activate_panico_geral(self):
        """Aumenta a chance de infecção para todos os jogadores."""
        channel = self.bot.get_channel(self.status_channel_id)
        if channel is None:
            print(f"Canal com ID {self.status_channel_id} não encontrado.")
            return

        embed = discord.Embed(
            title="😱 Pânico Geral Ativado!",
            description="A chance de infecção aumentou em 10% para todos os jogadores por 45 minutos.",
            color=discord.Color.dark_red()
        )
        await channel.send(embed=embed)
        
        # Implementar lógica para aumentar a chance de infecção
        self.panico_geral_active = True

        # Esperar 45 minutos
        await asyncio.sleep(2700)

        # Reverter o efeito
        embed = discord.Embed(
            title="😱 Pânico Geral Terminada!",
            description="A chance de infecção voltou ao normal.",
            color=discord.Color.dark_red()
        )
        await channel.send(embed=embed)
        self.panico_geral_active = False
        self.current_event = None

    # Funções Auxiliares

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
        
        # Sistema de Drop de Snipers
        await self.sniper_drop(ctx, user_id)

        embed = discord.Embed(
            title="🏆 Boss Derrotado!",
            description=f"O boss **{self.current_boss['name']}** foi vencido!\nRecompensas: **{reward_item}** 🎁, **{reward_money}** 💰 e **{reward_ember}** Ember 🔥",
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

    async def add_item_to_inventory(self, user_id, item):
        """Adiciona um item ao inventário do jogador."""
        async with self.bot.pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO inventory(user_id, item) VALUES($1, $2)",
                user_id, item
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

    # Sistema de Ataque do Boss

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

    # Sistema de Mudança de Status do Bot

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

    # Sistema de Ranking a cada 2 horas

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
    async def before_rank_update(self):
        await self.bot.wait_until_ready()

    # Listener para Quando o Cog Está Pronto

    @commands.Cog.listener()
    async def on_ready(self):
        """Evento que é chamado quando o cog está pronto."""
        print(f"Cog '{self.__class__.__name__}' está pronto!")

    # Setup do Cog

    async def setup(self, bot):
        """Configurações iniciais do cog."""
        await bot.add_cog(BossCog(bot))

    # Sistema de Drop de Snipers

    async def sniper_drop(self, ctx, user_id):
        """Sistema de drop para Snipers ao derrotar o boss."""
        drop_chance = random.randint(1, 100)
        if drop_chance <= 35:  # 35% de chance total de drop
            # Definir as chances individuais
            sniper_chance = random.randint(1, 100)
            if sniper_chance <= 5:  # 5% para Sniper Boss
                role_id = self.sniper_boss_role_id
                sniper_name = "Sniper Boss 💣"
            elif sniper_chance <= 25:  # 20% para Sniper Adamanty
                role_id = self.sniper_adamanty_role_id
                sniper_name = "Sniper Adamanty 🔫"
            else:  # 10% para Sniper Emberium
                role_id = self.sniper_emberium_role_id
                sniper_name = "Sniper Emberium 🔥"
            
            # Obter o membro
            member = ctx.guild.get_member(user_id)
            if member:
                role = ctx.guild.get_role(role_id)
                if role:
                    if role in member.roles:
                        await ctx.send(f"🔔 **{ctx.author.display_name}**, você já possui o cargo **{role.name}**!")
                    else:
                        await member.add_roles(role)
                        embed = discord.Embed(
                            title="🎁 Drop de Sniper!",
                            description=f"Parabéns **{ctx.author.display_name}**! Você recebeu o cargo **{role.name}**.",
                            color=discord.Color.purple()
                        )
                        await ctx.send(embed=embed)
                else:
                    await ctx.send("⚠️ O cargo de Sniper não foi encontrado. Verifique os IDs configurados.")
            else:
                await ctx.send("⚠️ Não foi possível encontrar seu perfil no servidor.")

    # Comando Admin para Roubar o Boss

    @boss.command(name="steal")
    @commands.has_permissions(administrator=True)
    async def boss_steal(self, ctx):
        """Permite que um admin roube o boss ativo e receba uma recompensa."""
        if not self.current_boss:
            await ctx.send("⚔️ Não há nenhum boss ativo para ser roubado.")
            return

        user_id = ctx.author.id

        # Resetar o boss
        stolen_boss = self.current_boss["name"]
        self.current_boss = None

        # Recompensa para o admin que roubou
        reward_money = random.randint(2000, 3000)
        reward_ember = random.randint(1000, 1500)

        await self.add_money_to_player(user_id, reward_money)
        await self.award_ember(user_id, reward_ember)

        # Notificação ao admin
        embed = discord.Embed(
            title="🚨 Boss Roubado!",
            description=f"**{ctx.author.display_name}** roubou o boss **{stolen_boss}**!\nRecompensas: **{reward_money}** 💰 e **{reward_ember}** Ember 🔥",
            color=discord.Color.dark_red()
        )
        await ctx.send(embed=embed)

        # Opcional: Mostrar a arma do boss roubado
        weapon = random.choice(self.weapons)
        weapon_embed = discord.Embed(
            title="🔫 Arma do Boss Roubado",
            description=f"A arma obtida ao roubar o boss é: **{weapon}**",
            color=discord.Color.gold()
        )
        await ctx.send(embed=weapon_embed)

    @boss_steal.error
    async def boss_steal_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("⚠️ Você não possui permissão para usar este comando.")
        else:
            await ctx.send("⚠️ Ocorreu um erro ao tentar roubar o boss.")

    # Sistema de Drop de Snipers Continua...

    # (O restante do código permanece inalterado)

# Configuração do cog
async def setup(bot):
    await bot.add_cog(BossCog(bot))
