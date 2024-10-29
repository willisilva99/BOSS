import discord
from discord.ext import commands, tasks
from collections import defaultdict

class RankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.damage_rank = defaultdict(int)
        self.kill_rank = defaultdict(int)
        self.sniper_rank = defaultdict(int)
        self.rank_display_index = 0

        # IDs dos cargos para cada posição de cada ranking
        self.role_ids = {
            "damage": [1300850877585690655, 1300852310171324566, 1300852691970428958],
            "kill": [1300853285858578543, 1300853676784484484, 1300854136648241235],
            "sniper": [1300854639658270761, 1300854891350327438, 1300855252928434288]
        }

        # ID do canal onde o rank será exibido
        self.channel_id = 1186636197934661632

        # Inicia as tarefas para exibição e atualização do ranking e de cargos
        self.show_rank.start()
        self.update_roles.start()

    def record_damage(self, user_id, damage):
        """Registra o dano causado por um usuário."""
        self.damage_rank[user_id] += damage

    def record_kill(self, user_id):
        """Registra uma kill no boss por um usuário."""
        self.kill_rank[user_id] += 1

    def record_sniper(self, user_id):
        """Registra uma sniper ganha por um usuário."""
        self.sniper_rank[user_id] += 1

    @commands.Cog.listener()
    async def on_ready(self):
        # Verifica se o bot está pronto e encontra o canal de rank
        channel = self.bot.get_channel(self.channel_id)
        if channel:
            print(f"Canal de rank encontrado: {channel.name} (ID: {channel.id})")
        else:
            print("Erro: Canal de classificação não encontrado.")
        print("RankCog está pronto!")

    @tasks.loop(minutes=2)
    async def show_rank(self):
        """Alterna entre os rankings a cada 2 minutos e envia a mensagem de rank no canal correto."""
        # Obtenha o canal de rank
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            print("Erro: Canal de classificação não encontrado.")
            return

        # Configura títulos e emojis para cada ranking
        rank_titles = [
            "🏆 **Top 5 Guerreiros - Dano ao Boss**",
            "⚔️ **Top 5 Matadores de Bosses**",
            "🔫 **Top 5 Colecionadores de Snipers**"
        ]
        rank_emojis = ["💥", "💀", "🎯"]

        embed = discord.Embed(
            title=rank_titles[self.rank_display_index],
            description="Parabéns aos melhores guerreiros! Lutem para alcançar o topo e mostrar sua força!",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url="https://i.postimg.cc/Y9TKwnJp/trophy-icon.png")  # Ícone de troféu
        embed.set_footer(text="Continue batalhando para melhorar seu rank! 💪")

        # Exibir o ranking correto com base no índice atual
        if self.rank_display_index == 0:
            sorted_rank = sorted(self.damage_rank.items(), key=lambda x: x[1], reverse=True)
            for i, (user_id, damage) in enumerate(sorted_rank[:5], 1):
                emoji = rank_emojis[0]
                embed.add_field(
                    name=f"{emoji} {i}. <@{user_id}>",
                    value=f"**Dano Causado:** {damage} 💥",
                    inline=False
                )
        elif self.rank_display_index == 1:
            sorted_rank = sorted(self.kill_rank.items(), key=lambda x: x[1], reverse=True)
            for i, (user_id, kills) in enumerate(sorted_rank[:5], 1):
                emoji = rank_emojis[1]
                embed.add_field(
                    name=f"{emoji} {i}. <@{user_id}>",
                    value=f"**Bosses Derrotados:** {kills} 💀",
                    inline=False
                )
        else:
            sorted_rank = sorted(self.sniper_rank.items(), key=lambda x: x[1], reverse=True)
            for i, (user_id, snipers) in enumerate(sorted_rank[:5], 1):
                emoji = rank_emojis[2]
                embed.add_field(
                    name=f"{emoji} {i}. <@{user_id}>",
                    value=f"**Snipers Conquistadas:** {snipers} 🎯",
                    inline=False
                )

        await channel.send(embed=embed)
        self.rank_display_index = (self.rank_display_index + 1) % 3  # Alterna entre os três ranks

    @tasks.loop(hours=3)
    async def update_roles(self):
        """Atualiza os cargos dos Top 3 de cada ranking a cada 3 horas."""
        guild = self.bot.guilds[0]  # Assume o primeiro servidor do bot
        if not guild:
            print("Erro: Servidor não encontrado.")
            return

        # Atualiza o Top 3 dos rankings de acordo com o rank atual
        if self.rank_display_index == 0:
            await self.update_top_roles(guild, self.damage_rank, self.role_ids["damage"])
        elif self.rank_display_index == 1:
            await self.update_top_roles(guild, self.kill_rank, self.role_ids["kill"])
        elif self.rank_display_index == 2:
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

async def setup(bot):
    await bot.add_cog(RankCog(bot))
