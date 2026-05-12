import os
from db import conectar, criar_tabelas

def resetar_banco():
    print("Conectando ao banco de dados...")
    conexao = conectar()
    if not conexao:
        print("Erro: Não foi possível conectar ao banco de dados.")
        return

    cursor = conexao.cursor()
    
    tabelas = ['orcamento_itens', 'orcamentos', 'veiculos', 'servicos', 'clientes']
    
    print("Apagando tabelas existentes...")
    for tabela in tabelas:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {tabela} CASCADE" if 'POSTGRES_URL' in os.environ else f"DROP TABLE IF EXISTS {tabela}")
            print(f"Tabela {tabela} apagada.")
        except Exception as e:
            print(f"Aviso ao apagar {tabela}: {e}")
            
    conexao.commit()
    conexao.close()
    
    print("\nRecriando tabelas com o novo formato...")
    criar_tabelas()
    print("Tabelas recriadas com sucesso!")

if __name__ == '__main__':
    resetar_banco()
