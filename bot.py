import discord
from discord.ext import commands
import random
from collections import defaultdict
import asyncio
import os

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_boss = None  # Inicialmente, sem boss ativo
        self.cooldown_time = 3600  # 1 hora de cooldown por usuário
        self.last_attack_time = {}
        self.damage_dealt = defaultdict(int)  # Armazena o dano causado por cada jogador
        self.kills = defaultdict(int)  # Armazena o número de kills por jogador
        self.snipers_won = defaultdict(int)  # Armazena o número de snipers ganhas por jogador

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

        # IDs dos cargos por desempenho
        self.damage_roles = [1300850877585690655, 1300852310171324566, 1300852691970428958]  # Cargos de dano
        self.kill_roles = [1300853285858578543, 1300853676784484484, 1300854136648241235]  # Cargos de kills
        self.sniper_roles = [1300854639658270761, 1300854891350327438, 1300855252928434288]  # Cargos de snipers

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
        user_id = ctx.author.id
        display_name = f"<@{ctx.author.id}>"  # Menciona o usuário

        if not self.current_boss:
            # Invocar o boss
            self.current_boss = random.choice(self.bosses).copy()
            embed = discord.Embed(
                title="⚔️ Boss Invocado!",
                description=f"{display_name} invocou o {self.current_boss['name']} com {self.current_boss['hp']} HP!\n"
                            f"{random.choice(self.boss_dialogues['invocation'])}\n"
                            "Todos devem atacá-lo para derrotá-lo!",
                color=discord.Color.red()
            )
            embed.set_image(url=self.boss_images[self.current_boss['name']]["default"])
            await ctx.send(embed=embed)
        else:
            # Lógica para atacar o boss
            if user_id not in self.last_attack_time or (ctx.message.created_at.timestamp() - self.last_attack_time[user_id]) >= self.cooldown_time:
                damage = random.randint(50, 200)
                self.current_boss["hp"] -= damage
                self.last_attack_time[user_id] = ctx.message.created_at.timestamp()

                # Registra dano
                self.damage_dealt[user_id] += damage

                embed = discord.Embed(
                    title="🎯 Ataque no Boss!",
                    description=f"{display_name} atacou o {self.current_boss['name']} causando {damage} de dano!\n"
                                f"HP restante do boss: {self.current_boss['hp']}",
                    color=discord.Color.orange()
                )
                embed.set_image(url=self.boss_images[self.current_boss['name']]["attack"])
                await ctx.send(embed=embed)

                # Verifica se o boss foi derrotado
                if self.current_boss["hp"] <= 0:
                    self.kills[user_id] += 1  # Incrementa o contador de kills
                    reward_message = self.generate_sniper_drop()
                    embed = discord.Embed(
                        title="🏆 Boss Derrotado!",
                        description=f"{random.choice(self.boss_dialogues['defeat'])}\n{reward_message}",
                        color=discord.Color.green()
                    )
                    embed.set_image(url=self.boss_images[self.current_boss['name']]["defeated"])
                    await ctx.send(embed=embed)

                    # Atualiza os cargos de acordo com o desempenho
                    await self.update_roles(user_id)
                    self.current_boss = None  # Reseta o boss
                elif await self.attempt_boss_escape():
                    embed = discord.Embed(
                        title="🏃‍♂️ O Boss Fugiu!",
                        description=f"{random.choice(self.boss_dialogues['escape'])}\n"
                                    "Você não ganhou nenhuma recompensa.",
                        color=discord.Color.yellow()
                    )
                    embed.set_image(url=self.boss_images[self.current_boss['name']]["flee"])
                    await ctx.send(embed=embed)
                    self.current_boss = None  # Reseta o boss
            else:
                time_remaining = int(self.cooldown_time - (ctx.message.created_at.timestamp() - self.last_attack_time[user_id]))
                minutes, seconds = divmod(time_remaining, 60)
                embed = discord.Embed(
                    title="⏳ Cooldown Ativo",
                    description=f"{display_name}, você precisa esperar mais **{minutes} minutos e {seconds} segundos** para atacar o boss novamente!",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)

    async def update_roles(self, user_id):
        """Atualiza os cargos com base no dano causado e nas kills."""
        guild = self.bot.guilds[0]  # Assume o primeiro servidor do bot

        # Atualiza cargos por dano
        sorted_damage = sorted(self.damage_dealt.items(), key=lambda x: x[1], reverse=True)[:3]
        for index, (uid, damage) in enumerate(sorted_damage):
            if uid == user_id:
                role = guild.get_role(self.damage_roles[index])  # Cargos de dano
                await guild.get_member(uid).add_roles(role)
                await guild.get_member(uid).send(f"🎖️ Você ganhou o cargo de {role.name} por causar mais dano!")

        # Atualiza cargos por kills
        sorted_kills = sorted(self.kills.items(), key=lambda x: x[1], reverse=True)[:3]
        for index, (uid, kills) in enumerate(sorted_kills):
            if uid == user_id:
                role = guild.get_role(self.kill_roles[index])  # Cargos de kills
                await guild.get_member(uid).add_roles(role)
                await guild.get_member(uid).send(f"🎖️ Você ganhou o cargo de {role.name} por derrotar mais bosses!")

        # Atualiza cargos por snipers
        sorted_snipers = sorted(self.snipers_won.items(), key=lambda x: x[1], reverse=True)[:3]
        for index, (uid, snipers) in enumerate(sorted_snipers):
            if uid == user_id:
                role = guild.get_role(self.sniper_roles[index])  # Cargos de snipers
                await guild.get_member(uid).add_roles(role)
                await guild.get_member(uid).send(f"🎖️ Você ganhou o cargo de {role.name} por ganhar mais snipers!")

# Função de setup para adicionar o cog ao bot
async def setup(bot):
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
