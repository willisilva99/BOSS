import discord
from discord.ext import commands
import random

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_boss = None  # Inicialmente, sem boss ativo
        self.cooldown_time = 7200  # Aumentando para 2 horas (7200 segundos)
        self.last_attack_time = {}
        self.snipers = ["🔫 SNIPER BOSS RARA", "🔥 SNIPER EMBERIUM", "💎 SNIPER DAMANTY"]

        # Dados para simular rankings de dano e mortes (substituindo RankCog)
        self.damage_data = {}  # Armazenamento de dano por jogador
        self.kills_data = {}  # Armazenamento de mortes por jogador

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
                "attack_player": "https://i.postimg.cc/QMNkMFrJ/DALL-E-2024-10-11-26-A-dramatic-fantasy-scene-depicting-the-powerful-zombie-boss-named-Mega.webp",
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

        # URLs das imagens das snipers
        self.sniper_images = {
            "SNIPER BOSS RARA": {
                "default": "https://i.postimg.cc/50hC80DG/DALL-E-2024-10-29-10-21-27-A-rugged-survivor-in-an-apocalyptic-setting-holding-the-Emberium-Snip.webp",
                "broken": "https://i.postimg.cc/mDz9cMpC/DALL-E-2024-10-23-18-A-rugged-survivor-in-an-apocalyptic-setting-holding-a-completely-shatt.webp"
            },
            "SNIPER EMBERIUM": {
                "default": "https://i.postimg.cc/nh2BNnQj/DALL-E-2024-10-29-10-24-23-A-rugged-survivor-in-an-apocalyptic-setting-confidently-wielding-the.webp",
                "broken": "https://i.postimg.cc/1zzwQbpW/DALL-E-2024-10-29-10-31-58-A-rugged-survivor-in-an-apocalyptic-setting-holding-a-Sniper-Boss-Rar.webp"
            },
            "SNIPER DAMANTY": {
                "default": "https://i.postimg.cc/qv42mNgH/DALL-E-2024-10-29-10-32-54-A-rugged-survivor-in-an-apocalyptic-setting-confidently-holding-the-S.webp",
                "broken": "https://i.postimg.cc/MGrRKt5z/DALL-E-2024-10-29-10-33-40-A-rugged-survivor-in-an-apocalyptic-setting-holding-a-Sniper-Damanty.webp"
            }
        }

        # Lista de bosses com diferentes características e HP elevado para mais dificuldade
        self.bosses = [
            {"name": "👹 Mega Boss", "hp": 5000, "attack_chance": 30, "damage_range": (50, 150)},
            {"name": "👻 Boss das Sombras", "hp": 7000, "attack_chance": 40, "damage_range": (60, 200)},
            {"name": "💀 Gigante Emberium", "hp": 10000, "attack_chance": 50, "damage_range": (80, 250)},
        ]

        # Diálogos dos bosses
        self.boss_dialogues = {
            "invocation": ["🌍 O mundo está em ruínas, e você ousa me desafiar?!"],
            "attack": ["💀 Sua força é insignificante diante de mim!"],
            "defeat": ["😱 Não pode ser... A era de trevas... foi interrompida!"],
            "escape": ["🏃‍♂️ Vocês acham que me prenderão? Eu sou o apocalipse!"]
        }

    async def attempt_boss_escape(self):
        """Simula a chance de fuga do boss."""
        escape_chance = 20  # Exemplo: 20% de chance de o boss fugir
        return random.randint(1, 100) <= escape_chance

    # Método para conceder cargo ao jogador e remover se necessário
    async def grant_role(self, ctx, user, role_name):
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role:
            for member in role.members:
                if member != user:
                    await member.remove_roles(role)
            await user.add_roles(role)
            await ctx.send(f"🎉 {user.mention} agora possui o cargo **{role_name}** por estar entre os melhores! 🏆")

    def record_damage(self, player_id, damage):
        if player_id not in self.damage_data:
            self.damage_data[player_id] = 0
        self.damage_data[player_id] += damage

    def get_top_players_by_damage(self, limit=3):
        sorted_damage = sorted(self.damage_data.items(), key=lambda x: x[1], reverse=True)
        return [player_id for player_id, _ in sorted_damage[:limit]]

    def get_top_players_by_kills(self, limit=3):
        sorted_kills = sorted(self.kills_data.items(), key=lambda x: x[1], reverse=True)
        return [player_id for player_id, _ in sorted_kills[:limit]]

    async def update_roles(self, ctx):
        top_damage_players = self.get_top_players_by_damage(limit=3)
        top_kills_players = self.get_top_players_by_kills(limit=3)

        for player_id in top_damage_players:
            user = await self.bot.fetch_user(player_id)
            await self.grant_role(ctx, user, "Top Damager")

        for player_id in top_kills_players:
            user = await self.bot.fetch_user(player_id)
            await self.grant_role(ctx, user, "Top Killer")

    @commands.command(name="boss")
    async def boss_attack(self, ctx):
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

                self.record_damage(user_id, damage)

                self.last_attack_time[user_id] = ctx.message.created_at.timestamp()
                embed = discord.Embed(
                    title="🎯 Ataque no Boss!",
                    description=f"{display_name} atacou o {self.current_boss['name']} causando {damage} de dano!\n"
                                f"**HP restante do boss**: {self.current_boss['hp']}",
                    color=discord.Color.orange()
                )

                boss_image_key = self.boss_image_keys.get(self.current_boss["name"], None)
                if boss_image_key:
                    embed.set_image(url=self.boss_images[boss_image_key]["attack"])
                await ctx.send(embed=embed)

                await self.update_roles(ctx)

                if random.randint(1, 100) <= self.current_boss["attack_chance"]:
                    boss_damage = random.randint(*self.current_boss["damage_range"])
                    embed = discord.Embed(
                        title="⚠️ Contra-Ataque do Boss!",
                        description=f"O {self.current_boss['name']} contra-atacou {display_name}, causando {boss_damage} de dano!",
                        color=discord.Color.red()
                    )
                    if boss_image_key:
                        embed.set_image(url=self.boss_images[boss_image_key]["attack_player"])
                    await ctx.send(embed=embed)

                if self.current_boss["hp"] <= 0:
                    reward_message = self.generate_sniper_drop()
                    embed = discord.Embed(
                        title="🏆 Boss Derrotado!",
                        description=f"{random.choice(self.boss_dialogues['defeat'])}\n{reward_message}",
                        color=discord.Color.green()
                    )
                    if boss_image_key:
                        embed.set_image(url=self.boss_images[boss_image_key]["defeated"])
                    await ctx.send(embed=embed)
                    self.current_boss = None
                elif await self.attempt_boss_escape():
                    embed = discord.Embed(
                        title="🏃‍♂️ O Boss Fugiu!",
                        description=f"{random.choice(self.boss_dialogues['escape'])}\n"
                                    "Você não ganhou nenhuma recompensa.",
                        color=discord.Color.yellow()
                    )
                    if boss_image_key:
                        embed.set_image(url=self.boss_images[boss_image_key]["flee"])
                    await ctx.send(embed=embed)
                    self.current_boss = None
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

async def setup(bot):
    await bot.add_cog(BossCog(bot))
