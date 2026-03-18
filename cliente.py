from db import conectar, DatabaseError, IntegrityError


def cadastrar_cliente(nome, telefone, email, cpf, cep, rua, bairro, cidade, estado):
    """Cadastra um novo cliente no banco de dados."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute('SELECT nome, cpf FROM clientes WHERE LOWER(nome) = LOWER(?) OR cpf = ?', (nome, cpf))
        existing = cursor.fetchall()
        for ext_nome, ext_cpf in existing:
            if ext_nome.lower() == nome.lower():
                return False, "Erro: Cliente já cadastrado com este Nome."
            if ext_cpf == cpf:
                return False, "Erro: Cliente já cadastrado com este CPF."

        cursor.execute('''
            INSERT INTO clientes (nome, telefone, email, cpf, cep, rua, bairro, cidade, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nome, telefone, email, cpf, cep, rua, bairro, cidade, estado))
        conexao.commit()
        return True, "Cliente cadastrado com sucesso."
    except IntegrityError as e:
        if "UNIQUE constraint failed: clientes.cpf" in str(e) or "duplicate key" in str(e).lower():
            return False, "Erro: CPF já cadastrado."
        else:
            return False, f"Erro ao cadastrar cliente: {e}"
    except DatabaseError as e:
        return False, f"Erro ao cadastrar cliente: {e}"
    finally:
        conexao.close()


def listar_clientes(termo_busca=None):
    """Lista todos os clientes ou filtra por nome/CPF."""
    conexao = conectar()
    if conexao is None:
        return []

    cursor = conexao.cursor()
    try:
        query = '''
            SELECT id, nome, telefone, email, cpf, cep, rua, bairro, cidade, estado 
            FROM clientes
        '''
        params = []

        if termo_busca:
            like = f'%{termo_busca}%'
            query += ' WHERE nome LIKE ? OR cpf LIKE ? ORDER BY nome'
            params = [like, like]
        else:
            query += ' ORDER BY nome'

        cursor.execute(query, params)
        return cursor.fetchall()
    except DatabaseError as e:
        print(f"Erro ao listar clientes: {e}")
        return []
    finally:
        conexao.close()


def buscar_cliente_por_id(id_cliente):
    """Busca um único cliente pelo ID."""
    conexao = conectar()
    if conexao is None:
        return None

    cursor = conexao.cursor()
    try:
        cursor.execute('''
            SELECT id, nome, telefone, email, cpf, cep, rua, bairro, cidade, estado 
            FROM clientes WHERE id = ?
        ''', (id_cliente,))
        return cursor.fetchone()
    except DatabaseError as e:
        print(f"Erro ao buscar cliente: {e}")
        return None
    finally:
        conexao.close()


def atualizar_cliente(id, nome, telefone, email, cpf, cep, rua, bairro, cidade, estado):
    """Atualiza os dados de um cliente existente."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute('SELECT nome, cpf FROM clientes WHERE (LOWER(nome) = LOWER(?) OR cpf = ?) AND id != ?', (nome, cpf, id))
        existing = cursor.fetchall()
        for ext_nome, ext_cpf in existing:
            if ext_nome.lower() == nome.lower():
                return False, "Erro: Cliente já cadastrado com este Nome."
            if ext_cpf == cpf:
                return False, "Erro: Cliente já cadastrado com este CPF."

        cursor.execute('''
            UPDATE clientes
            SET nome = ?, telefone = ?, email = ?, cpf = ?, 
                cep = ?, rua = ?, bairro = ?, cidade = ?, estado = ?
            WHERE id = ?
        ''', (nome, telefone, email, cpf, cep, rua, bairro, cidade, estado, id))
        conexao.commit()
        return True, "Cliente atualizado com sucesso."
    except IntegrityError as e:
        if "UNIQUE constraint failed: clientes.cpf" in str(e) or "duplicate key" in str(e).lower():
            return False, "Erro: CPF já cadastrado para outro cliente."
        else:
            return False, f"Erro ao atualizar cliente: {e}"
    except DatabaseError as e:
        return False, f"Erro ao atualizar cliente: {e}"
    finally:
        conexao.close()


def excluir_cliente(id):
    """Exclui um cliente pelo ID."""
    conexao = conectar()
    cursor = conexao.cursor()
    try:
        cursor.execute('DELETE FROM clientes WHERE id = ?', (id,))
        conexao.commit()
        return True, "Cliente excluído com sucesso."
    except DatabaseError as e:
        return False, f"Erro ao excluir cliente: {e}"
    finally:
        conexao.close()
