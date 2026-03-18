import sqlite3
import os

# Caminho do banco de dados (na mesma pasta do projeto)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'banco.db')

# No Vercel, o diretório raiz é somente leitura. Precisamos usar o /tmp.
IS_VERCEL = os.environ.get('VERCEL') == '1'

if IS_VERCEL:
    DB_PATH = '/tmp/banco.db'
    # Se o banco não existir no /tmp, copiamos o original se ele existir no BASE_DIR
    if not os.path.exists(DB_PATH):
        original_db = os.path.join(BASE_DIR, 'banco.db')
        if os.path.exists(original_db):
            import shutil
            try:
                shutil.copy2(original_db, DB_PATH)
                print(f"Banco de dados copiado para {DB_PATH}")
            except Exception as e:
                print(f"Erro ao copiar banco para /tmp: {e}")


def conectar():
    """Cria e retorna uma conexão com o banco de dados SQLite."""
    try:
        # No Vercel, garantimos que o diretório exista (embora /tmp sempre exista)
        if IS_VERCEL:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            
        conexao = sqlite3.connect(DB_PATH)
        conexao.execute("PRAGMA foreign_keys = ON")  # Ativa chaves estrangeiras
        return conexao
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None


def criar_tabelas():
    """Cria todas as tabelas do sistema se não existirem."""
    conexao = conectar()
    if conexao is None:
        print("Não foi possível conectar ao banco de dados.")
        return

    cursor = conexao.cursor()

    # Tabela clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            email TEXT,
            cpf TEXT UNIQUE NOT NULL,
            cep TEXT,
            rua TEXT,
            bairro TEXT,
            cidade TEXT,
            estado TEXT
        )
    ''')

    # Tabela veículos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            ano TEXT,
            cor TEXT,
            placa TEXT UNIQUE NOT NULL,
            cliente_id INTEGER NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
        )
    ''')

    # Tabela serviços (catálogo)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Particular'
        )
    ''')

    # Tabela orçamentos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orcamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            data_criacao TEXT NOT NULL DEFAULT (date('now')),
            data_atualizacao TEXT NOT NULL DEFAULT (date('now')),
            status TEXT NOT NULL DEFAULT 'Pendente',
            observacoes TEXT,
            valor_total REAL NOT NULL DEFAULT 0.0
        )
    ''')

    # Tabela itens do orçamento
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orcamento_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orcamento_id INTEGER NOT NULL,
            servico_id INTEGER,
            servico_nome TEXT,
            servico_tipo TEXT,
            descricao_personalizada TEXT,
            valor_unitario REAL NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE
        )
    ''')

    conexao.commit()
    conexao.close()
    print("Tabelas criadas ou já existem.")
