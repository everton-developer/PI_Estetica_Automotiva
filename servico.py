# servico.py
from db import conectar
import sqlite3


def cadastrar_servico(nome, descricao, valor, tipo='Particular'):
    """Cadastra um novo serviço no catálogo."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute('SELECT id FROM servicos WHERE LOWER(nome) = LOWER(?) AND tipo = ?', (nome, tipo))
        if cursor.fetchone():
            return False, "Erro: Serviço já cadastrado com este Nome e Tipo."

        cursor.execute('''
            INSERT INTO servicos (nome, descricao, valor, tipo) VALUES (?, ?, ?, ?)
        ''', (nome, descricao, valor, tipo))
        conexao.commit()
        return True, "Serviço cadastrado com sucesso."
    except sqlite3.Error as e:
        return False, f"Erro ao cadastrar serviço: {e}"
    finally:
        conexao.close()


def listar_servicos(filtro=None):
    """Lista todos os serviços ou filtra por nome/descrição."""
    conexao = conectar()
    if conexao is None:
        return []

    cursor = conexao.cursor()
    try:
        query = 'SELECT id, nome, descricao, valor, tipo FROM servicos'
        params = []

        if filtro:
            like = f'%{filtro}%'
            query += ' WHERE nome LIKE ? OR descricao LIKE ?'
            params = [like, like]

        query += ' ORDER BY nome'
        cursor.execute(query, params)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Erro ao listar serviços: {e}")
        return []
    finally:
        conexao.close()


def buscar_servico_por_id(id):
    """Busca um único serviço pelo ID."""
    conexao = conectar()
    if conexao is None:
        return None

    cursor = conexao.cursor()
    try:
        cursor.execute('SELECT id, nome, descricao, valor, tipo FROM servicos WHERE id = ?', (id,))
        return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"Erro ao buscar serviço: {e}")
        return None
    finally:
        conexao.close()


def editar_servico(id, nome, descricao, valor, tipo='Particular'):
    """Atualiza os dados de um serviço existente."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute('SELECT id FROM servicos WHERE LOWER(nome) = LOWER(?) AND tipo = ? AND id != ?', (nome, tipo, id))
        if cursor.fetchone():
            return False, "Erro: Serviço já cadastrado com este Nome e Tipo."

        cursor.execute('''
            UPDATE servicos SET nome = ?, descricao = ?, valor = ?, tipo = ? WHERE id = ?
        ''', (nome, descricao, valor, tipo, id))
        conexao.commit()
        return True, "Serviço atualizado com sucesso."
    except sqlite3.Error as e:
        return False, f"Erro ao atualizar serviço: {e}"
    finally:
        conexao.close()


def excluir_servico(id):
    """Exclui um serviço pelo ID."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute('DELETE FROM servicos WHERE id = ?', (id,))
        conexao.commit()
        return True, "Serviço excluído com sucesso."
    except sqlite3.Error as e:
        return False, f"Erro ao excluir serviço: {e}"
    finally:
        conexao.close()
