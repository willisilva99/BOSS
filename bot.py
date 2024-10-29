import discord
from discord.ext import commands, tasks
import os
import asyncpg
import asyncio
import random
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração de intents e prefixo
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="n!", intents=intents)

# URL de conexão com o banco de dados
DATABASE_URL = os.getenv("DATABASE_URL")

# Lista de cogs
cogs = [
    "boss",  # Cog do boss com funcionalidades avançadas
]

# Mensagens de status aleatórias para dar mais imersão ao bot
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

async def setup_database():
    # Conecta ao banco de dados e cria as tabelas, se não existirem
    try:
        bot.pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
        print("Conexão com o banco de dados estabelecida com sucesso.")

        async with bot.pool.acquire() as connection:
            # Criação das tabelas no banco de dados
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id BIGINT PRIMARY KEY,
                    wounds INTEGER DEFAULT 0,
                    money INTEGER DEFAULT 1000,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    infected BOOLEAN DEFAULT FALSE,
                    damage_debuff BOOLEAN DEFAULT FALSE
                );
            """)

            await connection.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES players(user_id) ON DELETE CASCADE,
                    item TEXT NOT NULL
                );
            """)

            # Tabela para Classes
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS classes (
                    class_id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT
                );
            """)

            # Tabela para Associar Jogadores às Classes
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS player_classes (
                    user_id BIGINT REFERENCES players(user_id) ON DELETE CASCADE,
                    class_id INTEGER REFERENCES classes(class_id) ON DELETE SET NULL,
                    PRIMARY KEY (user_id)
                );
            """)

            # Tabela para Itens da Loja
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS shop_items (
                    item_id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    cost INTEGER NOT NULL,
                    rarity TEXT CHECK (rarity IN ('comum', 'raro', 'épico')) NOT NULL
                );
            """)

            # Tabela para Debuffs (Caso queira gerenciar múltiplos debuffs)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS debuffs (
                    debuff_id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    duration INTEGER NOT NULL  -- duração em segundos
                );
            """)

            # Tabela para Gerenciar Debuffs Aplicados aos Jogadores
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS player_debuffs (
                    user_id BIGINT REFERENCES players(user_id) ON DELETE CASCADE,
                    debuff_id INTEGER REFERENCES debuffs(debuff_id) ON DELETE CASCADE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, debuff_id)
                );
            """)

            # Definição das colunas necessárias para cada tabela
            required_columns = {
                "players": {
                    "wounds": "INTEGER DEFAULT 0",
                    "money": "INTEGER DEFAULT 1000",
                    "xp": "INTEGER DEFAULT 0",
                    "level": "INTEGER DEFAULT 1",
                    "infected": "BOOLEAN DEFAULT FALSE",
                    "damage_debuff": "BOOLEAN DEFAULT FALSE"
                },
                "inventory": {
                    "item": "TEXT NOT NULL"
                },
                "classes": {
                    "name": "TEXT UNIQUE NOT NULL",
                    "description": "TEXT"
                },
                "player_classes": {
                    "user_id": "BIGINT REFERENCES players(user_id) ON DELETE CASCADE",
                    "class_id": "INTEGER REFERENCES classes(class_id) ON DELETE SET NULL"
                },
                "shop_items": {
                    "name": "TEXT NOT NULL",
                    "description": "TEXT",
                    "cost": "INTEGER NOT NULL",
                    "rarity": "TEXT CHECK (rarity IN ('comum', 'raro', 'épico')) NOT NULL"
                },
                "debuffs": {
                    "name": "TEXT NOT NULL",
                    "description": "TEXT",
                    "duration": "INTEGER NOT NULL"
                },
                "player_debuffs": {
                    "user_id": "BIGINT REFERENCES players(user_id) ON DELETE CASCADE",
                    "debuff_id": "INTEGER REFERENCES debuffs(debuff_id) ON DELETE CASCADE",
                    "applied_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                }
            }

            for table, columns in required_columns.items():
                existing_columns = await connection.fetch("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = $1;
                """, table)

                existing_columns = {record['column_name'] for record in existing_columns}

                for column, definition in columns.items():
                    if column not in existing_columns:
                        alter_query = f"ALTER TABLE {table} ADD COLUMN {column} {definition};"
                        try:
                            await connection.execute(alter_query)
                            print(f"Coluna '{column}' adicionada à tabela '{table}'.")
                        except Exception as e:
                            print(f"Erro ao adicionar a coluna '{column}' na tabela '{table}': {e}")

    async def load_cogs():
        # Carrega todos os cogs listados
        for cog in cogs:
            try:
                await bot.load_extension(f"cogs.{cog}")
                print(f"Cog '{cog}' carregado com sucesso.")
            except Exception as e:
                print(f"Erro ao carregar o cog '{cog}': {e}")

    @tasks.loop(minutes=10)
    async def change_status():
        # Atualiza o status do bot aleatoriamente a cada 10 minutos
        new_status = random.choice(status_messages)
        await bot.change_presence(activity=discord.Game(new_status))

    @bot.event
    async def on_ready():
        print(f"Bot conectado como {bot.user}")
        print("Bot está pronto e todos os cogs foram carregados.")
        change_status.start()  # Inicia a tarefa de mudança de status

    @bot.event
    async def on_command_error(ctx, error):
        # Captura e exibe erros de comando
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏳ Cooldown Ativo",
                description=f"O comando `{ctx.command}` está em cooldown. Tente novamente em {error.retry_after:.2f} segundos.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, asyncpg.exceptions.UndefinedColumnError):
            embed = discord.Embed(
                title="⚠️ Erro no Banco de Dados",
                description="Ocorreu um erro no banco de dados: coluna inexistente.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            print(f"Erro detectado: {error}")
        else:
            # Captura e exibe outros erros de comando
            embed = discord.Embed(
                title="⚠️ Erro de Comando",
                description=f"Ocorreu um erro ao executar `{ctx.command}`:\n{error}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            print(f"Erro detectado: {error}")

    @bot.event
    async def on_message(message):
        # Ignora mensagens do próprio bot e processa comandos nas mensagens
        if message.author == bot.user:
            return
        await bot.process_commands(message)

    async def setup_bot():
        await setup_database()  # Configura e conecta o banco de dados
        await load_cogs()       # Carrega os cogs
        await bot.start(os.getenv("TOKEN"))  # Inicia o bot com o token do .env

    if __name__ == "__main__":
        asyncio.run(setup_bot())
    ```

### **Alterações Realizadas**

1. **Correção do Dicionário `required_columns`:**
   - **Removido:** `"PRIMARY KEY (user_id)"` da tabela `player_classes`.
   - **Mantido:** Apenas os nomes das colunas (`"user_id"` e `"class_id"`) com suas definições.
   - **Revisado:** Certifique-se de que somente nomes de colunas válidos e suas definições estejam presentes como chaves no dicionário.

2. **Tratamento de Erros Adicionais em PT-BR:**
   - Adicionei um tratamento específico para `asyncpg.exceptions.UndefinedColumnError`, que envia uma mensagem de erro em Português ao usuário e imprime o erro no console.
   - Todas as mensagens de erro e logs foram traduzidas para PT-BR.

3. **Manutenção das Restrições de Tabela no `CREATE TABLE`:**
   - As restrições de tabela, como `PRIMARY KEY` e `FOREIGN KEY`, permanecem definidas nas consultas `CREATE TABLE`. Elas não precisam estar no dicionário `required_columns`.

### **Verificação das Alterações no Banco de Dados**

Após implementar essas alterações, siga os passos abaixo para garantir que o banco de dados está configurado corretamente:

1. **Executar o Bot:**
   - Inicie o bot executando o script:
     ```bash
     python bot.py
     ```
   - Observe o console para garantir que não há erros de sintaxe e que as colunas faltantes estão sendo adicionadas.

2. **Verificar as Tabelas e Colunas:**
   - **Para PostgreSQL:**
     ```sql
     \d players
     ```
   - **Para MySQL:**
     ```sql
     DESCRIBE players;
     ```
   - Certifique-se de que as colunas `infected` e `damage_debuff` existem na tabela `players`, além das outras colunas definidas.

### **Testando os Comandos do Bot**

Após corrigir o erro de sintaxe, é fundamental testar os comandos para garantir que tudo está funcionando conforme o esperado.

1. **Usar o Comando `!boss`:**
   - Envie o comando `n!boss` no canal designado para combates.
   - **Primeira Invocação:** O boss deve ser invocado, e uma mensagem informando sua aparição deve ser enviada.
   - **Invocações Subsequentes Antes do Cooldown Expirar:** Você deve receber uma mensagem informando que o comando está em cooldown e quanto tempo resta para tentar novamente.

2. **Verificar a Aplicação de Infecção e Debuffs:**
   - Após atacar o boss, verifique se as colunas `infected` e `damage_debuff` estão sendo atualizadas corretamente no banco de dados.
   - **Exemplo de Consulta:**
     ```sql
     SELECT user_id, infected, damage_debuff FROM players WHERE user_id = <ID_DO_USUARIO>;
     ```

3. **Forçar um Erro de Coluna Inexistente (Opcional):**
   - Para testar o tratamento de erros, você pode temporariamente remover a coluna `infected` do banco de dados e tentar usar o comando `!boss` novamente para ver se a mensagem de erro personalizada é exibida.
   - **Comando SQL para Remover a Coluna (Cuidado!):**
     ```sql
     ALTER TABLE players DROP COLUMN infected;
     ```
   - **Nota:** Certifique-se de ter um backup do banco de dados antes de realizar alterações destrutivas.

### **Considerações Finais**

- **Backup do Banco de Dados:**
  - Antes de executar scripts que alteram o esquema do banco de dados, sempre faça um backup para evitar perda de dados em caso de erros inesperados.

- **Gerenciamento de Migrações:**
  - Para projetos maiores, considere utilizar ferramentas de migração de banco de dados como **Alembic** (para SQLAlchemy) ou outras ferramentas compatíveis com `asyncpg`. Isso facilitará o gerenciamento de alterações no esquema do banco de dados ao longo do tempo.

- **Permissões do Banco de Dados:**
  - Assegure-se de que o usuário do banco de dados que o bot está utilizando possui as permissões necessárias para alterar o esquema das tabelas (adicionar colunas, criar tabelas, etc.).

- **Manter o Dicionário `required_columns` Atualizado:**
  - Sempre que adicionar novas colunas ou tabelas no seu projeto, atualize o dicionário `required_columns` na função `setup_database` para garantir que o banco de dados seja atualizado automaticamente.

- **Monitorar Logs e Mensagens de Erro:**
  - Continue monitorando os logs do seu bot para identificar e resolver quaisquer novos erros que possam surgir.

Se você seguir esses passos e realizar as correções necessárias, o seu bot deve funcionar corretamente sem gerar erros de sintaxe ou problemas relacionados ao banco de dados. Se encontrar mais problemas ou tiver dúvidas adicionais, sinta-se à vontade para perguntar!
