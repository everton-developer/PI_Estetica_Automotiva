from db import conectar, DatabaseError, IntegrityError


def cadastrar_veiculo(marca, modelo, ano, cor, placa, cliente_id):
    """Cadastra um novo veículo vinculado a um cliente."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute('SELECT id FROM veiculos WHERE LOWER(placa) = LOWER(?)', (placa,))
        if cursor.fetchone():
            return False, "Erro: Placa já cadastrada."

        cursor.execute('''
            INSERT INTO veiculos (marca, modelo, ano, cor, placa, cliente_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (marca, modelo, ano, cor, placa, cliente_id))
        conexao.commit()
        return True, "Veículo cadastrado com sucesso."
    except IntegrityError as e:
        if "UNIQUE constraint failed: veiculos.placa" in str(e) or "duplicate key" in str(e).lower():
            return False, "Erro: Placa já cadastrada."
        else:
            return False, f"Erro ao cadastrar veículo: {e}"
    except DatabaseError as e:
        return False, f"Erro ao cadastrar veículo: {e}"
    finally:
        conexao.close()


def listar_veiculos(filtro=None):
    """Lista todos os veículos ou filtra por marca/modelo/placa."""
    conexao = conectar()
    if conexao is None:
        return []

    cursor = conexao.cursor()
    try:
        query = '''
            SELECT veiculos.id, veiculos.marca, veiculos.modelo, veiculos.ano,
                   veiculos.cor, veiculos.placa, clientes.nome AS cliente_nome,
                   veiculos.cliente_id
            FROM veiculos
            JOIN clientes ON veiculos.cliente_id = clientes.id
        '''
        params = []

        if filtro:
            like = f'%{filtro}%'
            query += ''' WHERE veiculos.marca LIKE ? OR veiculos.modelo LIKE ? 
                         OR veiculos.placa LIKE ? OR clientes.nome LIKE ?'''
            params = [like, like, like, like]

        query += ' ORDER BY veiculos.marca, veiculos.modelo'
        cursor.execute(query, params)
        return cursor.fetchall()
    except DatabaseError as e:
        print(f"Erro ao listar veículos: {e}")
        return []
    finally:
        conexao.close()


def buscar_veiculo_por_id(id):
    """Busca um único veículo pelo ID."""
    conexao = conectar()
    if conexao is None:
        return None

    cursor = conexao.cursor()
    try:
        cursor.execute('''
            SELECT veiculos.id, veiculos.marca, veiculos.modelo, veiculos.ano,
                   veiculos.cor, veiculos.placa, veiculos.cliente_id,
                   clientes.nome AS cliente_nome
            FROM veiculos
            JOIN clientes ON veiculos.cliente_id = clientes.id
            WHERE veiculos.id = ?
        ''', (id,))
        return cursor.fetchone()
    except DatabaseError as e:
        print(f"Erro ao buscar veículo: {e}")
        return None
    finally:
        conexao.close()


def listar_veiculos_por_cliente(cliente_id):
    """Lista todos os veículos de um cliente específico."""
    conexao = conectar()
    if conexao is None:
        return []

    cursor = conexao.cursor()
    try:
        cursor.execute('''
            SELECT id, marca, modelo, ano, cor, placa
            FROM veiculos WHERE cliente_id = ?
            ORDER BY marca, modelo
        ''', (cliente_id,))
        return cursor.fetchall()
    except DatabaseError as e:
        print(f"Erro ao listar veículos do cliente: {e}")
        return []
    finally:
        conexao.close()


def editar_veiculo(id, marca, modelo, ano, cor, placa, cliente_id):
    """Atualiza os dados de um veículo existente."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute('SELECT id FROM veiculos WHERE LOWER(placa) = LOWER(?) AND id != ?', (placa, id))
        if cursor.fetchone():
            return False, "Erro: Placa já cadastrada para outro veículo."

        cursor.execute('''
            UPDATE veiculos
            SET marca = ?, modelo = ?, ano = ?, cor = ?, placa = ?, cliente_id = ?
            WHERE id = ?
        ''', (marca, modelo, ano, cor, placa, cliente_id, id))
        conexao.commit()
        return True, "Veículo atualizado com sucesso."
    except IntegrityError as e:
        if "UNIQUE constraint failed: veiculos.placa" in str(e) or "duplicate key" in str(e).lower():
            return False, "Erro: Placa já cadastrada para outro veículo."
        else:
            return False, f"Erro ao atualizar veículo: {e}"
    except DatabaseError as e:
        return False, f"Erro ao atualizar veículo: {e}"
    finally:
        conexao.close()


def excluir_veiculo(id):
    """Exclui um veículo pelo ID."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute('DELETE FROM veiculos WHERE id = ?', (id,))
        conexao.commit()
        return True, "Veículo excluído com sucesso."
    except DatabaseError as e:
        return False, f"Erro ao excluir veículo: {e}"
    finally:
        conexao.close()
