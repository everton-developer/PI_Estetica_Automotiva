import os

# No Vercel, o diretório raiz é somente leitura.
IS_VERCEL = os.environ.get('VERCEL') == '1'
DATABASE_URL = os.environ.get('POSTGRES_URL') # Vercel Postgres

class CursorWrapper:
    """Wrapper para o cursor que converte '?' em '%s' se for Postgres e trata lastrowid."""
    def __init__(self, cursor, is_postgres):
        self._cursor = cursor
        self._is_postgres = is_postgres
        self._lastrowid = None

    def execute(self, query, params=None):
        if self._is_postgres and query:
            # Converte ? para %s
            query = query.replace('?', '%s')
            # Converte strftime para TO_CHAR (simplificado para o que o app usa)
            # SQLite: strftime('%d/%m/%Y %H:%M', data_atualizacao)
            # Postgres: TO_CHAR(data_atualizacao, 'DD/MM/YYYY HH24:MI')
            if 'strftime' in query:
                import re
                query = re.sub(r"strftime\('%d/%m/%Y %H:%M',\s*(.*?)\)", r"TO_CHAR(\1, 'DD/MM/YYYY HH24:MI')", query)
            
            # Se for INSERT e não tiver RETURNING, adicionamos para pegar o lastrowid
            is_insert = query.strip().upper().startswith('INSERT')
            if is_insert and 'RETURNING' not in query.upper():
                query += ' RETURNING id'
                
            res = self._cursor.execute(query, params) if params is not None else self._cursor.execute(query)
            
            if is_insert:
                try:
                    row = self._cursor.fetchone()
                    if row: self._lastrowid = row[0]
                except: pass
            return res
        
        return self._cursor.execute(query, params) if params is not None else self._cursor.execute(query)

    @property
    def lastrowid(self):
        if self._is_postgres: return self._lastrowid
        return self._cursor.lastrowid

    def fetchone(self): return self._cursor.fetchone()
    def fetchall(self): return self._cursor.fetchall()
    def close(self): return self._cursor.close()
    
    def __getattr__(self, name):
        return getattr(self._cursor, name)

class ConnectionWrapper:
    """Wrapper para a conexão que retorna um CursorWrapper."""
    def __init__(self, conexao, is_postgres):
        self._conexao = conexao
        self._is_postgres = is_postgres

    def cursor(self):
        return CursorWrapper(self._conexao.cursor(), self._is_postgres)

    def commit(self): return self._conexao.commit()
    def close(self): return self._conexao.close()
    def execute(self, *args, **kwargs): return self._conexao.execute(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._conexao, name)

import sqlite3
try: import psycopg2
except: psycopg2 = None

# Exportando erros genéricos para compatibilidade
DatabaseError = Exception # Base para erros de banco
IntegrityError = Exception # Base para erros de integridade

def conectar():
    """Cria e retorna uma conexão com o banco de dados (Postgres ou SQLite)."""
    global DatabaseError, IntegrityError
    if DATABASE_URL and psycopg2:
        try:
            conexao = psycopg2.connect(DATABASE_URL)
            DatabaseError = psycopg2.Error
            IntegrityError = psycopg2.IntegrityError
            return ConnectionWrapper(conexao, True)
        except Exception as e:
            print(f"Erro ao conectar ao Postgres: {e}")
            return None
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(BASE_DIR, 'banco.db')
        
        if IS_VERCEL:
            db_path = '/tmp/banco.db'
            if not os.path.exists(db_path):
                original_db = os.path.join(BASE_DIR, 'banco.db')
                if os.path.exists(original_db):
                    import shutil
                    try: shutil.copy2(original_db, db_path)
                    except: pass

        try:
            conexao = sqlite3.connect(db_path)
            conexao.execute("PRAGMA foreign_keys = ON")
            DatabaseError = sqlite3.Error
            IntegrityError = sqlite3.IntegrityError
            return ConnectionWrapper(conexao, False)
        except sqlite3.Error as e:
            print(f"Erro ao conectar ao SQLite: {e}")
            return None

def criar_tabelas():
    """Cria todas as tabelas do sistema se não existirem."""
    conexao = conectar()
    if conexao is None: return

    cursor = conexao.cursor()
    
    # Abstração simples para autoincremento (Postgres vs SQLite)
    is_postgres = DATABASE_URL is not None
    auto_inc = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    now_func = "CURRENT_DATE" if is_postgres else "(date('now'))"

    # Criamos as tabelas usando placeholders adaptados (aunque aqui não usamos)
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS clientes (
            id {auto_inc},
            nome TEXT NOT NULL,
            telefone TEXT,
            email TEXT,
            cpf TEXT UNIQUE,
            cep TEXT,
            rua TEXT,
            numero TEXT,
            complemento TEXT,
            bairro TEXT,
            cidade TEXT,
            estado TEXT
        )
    ''')

    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS veiculos (
            id {auto_inc},
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            ano TEXT,
            cor TEXT,
            placa TEXT UNIQUE NOT NULL,
            cliente_id INTEGER NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS servicos (
            id {auto_inc},
            nome TEXT NOT NULL,
            descricao TEXT,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Particular'
        )
    ''')

    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS orcamentos (
            id {auto_inc},
            cliente_id INTEGER,
            veiculo_id INTEGER,
            cliente_nome TEXT,
            cliente_telefone TEXT,
            cliente_cpf TEXT,
            veiculo_placa TEXT,
            veiculo_marca TEXT,
            veiculo_modelo TEXT,
            veiculo_ano TEXT,
            veiculo_cor TEXT,
            data_criacao TEXT NOT NULL DEFAULT {now_func},
            data_atualizacao TEXT NOT NULL DEFAULT {now_func},
            status TEXT NOT NULL DEFAULT 'Pendente',
            observacoes TEXT,
            valor_total REAL NOT NULL DEFAULT 0.0
        )
    ''')

    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS orcamento_itens (
            id {auto_inc},
            orcamento_id INTEGER NOT NULL,
            servico_id INTEGER,
            servico_nome TEXT,
            servico_tipo TEXT,
            descricao_personalizada TEXT,
            valor_unitario REAL NOT NULL,
            FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE
        )
    ''')

    conexao.commit()
    conexao.close()
    print("Tabelas verificadas/criadas.")
