import discord
from discord.ext import commands, tasks
from collections import defaultdict
import asyncio

class RankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.damage_rank = defaultdict(int)
        self.kill_rank = defaultdict(int)
        self.sniper_rank = defaultdict(int)

        # IDs dos cargos para cada posição de cada ranking
        self.role_ids = {
            "damage": [1300850877585690655, 1300852310171324566, 1300852691970428958],
            "kill": [1300853285858578543, 1300853676784484484, 1300854136648241235],
            "sniper": [1300854639658270761, 1300854891350327438, 1300855252928434288]
        }

        # ID do canal onde o rank será exibido
        self.channel_id = 1186636197934661632

    @commands.Cog.listener()
    async def on_ready(self):
        # Aguardar para garantir que o bot está totalmente conectado
        await asyncio.sleep(5)
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
        """Envia o ranking no canal especificado."""
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            print("Erro: Canal de classificação não encontrado.")
            return

        # Seleciona o ranking apropriado
        rank = getattr(self, f"{rank_type}_rank")
        sorted_rank = sorted(rank.items(), key=lambda x: x[1], reverse=True)[:5]

        # Cria o embed para o ranking
        embed = discord.Embed(
            title=title,
            description="Aqui estão os heróis que se destacaram! Parabéns aos líderes!",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url="https://i.postimg.cc/Y9TKwnJp/trophy-icon.png")
        embed.set_footer(text="Continue batalhando para melhorar seu rank! 💪")

        for i, (user_id, score) in enumerate(sorted_rank, 1):
            embed.add_field(
                name=f"{emoji} {i}. <@{user_id}>",
                value=f"**{description}:** {score}",
                inline=False
            )

        await channel.send(embed=embed)

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

async def setup(bot):
    await bot.add_cog(RankCog(bot))
