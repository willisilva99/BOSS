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
        await self.bot.get_channel(self.status_channel_id).send(f"⚠️ {self.bot.get_user(user_id).display_name} foi infectado durante o combate!")

# Aplicação de debuff de dano
async def apply_damage_debuff(self, user_id):
    chance = random.randint(1, 100)
    if chance <= 15:  # 15% de chance de debuff
        async with self.bot.pool.acquire() as connection:
            await connection.execute("UPDATE players SET damage_debuff = TRUE WHERE user_id = $1", user_id)

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
        members = [member.display_name for member in channel.members if member.id != self.bot.user.id]
        if members:
            await channel.send(f"{random.choice(taunts)} {random.choice(members)}, você será o próximo! 😈")

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
    channel = self.bot.get_channel(self.status_channel_id)
    await channel.send(embed=embed)

@boss_attack_task.before_loop
async def before_boss_attack(self):
    await self.bot.wait_until_ready()

@rank_update.before_loop
async def before_rank_update(self):
    await self.bot.wait_until_ready()
