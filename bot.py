import discord
from discord.ext import commands, tasks
import random
from collections import defaultdict
import asyncio
import os

class RankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.damage_rank = defaultdict(int)
        self.kill_rank = defaultdict(int)
        self.sniper_rank = defaultdict(int)

        # URLs das imagens para cada ranking
        self.rank_images = {
            "damage": "https://i.postimg.cc/MTJwRfzg/DALL-E-2024-10-29-15-12-42-Create-an-apocalyptic-themed-background-image-titled-Top-Rank-Dano-N.webp",
            "kill": "https://i.postimg.cc/y85s1rt1/DALL-E-2024-10-29-15-07-02-Create-an-apocalyptic-background-image-titled-Top-Rank-Kill-Nova-Era.webp",
            "sniper": "https://i.postimg.cc/R0H9NLxc/DALL-E-2024-10-29-15-20-36-Create-an-apocalyptic-themed-background-image-titled-Top-Sniper-Nova.webp"
        }

        # IDs dos cargos para cada posição de cada ranking
        self.role_ids = {
            "damage": [1300850877585690655, 1300852310171324566, 1300852691970428958],
            "kill": [1300853285858578543, 1300853676784484484, 1300854136648241235],
            "sniper": [1300854639658270761, 1300854891350327438, 1300855252928434288]
        }

        # Lista de emojis de reação com tema apocalíptico
        self.reaction_emojis = ["🔥", "💀", "⚔️", "☠️", "⚡", "🔫", "🎯", "🪓", "💣"]

        # ID do canal onde o rank será exibido
        self.channel_id = 1186636197934661632

        # Iniciar o reset diário dos rankings
        self.reset_rankings.start()

    @tasks.loop(hours=24)
    async def reset_rankings(self):
        """Reseta os rankings a cada 24 horas."""
        self.damage_rank.clear()
        self.kill_rank.clear()
        self.sniper_rank.clear()
        print("Rankings resetados.")

    @commands.Cog.listener()
    async def on_ready(self):
        """Inicia as tarefas de ranking e atualização de cargos."""
        await asyncio.sleep(5)  # Aguardar para garantir que o bot está totalmente conectado
        channel = self.bot.get_channel(self.channel_id)
        if channel:
            print(f"Canal de rank encontrado: {channel.name} (ID: {channel.id})")
            self.show_damage_rank.start()  # Inicia a tarefa para exibir o ranking de dano
            self.show_kill_rank.start()  # Inicia a tarefa para exibir o ranking de kills
            self.show_sniper_rank.start()  # Inicia a tarefa para exibir o ranking de snipers
            self.update_roles.start()  # Inicia a tarefa de atualização de cargos
        else:
            print("Erro: Canal de classificação não encontrado após o delay de inicialização.")
        print("RankCog está pronto!")

    @tasks.loop(hours=3)
    async def show_damage_rank(self):
        """Envia o ranking de dano ao boss no canal específico a cada 3 horas."""
        await self.send_rank("damage", "🏆 **Top 5 Guerreiros - Dano ao Boss**", "💥", "Dano Causado")

    @tasks.loop(hours=3, minutes=10)
    async def show_kill_rank(self):
        """Envia o ranking de matadores de boss no canal específico a cada 3 horas e 10 minutos."""
        await self.send_rank("kill", "⚔️ **Top 5 Matadores de Bosses**", "💀", "Bosses Derrotados")

    @tasks.loop(hours=3, minutes=20)
    async def show_sniper_rank(self):
        """Envia o ranking de colecionadores de snipers no canal específico a cada 3 horas e 20 minutos."""
        await self.send_rank("sniper", "🔫 **Top 5 Colecionadores de Snipers**", "🎯", "Snipers Conquistadas")

    async def send_rank(self, rank_type, title, emoji, description):
        """Envia o ranking no canal especificado e adiciona uma reação apocalíptica."""
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            print("Erro: Canal de classificação não encontrado.")
            return

        # Seleciona o ranking apropriado e a imagem de fundo
        rank = getattr(self, f"{rank_type}_rank")
        sorted_rank = sorted(rank.items(), key=lambda x: x[1], reverse=True)[:5]
        image_url = self.rank_images[rank_type]

        # Cria o embed para o ranking com imagem temática
        embed = discord.Embed(
            title=title,
            description="Sobreviventes lendários que se destacaram em um mundo apocalíptico. Honra e glória aos melhores!",
            color=discord.Color.orange()
        )
        embed.set_image(url=image_url)
        embed.set_footer(text="Continue lutando para subir no ranking e mostrar sua força! 💪")

        for i, (user_id, score) in enumerate(sorted_rank, 1):
            embed.add_field(
                name=f"{emoji} {i}. <@{user_id}>",
                value=f"**{description}:** {score}",
                inline=False
            )

        message = await channel.send(embed=embed)

        # Adiciona uma reação apocalíptica aleatória ao embed enviado
        reaction = random.choice(self.reaction_emojis)
        await message.add_reaction(reaction)

    @tasks.loop(hours=3)
    async def update_roles(self):
        """Atualiza os cargos dos Top 3 de cada ranking a cada 3 horas."""
        guild = self.bot.guilds[0]  # Assume o primeiro servidor do bot
        if not guild:
            print("Erro: Servidor não encontrado.")
            return

        # Atualiza o Top 3 de todos os rankings de acordo com o rank atual
        await self.update_top_roles(guild, self.damage_rank, self.role_ids["damage"])
        await self.update_top_roles(guild, self.kill_rank, self.role_ids["kill"])
        await self.update_top_roles(guild, self.sniper_rank, self.role_ids["sniper"])

    async def update_top_roles(self, guild, ranking, role_ids):
        """Atribui cargos ao Top 3 de um ranking específico e remove cargos antigos."""
        # Ordena o ranking e pega o Top 3
        sorted_rank = sorted(ranking.items(), key=lambda x: x[1], reverse=True)[:3]

        for index, (user_id, _) in enumerate(sorted_rank):
            member = guild.get_member(user_id)
            if member:
                # Atribui o cargo correspondente ao ranking atual
                role = guild.get_role(role_ids[index])
                await member.add_roles(role, reason="Atualização de rank")
        
        # Remove cargos dos usuários que saíram do Top 3
        for role_id in role_ids:
            role = guild.get_role(role_id)
            for member in role.members:
                if member.id not in [user_id for user_id, _ in sorted_rank]:
                    await member.remove_roles(role, reason="Removido do Top 3")

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_boss = None  # Inicialmente, sem boss ativo
        self.cooldown_time = 7200  # Aumentando para 2 horas (7200 segundos)
        self.last_attack_time = {}
        self.snipers = ["🔫 SNIPER BOSS RARA", "🔥 SNIPER EMBERIUM", "💎 SNIPER DAMANTY"]

        # URLs das imagens dos bosses
        self.boss_images = {
            "Gigante Emberium": {
                "default": "https://i.postimg.cc/Gtfm6xSL/DALL-E-2024-10-29-09-18-46-A-powerful-zombie-boss-named-Emberium-for-a-game-featuring-an-exagge.webp",
                "attack": "https://i.postimg.cc/BnH2pxJg/DALL-E-2024-10-29-09-20-36-A-powerful-zombie-boss-named-Emberium-attacking-a-player-in-a-fantasy.webp",
                "attack_player": "https://i.postimg.cc/zfkKZ8bH/DALL-E-2024-10-29-09-21-49-A-powerful-zombie-boss-named-Emberium-inflicting-damage-on-a-player-i.webp",
                "flee": "https://i.postimg.cc/k5CKpB4d/DALL-E-2024-10-29-09-40-12-A-dramatic-scene-depicting-a-powerful-zombie-boss-named-Emberium-in-t.webp",
                "defeated": "https://i.postimg.cc/Kvdnt9hj/DALL-E-2024-10-29-09-41-47-A-dramatic-scene-depicting-a-powerful-zombie-boss-named-Emberium-lyin.webp"
            },
            "Boss das Sombras": {
                "default": "https://i.postimg.cc/zvQTt7Ld/DALL-E-2024-10-29-09-43-23-A-powerful-zombie-boss-known-as-Shadow-Boss-in-a-fantasy-game-setting.webp",
                "attack": "https://i.postimg.cc/3NNgFVw4/DALL-E-2024-10-29-09-44-13-A-dramatic-fantasy-scene-depicting-a-powerful-zombie-boss-named-Shadow.webp",
                "attack_player": "https://i.postimg.cc/m2cYcvqK/DALL-E-2024-10-29-09-44-57-A-dramatic-fantasy-scene-depicting-the-powerful-zombie-boss-named-Shad.webp",
                "flee": "https://i.postimg.cc/NGC8jsN1/DALL-E-2024-10-29-09-46-35-A-dramatic-fantasy-scene-depicting-the-powerful-zombie-boss-named-Shad.webp",
                "defeated": "https://i.postimg.cc/x8mLZHKn/DALL-E-2024-10-29-09-47-45-A-dramatic-fantasy-scene-depicting-the-powerful-zombie-boss-named-Shad.webp"
            },
            "Mega Boss": {
                "default": "https://i.postimg.cc/W3CMSSq5/DALL-E-2024-10-29-09-49-34-A-powerful-fantasy-character-design-of-a-zombie-boss-named-Mega-Boss.webp",
                "attack": "https://i.postimg.cc/FR7yjwzf/DALL-E-2024-10-29-10-06-58-A-dramatic-fantasy-scene-depicting-a-brave-survivor-attacking-the-power.webp",
                "attack_player": "https://i.postimg.cc/QMNkMFrJ/DALL-E-2024-10-29-10-11-26-A-dramatic-fantasy-scene-depicting-the-powerful-zombie-boss-named-Mega.webp",
                "flee": "https://i.postimg.cc/2S77m4g5/DALL-E-2024-10-29-10-13-34-A-dramatic-fantasy-scene-depicting-the-powerful-zombie-boss-named-Mega.webp",
                "defeated": "https://i.postimg.cc/KvL5pXNB/DALL-E-2024-10-29-10-14-38-A-dramatic-fantasy-scene-depicting-the-powerful-zombie-boss-named-Mega.webp"
            }
        }

        # Mapear nomes dos bosses para correspondência no dicionário de imagens
        self.boss_image_keys = {
            "👹 Mega Boss": "Mega Boss",
            "👻 Boss das Sombras": "Boss das Sombras",
            "💀 Gigante Emberium": "Gigante Emberium"
        }

        # Lista de bosses com diferentes características e HP elevado para mais dificuldade
        self.bosses = [
            {"name": "👹 Mega Boss", "hp": 5000, "attack_chance": 30, "damage_range": (50, 150)},
            {"name": "👻 Boss das Sombras", "hp": 7000, "attack_chance": 40, "damage_range": (60, 200)},
            {"name": "💀 Gigante Emberium", "hp": 10000, "attack_chance": 50, "damage_range": (80, 250)},
        ]

        self.boss_dialogues = {
            "invocation": [
                "🌍 O mundo está em ruínas, e você ousa me desafiar?!",
                "🔥 Seu destino é a destruição, mortais!",
                "👿 A era dos fracos terminou. Prepare-se para o apocalipse!",
            ],
            "attack": [
                "💀 Sua força é insignificante diante de mim!",
                "⚔️ Cada golpe seu é uma provocação ao meu poder!",
                "😈 Vocês nunca vencerão. A nova era será minha!",
            ],
            "defeat": [
                "😱 Não pode ser... A era de trevas... foi interrompida!",
                "🔥 Eu... voltarei... para consumi-los!",
                "💔 Este não é o fim... Apenas o início do meu retorno!",
            ],
            "escape": [
                "🏃‍♂️ Vocês acham que me prenderão? Eu sou o apocalipse!",
                "💨 Adeus, mortais! Esta batalha não é o seu fim!",
                "😈 A nova era ainda não chegou... mas eu voltarei!",
            ]
        }

    async def attempt_boss_escape(self):
        """Verifica se o boss consegue fugir."""
        escape_chance = random.randint(1, 100)
        return escape_chance <= 15  # 15% de chance de fuga

    def generate_sniper_drop(self):
        """Define uma premiação rara."""
        drop_chance = random.randint(1, 1000)  # Tornar o drop muito raro
        if drop_chance <= 2:  # Chance de 0,2% de dropar sniper rara
            selected_sniper = random.choice(self.snipers)
            destroy_chance = random.randint(1, 100)
            if destroy_chance <= 30:  # 30% de chance do boss quebrar o prêmio
                return f"😖 O boss quebrou a {selected_sniper}!"
            else:
                return f"🎉 Parabéns! Você ganhou uma {selected_sniper}!"
        return "😢 O boss não deixou nenhuma sniper desta vez."

    @commands.command(name="boss")
    async def boss_attack(self, ctx):
        """Permite atacar o boss e, se derrotado, concede uma premiação."""
        if ctx.channel.id != 1299092242673303552:
            channel_link = f"<#{1299092242673303552}>"
            await ctx.send(f"⚠️ Este comando só pode ser usado no canal {channel_link}.")
            return

        user_id = ctx.author.id
        display_name = f"<@{ctx.author.id}>"

        if not self.current_boss:
            self.current_boss = random.choice(self.bosses).copy()
            embed = discord.Embed(
                title="⚔️ Boss Invocado!",
                description=f"{display_name} invocou o {self.current_boss['name']} com {self.current_boss['hp']} HP!\n"
                            f"{random.choice(self.boss_dialogues['invocation'])}\n"
                            "Todos devem atacá-lo para derrotá-lo!",
                color=discord.Color.red()
            )

            boss_image_key = self.boss_image_keys.get(self.current_boss["name"], None)
            if boss_image_key:
                embed.set_image(url=self.boss_images[boss_image_key]["default"])
            await ctx.send(embed=embed)
        else:
            if user_id not in self.last_attack_time or (ctx.message.created_at.timestamp() - self.last_attack_time[user_id]) >= self.cooldown_time:
                damage = random.randint(50, 200)
                self.current_boss["hp"] -= damage
                self.last_attack_time[user_id] = ctx.message.created_at.timestamp()
                embed = discord.Embed(
                    title="🎯 Ataque no Boss!",
                    description=f"{display_name} atacou o {self.current_boss['name']} causando {damage} de dano!\n"
                                f"HP restante do boss: {self.current_boss['hp']}",
                    color=discord.Color.orange()
                )
                embed.set_image(url=self.boss_images[self.current_boss["name"]]["attack"])
                await ctx.send(embed=embed)

                if self.current_boss["hp"] <= 0:
                    reward_message = self.generate_sniper_drop()
                    embed = discord.Embed(
                        title="🏆 Boss Derrotado!",
                        description=f"{random.choice(self.boss_dialogues['defeat'])}\n{reward_message}",
                        color=discord.Color.green()
                    )
                    embed.set_image(url=self.boss_images[self.current_boss["name"]]["defeated"])
                    await ctx.send(embed=embed)

                    # Atualiza os rankings após derrotar o boss
                    self.bot.get_cog('RankCog').record_damage(user_id, damage)  # Registra o dano no ranking
                    self.bot.get_cog('RankCog').record_kill(user_id)  # Registra a kill no ranking

                    self.current_boss = None
                else:
                    embed = discord.Embed(
                        title="⚠️ O Boss ainda está de pé!",
                        description=f"{self.current_boss['name']} ainda não foi derrotado!",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
            else:
                time_remaining = int(self.cooldown_time - (ctx.message.created_at.timestamp() - self.last_attack_time[user_id]))
                minutes, seconds = divmod(time_remaining, 60)
                embed = discord.Embed(
                    title="⏳ Cooldown Ativo",
                    description=f"{display_name}, você precisa esperar mais **{minutes} minutos e {seconds} segundos** para atacar o boss novamente!",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        print("BossCog está pronto!")

# Função de setup para adicionar os cogs ao bot
async def setup(bot):
    await bot.add_cog(RankCog(bot))
    await bot.add_cog(BossCog(bot))

# Criação do bot
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    print("Bot está pronto!")

asyncio.run(setup(bot))
bot.run(os.getenv("TOKEN"))
