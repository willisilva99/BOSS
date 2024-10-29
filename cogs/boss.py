import discord
from discord.ext import commands
import random

class BossCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_boss = None  # Inicialmente, sem boss ativo
        self.cooldown_time = 3600  # 1 hora de cooldown por usuário
        self.last_attack_time = {}
        self.snipers = ["🔫 SNIPER BOSS RARA", "🔥 SNIPER EMBERIUM", "💎 SNIPER DAMANTY"]
        
        # URLs das imagens dos bosses
        self.boss_images = {
            "Gigante Emberium": {
                "default": "https://cdn.discordapp.com/attachments/1300796026378256484/1300796094607003773/image.png",
                "attack": "https://cdn.discordapp.com/attachments/1300796026378256484/1300796526179782758/image.png",
                "attack_player": "https://cdn.discordapp.com/attachments/1300796026378256484/1300796853016723528/image.png",
                "flee": "https://cdn.discordapp.com/attachments/1300796026378256484/1300801431405727795/image.png",
                "defeated": "https://cdn.discordapp.com/attachments/1300796026378256484/1300801821169942568/image.png"
            },
            "Boss das Sombras": {
                "default": "https://cdn.discordapp.com/attachments/1300802228780666900/image.png",
                "attack": "https://cdn.discordapp.com/attachments/1300802427645198366/image.png",
                "attack_player": "https://cdn.discordapp.com/attachments/1300802611120832574/image.png",
                "flee": "https://cdn.discordapp.com/attachments/1300803016475148298/image.png",
                "defeated": "https://cdn.discordapp.com/attachments/1300803312894869565/image.png"
            },
            "Mega Boss": {
                "default": "https://cdn.discordapp.com/attachments/1300803765858730015/image.png",
                "attack": "https://cdn.discordapp.com/attachments/1300809511325401171/image.png",
                "attack_player": "https://cdn.discordapp.com/attachments/1300809635137327105/image.png",
                "flee": "https://cdn.discordapp.com/attachments/1300809809129508956/image.png",
                "defeated": "https://cdn.discordapp.com/attachments/1300810090147741807/image.png"
            }
        }

        # Lista de Bosses com diferentes características e HP elevado para mais dificuldade
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

    async def ensure_player(self, user_id):
        # Função para garantir que o jogador tenha uma entrada de dados no banco (pode ser customizado)
        pass  # Aqui inseriríamos a lógica de banco de dados

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

    async def attempt_boss_escape(self):
        """Verifica se o boss consegue fugir."""
        escape_chance = random.randint(1, 100)
        return escape_chance <= 15  # 15% de chance de fuga

    @commands.command(name="boss")
    async def boss_attack(self, ctx):
        """Permite atacar o boss e, se derrotado, concede uma premiação."""
        user_id = ctx.author.id
        display_name = f"<@{ctx.author.id}>"  # Menciona o usuário com o símbolo @

        if not self.current_boss:
            # Escolhe um boss aleatório para invocar
            self.current_boss = random.choice(self.bosses).copy()
            embed = discord.Embed(
                title="⚔️ Boss Invocado!",
                description=f"{display_name} invocou o {self.current_boss['name']} com {self.current_boss['hp']} HP!\n"
                            f"{random.choice(self.boss_dialogues['invocation'])}\n"
                            "Todos devem atacá-lo para derrotá-lo!",
                color=discord.Color.red()
            )

            # Seleciona a imagem do boss correspondente
            if self.current_boss['name'] == "👹 Mega Boss":
                embed.set_image(url=self.boss_images["Mega Boss"]["default"])  # Imagem do Mega Boss
            elif self.current_boss['name'] == "👻 Boss das Sombras":
                embed.set_image(url=self.boss_images["Boss das Sombras"]["default"])  # Imagem do Boss das Sombras
            else:
                embed.set_image(url=self.boss_images["Gigante Emberium"]["default"])  # Imagem do Gigante Emberium
            
            await ctx.send(embed=embed)
        else:
            # Caso o boss já tenha sido invocado, aplica o cooldown padrão para o atacante
            if user_id not in self.last_attack_time or (ctx.message.created_at.timestamp() - self.last_attack_time[user_id]) >= self.cooldown_time:
                damage = random.randint(50, 200)
                self.current_boss["hp"] -= damage
                self.last_attack_time[user_id] = ctx.message.created_at.timestamp()
                embed = discord.Embed(
                    title="🎯 Ataque no Boss!",
                    description=f"{display_name} atacou o {self.current_boss['name']} causando {damage} de dano!\n"
                                f"**HP restante do boss**: {self.current_boss['hp']}",
                    color=discord.Color.orange()
                )

                # Adiciona a imagem do ataque
                if self.current_boss['name'] == "👹 Mega Boss":
                    embed.set_image(url=self.boss_images["Mega Boss"]["attack"])  # Imagem de ataque do Mega Boss
                elif self.current_boss['name'] == "👻 Boss das Sombras":
                    embed.set_image(url=self.boss_images["Boss das Sombras"]["attack"])  # Imagem de ataque do Boss das Sombras
                else:
                    embed.set_image(url=self.boss_images["Gigante Emberium"]["attack"])  # Imagem de ataque do Gigante Emberium

                await ctx.send(embed=embed)

                # Chance do boss contra-atacar
                if random.randint(1, 100) <= self.current_boss["attack_chance"]:
                    boss_damage = random.randint(*self.current_boss["damage_range"])
                    embed = discord.Embed(
                        title="⚠️ Contra-Ataque do Boss!",
                        description=f"O {self.current_boss['name']} contra-atacou {display_name}, causando {boss_damage} de dano!",
                        color=discord.Color.red()
                    )
                    # Imagem do ataque do boss ao jogador
                    if self.current_boss['name'] == "👹 Mega Boss":
                        embed.set_image(url=self.boss_images["Mega Boss"]["attack_player"])
                    elif self.current_boss['name'] == "👻 Boss das Sombras":
                        embed.set_image(url=self.boss_images["Boss das Sombras"]["attack_player"])
                    else:
                        embed.set_image(url=self.boss_images["Gigante Emberium"]["attack_player"])
                    await ctx.send(embed=embed)

                if self.current_boss["hp"] <= 0:
                    # Boss derrotado por todos os jogadores
                    reward_message = self.generate_sniper_drop()
                    embed = discord.Embed(
                        title="🏆 Boss Derrotado!",
                        description=f"{random.choice(self.boss_dialogues['defeat'])}\n{reward_message}",
                        color=discord.Color.green()
                    )
                    embed.set_image(url=self.boss_images[self.current_boss['name']]["defeated"])  # Imagem do boss derrotado
                    await ctx.send(embed=embed)
                    self.current_boss = None  # Reinicia o boss para próxima invocação
                else:
                    # Verifica se o boss tenta fugir
                    if await self.attempt_boss_escape():
                        embed = discord.Embed(
                            title="🏃‍♂️ O Boss Fugiu!",
                            description=f"{random.choice(self.boss_dialogues['escape'])}\n"
                                        "Você não ganhou nenhuma recompensa.",
                            color=discord.Color.yellow()
                        )
                        embed.set_image(url=self.boss_images[self.current_boss['name']]["flee"])  # Imagem do boss fugindo
                        await ctx.send(embed=embed)
                        self.current_boss = None  # Reinicia o boss para próxima invocação
            else:
                # Usuário está em cooldown
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
        """Evento chamado quando o bot está pronto."""
        print("BossCog está pronto!")

# Função de setup para adicionar o cog ao bot
async def setup(bot):
    await bot.add_cog(BossCog(bot))
