import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'banco.db')

def migrate():
    # Desativa foreign keys durante a migração para evitar erros ao dropar tabelas
    conexao = sqlite3.connect(DB_PATH)
    conexao.execute("PRAGMA foreign_keys = OFF")
    cursor = conexao.cursor()
    
    try:
        # Pega as colunas existentes para orcamentos para garantir que passamos os IDs, data, etc.
        # Criar nova tabela orcamentos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orcamentos_new (
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
        
        # Migrar dados de orcamentos, juntando com clientes e veiculos para capturar os snapshots atuais
        cursor.execute('''
            INSERT INTO orcamentos_new (id, cliente_id, veiculo_id, cliente_nome, cliente_telefone, cliente_cpf,
                                        veiculo_placa, veiculo_marca, veiculo_modelo, veiculo_ano, veiculo_cor,
                                        data_criacao, data_atualizacao, status, observacoes, valor_total)
            SELECT o.id, o.cliente_id, o.veiculo_id, c.nome, c.telefone, c.cpf,
                   v.placa, v.marca, v.modelo, v.ano, v.cor,
                   o.data_criacao, o.data_atualizacao, o.status, o.observacoes, o.valor_total
            FROM orcamentos o
            LEFT JOIN clientes c ON o.cliente_id = c.id
            LEFT JOIN veiculos v ON o.veiculo_id = v.id
        ''')
        
        # Criar nova tabela orcamento_itens
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orcamento_itens_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orcamento_id INTEGER NOT NULL,
                servico_id INTEGER,
                servico_nome TEXT,
                servico_tipo TEXT,
                descricao_personalizada TEXT,
                valor_unitario REAL NOT NULL,
                quantidade INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (orcamento_id) REFERENCES orcamentos_new(id) ON DELETE CASCADE
            )
        ''')
        
        # Migrar dados de orcamento_itens, juntando com servicos
        cursor.execute('''
            INSERT INTO orcamento_itens_new (id, orcamento_id, servico_id, servico_nome, servico_tipo,
                                             descricao_personalizada, valor_unitario, quantidade)
            SELECT oi.id, oi.orcamento_id, oi.servico_id, s.nome, s.tipo,
                   oi.descricao_personalizada, oi.valor_unitario, oi.quantidade
            FROM orcamento_itens oi
            LEFT JOIN servicos s ON oi.servico_id = s.id
        ''')
        
        # Drop tabelas antigas
        cursor.execute('DROP TABLE orcamento_itens')
        cursor.execute('DROP TABLE orcamentos')
        
        # Renomear novas
        cursor.execute('ALTER TABLE orcamentos_new RENAME TO orcamentos')
        cursor.execute('ALTER TABLE orcamento_itens_new RENAME TO orcamento_itens')

        # Adiciona colunas numero e complemento à tabela clientes (se ainda não existirem)
        try:
            cursor.execute('ALTER TABLE clientes ADD COLUMN numero TEXT')
        except Exception:
            pass  # Coluna já existe
        try:
            cursor.execute('ALTER TABLE clientes ADD COLUMN complemento TEXT')
        except Exception:
            pass  # Coluna já existe
        
        conexao.commit()
        print("Migração concluída com sucesso.")
    except Exception as e:
        conexao.rollback()
        print(f"Erro na migração: {e}")
    finally:
        conexao.close()

if __name__ == '__main__':
    migrate()
