from db import conectar, DatabaseError
from datetime import datetime, timezone, timedelta
import string
import secrets

BRT = timezone(timedelta(hours=-3))

# Caracteres permitidos no código identificador de orçamento
# Alfanuméricos + caracteres especiais (exceto espaço, ponto, vírgula e similares)
CODIGO_CHARS = string.ascii_letters + string.digits + '!@#$%&*_-'


def gerar_codigo_orcamento():
    """Gera um código identificador único de 15 caracteres alfanuméricos com caracteres especiais."""
    while True:
        codigo = ''.join(secrets.choice(CODIGO_CHARS) for _ in range(15))
        # Verifica se o código já existe no banco
        conexao = conectar()
        if conexao is None:
            return codigo  # Em caso de erro, retorna sem verificar

        cursor = conexao.cursor()
        try:
            cursor.execute('SELECT id FROM orcamentos WHERE codigo_orcamento = ?', (codigo,))
            if cursor.fetchone() is None:
                return codigo  # Código único encontrado
        except DatabaseError:
            return codigo
        finally:
            conexao.close()


def criar_orcamento(cliente_id, veiculo_id, observacoes=''):
    """Cria um novo orçamento com status 'Pendente'."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        # Busca dados do cliente
        cursor.execute("SELECT nome, telefone, cpf FROM clientes WHERE id = ?", (cliente_id,))
        cliente_ref = cursor.fetchone()
        if not cliente_ref:
            return False, "Cliente não encontrado.", None
        cliente_nome, cliente_telefone, cliente_cpf = cliente_ref

        # Busca dados do veiculo
        cursor.execute("SELECT placa, marca, modelo, ano, cor FROM veiculos WHERE id = ?", (veiculo_id,))
        veiculo_ref = cursor.fetchone()
        if not veiculo_ref:
            return False, "Veículo não encontrado.", None
        veiculo_placa, veiculo_marca, veiculo_modelo, veiculo_ano, veiculo_cor = veiculo_ref

        # Gera o código identificador único
        codigo_orcamento = gerar_codigo_orcamento()

        agora = datetime.now(tz=BRT).strftime("%Y-%m-%d %H:%M")
        cursor.execute('''
            INSERT INTO orcamentos (cliente_id, veiculo_id, cliente_nome, cliente_telefone, cliente_cpf,
                                    veiculo_placa, veiculo_marca, veiculo_modelo, veiculo_ano, veiculo_cor,
                                    data_criacao, data_atualizacao, status, observacoes, valor_total, codigo_orcamento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pendente', ?, 0.0, ?)
        ''', (cliente_id, veiculo_id, cliente_nome, cliente_telefone, cliente_cpf,
              veiculo_placa, veiculo_marca, veiculo_modelo, veiculo_ano, veiculo_cor, agora, agora, observacoes, codigo_orcamento))
        conexao.commit()
        orcamento_id = cursor.lastrowid
        return True, "Orçamento criado com sucesso.", orcamento_id
    except DatabaseError as e:
        return False, f"Erro ao criar orçamento: {e}", None
    finally:
        conexao.close()


def listar_orcamentos(filtro=None, status_filtro=None):
    """Lista todos os orçamentos com dados do cliente e veículo."""
    conexao = conectar()
    if conexao is None:
        return []

    cursor = conexao.cursor()
    try:
        query = '''
            SELECT id, cliente_nome, 
                   veiculo_placa,
                   veiculo_marca || ' ' || veiculo_modelo AS veiculo_desc,
                   data_atualizacao AS data_formatada, status, 
                   valor_total, observacoes, codigo_orcamento
            FROM orcamentos
        '''
        conditions = []
        params = []

        if filtro:
            like = f'%{filtro}%'
            conditions.append('(cliente_nome LIKE ? OR veiculo_placa LIKE ?)')
            params.extend([like, like])

        if status_filtro and status_filtro != 'Todos':
            conditions.append('status = ?')
            params.append(status_filtro)

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += ' ORDER BY data_atualizacao DESC, id DESC'
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Formata a data de atualização pelo Python para ser compatível com SQLite e Postgres
        resultado = []
        for row in rows:
            row_list = list(row)
            try:
                # O banco armazena no formato '%Y-%m-%d %H:%M'
                dt_obj = datetime.strptime(str(row_list[4]), '%Y-%m-%d %H:%M')
                row_list[4] = dt_obj.strftime('%d/%m/%Y %H:%M')
            except ValueError:
                pass # Caso venha diferente do esperado (ex: datas truncadas), mantém original
            resultado.append(tuple(row_list))
        return resultado
    except DatabaseError as e:
        print(f"Erro ao listar orçamentos: {e}")
        return []
    finally:
        conexao.close()


def buscar_orcamento_por_id(id):
    """Busca um orçamento pelo ID com dados completos."""
    conexao = conectar()
    if conexao is None:
        return None

    cursor = conexao.cursor()
    try:
        cursor.execute('''
            SELECT id, cliente_id, veiculo_id,
                   cliente_nome, cliente_telefone,
                   cliente_cpf,
                   veiculo_placa,
                   veiculo_marca || ' ' || veiculo_modelo AS veiculo_desc,
                   veiculo_ano, veiculo_cor,
                   data_atualizacao AS data_formatada, status, 
                   valor_total, observacoes, codigo_orcamento
            FROM orcamentos
            WHERE id = ?
        ''', (id,))
        row = cursor.fetchone()
        if row:
            row_list = list(row)
            # data_formatada está no índice 10
            try:
                dt_obj = datetime.strptime(str(row_list[10]), '%Y-%m-%d %H:%M')
                row_list[10] = dt_obj.strftime('%d/%m/%Y %H:%M')
            except ValueError:
                pass
            return tuple(row_list)
        return None
    except DatabaseError as e:
        print(f"Erro ao buscar orçamento: {e}")
        return None
    finally:
        conexao.close()


def buscar_orcamento_por_codigo(codigo):
    """Busca um orçamento pelo código identificador."""
    conexao = conectar()
    if conexao is None:
        return None

    cursor = conexao.cursor()
    try:
        cursor.execute('''
            SELECT id, cliente_id, veiculo_id,
                   cliente_nome, cliente_telefone,
                   cliente_cpf,
                   veiculo_placa,
                   veiculo_marca || ' ' || veiculo_modelo AS veiculo_desc,
                   veiculo_ano, veiculo_cor,
                   data_atualizacao AS data_formatada, status, 
                   valor_total, observacoes, codigo_orcamento
            FROM orcamentos
            WHERE codigo_orcamento = ?
        ''', (codigo,))
        row = cursor.fetchone()
        if row:
            row_list = list(row)
            try:
                dt_obj = datetime.strptime(str(row_list[10]), '%Y-%m-%d %H:%M')
                row_list[10] = dt_obj.strftime('%d/%m/%Y %H:%M')
            except ValueError:
                pass
            return tuple(row_list)
        return None
    except DatabaseError as e:
        print(f"Erro ao buscar orçamento por código: {e}")
        return None
    finally:
        conexao.close()


def listar_itens_orcamento(orcamento_id):
    """Lista todos os itens de um orçamento específico."""
    conexao = conectar()
    if conexao is None:
        return []

    cursor = conexao.cursor()
    try:
        cursor.execute('''
            SELECT id, servico_id,
                   COALESCE(servico_nome, 'Personalizado') AS servico_nome,
                   descricao_personalizada,
                   valor_unitario,
                   COALESCE(servico_tipo, 'Particular') AS servico_tipo
            FROM orcamento_itens
            WHERE orcamento_id = ?
            ORDER BY id
        ''', (orcamento_id,))
        return cursor.fetchall()
    except DatabaseError as e:
        print(f"Erro ao listar itens do orçamento: {e}")
        return []
    finally:
        conexao.close()


def adicionar_item(orcamento_id, servico_id, descricao_personalizada, valor_unitario, tipo='Particular'):
    conexao = conectar()
    if conexao is None: return False, "Erro de conexão."
    cursor = conexao.cursor()

    try:
        servico_nome = None
        if servico_id:
            cursor.execute('SELECT nome FROM servicos WHERE id = ?', (servico_id,))
            srv = cursor.fetchone()
            if srv: servico_nome = srv[0]

        cursor.execute('''
            INSERT INTO orcamento_itens 
            (orcamento_id, servico_id, servico_nome, servico_tipo, descricao_personalizada, valor_unitario)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (orcamento_id, servico_id, servico_nome, tipo, descricao_personalizada, valor_unitario))
        
        # Atualiza valor total do orçamento (sem multiplicar por quantidade)
        cursor.execute('''
            UPDATE orcamentos 
            SET valor_total = (SELECT COALESCE(SUM(valor_unitario), 0) FROM orcamento_itens WHERE orcamento_id = ?),
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (orcamento_id, orcamento_id))
        
        conexao.commit()
        return True, "Item adicionado com sucesso."
    except DatabaseError as e:
        conexao.rollback()
        return False, f"Erro ao adicionar item: {e}"
    finally:
        conexao.close()


def remover_item(item_id):
    """Remove um item do orçamento e recalcula o valor total."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        # Busca o orcamento_id antes de remover
        cursor.execute('SELECT orcamento_id FROM orcamento_itens WHERE id = ?', (item_id,))
        resultado = cursor.fetchone()
        if resultado is None:
            return False, "Item não encontrado."

        orcamento_id = resultado[0]
        cursor.execute('DELETE FROM orcamento_itens WHERE id = ?', (item_id,))

        # Recalcula o valor total
        _recalcular_total(cursor, orcamento_id)

        conexao.commit()
        return True, "Item removido do orçamento."
    except DatabaseError as e:
        return False, f"Erro ao remover item: {e}"
    finally:
        conexao.close()


def atualizar_status(id, novo_status):
    """Atualiza o status de um orçamento."""
    status_validos = ['Pendente', 'Aprovado', 'Recusado', 'Concluído']
    if novo_status not in status_validos:
        return False, f"Status inválido. Use: {', '.join(status_validos)}"

    conexao = conectar()
    cursor = conexao.cursor()
    try:
        agora = datetime.now(tz=BRT).strftime("%Y-%m-%d %H:%M")
        cursor.execute('UPDATE orcamentos SET status = ?, data_atualizacao = ? WHERE id = ?', (novo_status, agora, id))
        conexao.commit()
        return True, f"Status atualizado para '{novo_status}'."
    except DatabaseError as e:
        return False, f"Erro ao atualizar status: {e}"
    finally:
        conexao.close()


def atualizar_observacoes(id, observacoes):
    """Atualiza as observações de um orçamento."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        agora = datetime.now(tz=BRT).strftime("%Y-%m-%d %H:%M")
        cursor.execute('UPDATE orcamentos SET observacoes = ?, data_atualizacao = ? WHERE id = ?', (observacoes, agora, id))
        conexao.commit()
        return True, "Observações atualizadas."
    except DatabaseError as e:
        return False, f"Erro ao atualizar observações: {e}"
    finally:
        conexao.close()


def excluir_orcamento(id):
    """Exclui um orçamento e todos os seus itens."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute('DELETE FROM orcamentos WHERE id = ?', (id,))
        conexao.commit()
        return True, "Orçamento excluído com sucesso."
    except DatabaseError as e:
        return False, f"Erro ao excluir orçamento: {e}"
    finally:
        conexao.close()


def contar_por_status():
    """Retorna a contagem de orçamentos por status."""
    conexao = conectar()
    if conexao is None:
        return {}

    cursor = conexao.cursor()
    try:
        cursor.execute('''
            SELECT status, COUNT(*) FROM orcamentos GROUP BY status
        ''')
        return dict(cursor.fetchall())
    except DatabaseError as e:
        print(f"Erro ao contar orçamentos: {e}")
        return {}
    finally:
        conexao.close()


def _recalcular_total(cursor, orcamento_id):
    """Recalcula o valor total de um orçamento e atualiza a data (uso interno)."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute('''
        UPDATE orcamentos SET valor_total = (
            SELECT COALESCE(SUM(valor_unitario), 0.0)
            FROM orcamento_itens WHERE orcamento_id = ?
        ), data_atualizacao = ? WHERE id = ?
    ''', (orcamento_id, agora, orcamento_id))
