from db import conectar, DatabaseError, IntegrityError
import bcrypt


def hash_senha(senha):
    """Gera o hash bcrypt de uma senha."""
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verificar_senha(senha, senha_hash):
    """Verifica se a senha corresponde ao hash."""
    return bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))


def autenticar_usuario(login, senha):
    """Autentica um usuário pelo login e senha. Retorna dados do usuário ou None."""
    conexao = conectar()
    if conexao is None:
        return None

    cursor = conexao.cursor()
    try:
        cursor.execute('SELECT id, nome, login, senha, email, tipo FROM usuarios WHERE login = ?', (login,))
        usuario = cursor.fetchone()
        if usuario and verificar_senha(senha, usuario[3]):
            # Retorna sem a senha
            return {
                'id': usuario[0],
                'nome': usuario[1],
                'login': usuario[2],
                'email': usuario[4],
                'tipo': usuario[5]
            }
        return None
    except DatabaseError as e:
        print(f"Erro ao autenticar usuário: {e}")
        return None
    finally:
        conexao.close()


def cadastrar_usuario(nome, login, senha, email):
    """Cadastra um novo usuário comum no sistema."""
    conexao = conectar()
    if conexao is None:
        return False, "Erro de conexão com o banco de dados."

    cursor = conexao.cursor()
    try:
        # Verifica se login já existe
        cursor.execute('SELECT id FROM usuarios WHERE login = ?', (login,))
        if cursor.fetchone():
            return False, "Erro: Login já cadastrado."

        # Verifica se email já existe
        cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
        if cursor.fetchone():
            return False, "Erro: E-mail já cadastrado."

        senha_hash = hash_senha(senha)
        cursor.execute('''
            INSERT INTO usuarios (nome, login, senha, email, tipo)
            VALUES (?, ?, ?, ?, 'comum')
        ''', (nome, login, senha_hash, email))
        conexao.commit()
        return True, "Usuário cadastrado com sucesso."
    except IntegrityError as e:
        if "login" in str(e).lower() or "duplicate key" in str(e).lower():
            return False, "Erro: Login já cadastrado."
        return False, f"Erro ao cadastrar usuário: {e}"
    except DatabaseError as e:
        return False, f"Erro ao cadastrar usuário: {e}"
    finally:
        conexao.close()


def listar_usuarios():
    """Lista todos os usuários (exceto senhas)."""
    conexao = conectar()
    if conexao is None:
        return []

    cursor = conexao.cursor()
    try:
        cursor.execute('SELECT id, nome, login, email, tipo FROM usuarios ORDER BY nome')
        return cursor.fetchall()
    except DatabaseError as e:
        print(f"Erro ao listar usuários: {e}")
        return []
    finally:
        conexao.close()


def buscar_usuario_por_id(id_usuario):
    """Busca um único usuário pelo ID (sem senha)."""
    conexao = conectar()
    if conexao is None:
        return None

    cursor = conexao.cursor()
    try:
        cursor.execute('SELECT id, nome, login, email, tipo FROM usuarios WHERE id = ?', (id_usuario,))
        return cursor.fetchone()
    except DatabaseError as e:
        print(f"Erro ao buscar usuário: {e}")
        return None
    finally:
        conexao.close()


def atualizar_usuario(id_usuario, nome, login, email, senha=None):
    """Atualiza os dados de um usuário existente. Não permite alterar o ADM."""
    conexao = conectar()
    if conexao is None:
        return False, "Erro de conexão com o banco de dados."

    cursor = conexao.cursor()
    try:
        # Verifica se o usuário existe e não é ADM
        cursor.execute('SELECT tipo FROM usuarios WHERE id = ?', (id_usuario,))
        usuario = cursor.fetchone()
        if not usuario:
            return False, "Usuário não encontrado."
        if usuario[0] == 'adm':
            return False, "Erro: O usuário administrador não pode ser modificado pela interface."

        # Verifica se login já existe para outro usuário
        cursor.execute('SELECT id FROM usuarios WHERE login = ? AND id != ?', (login, id_usuario))
        if cursor.fetchone():
            return False, "Erro: Login já cadastrado para outro usuário."

        # Verifica se email já existe para outro usuário
        cursor.execute('SELECT id FROM usuarios WHERE email = ? AND id != ?', (email, id_usuario))
        if cursor.fetchone():
            return False, "Erro: E-mail já cadastrado para outro usuário."

        if senha:
            senha_hash = hash_senha(senha)
            cursor.execute('''
                UPDATE usuarios SET nome = ?, login = ?, senha = ?, email = ? WHERE id = ?
            ''', (nome, login, senha_hash, email, id_usuario))
        else:
            cursor.execute('''
                UPDATE usuarios SET nome = ?, login = ?, email = ? WHERE id = ?
            ''', (nome, login, email, id_usuario))

        conexao.commit()
        return True, "Usuário atualizado com sucesso."
    except IntegrityError as e:
        if "login" in str(e).lower() or "duplicate key" in str(e).lower():
            return False, "Erro: Login já cadastrado para outro usuário."
        return False, f"Erro ao atualizar usuário: {e}"
    except DatabaseError as e:
        return False, f"Erro ao atualizar usuário: {e}"
    finally:
        conexao.close()


def excluir_usuario(id_usuario):
    """Exclui um usuário. Não permite excluir o ADM."""
    conexao = conectar()
    if conexao is None:
        return False, "Erro de conexão com o banco de dados."

    cursor = conexao.cursor()
    try:
        # Verifica se não é o ADM
        cursor.execute('SELECT tipo FROM usuarios WHERE id = ?', (id_usuario,))
        usuario = cursor.fetchone()
        if not usuario:
            return False, "Usuário não encontrado."
        if usuario[0] == 'adm':
            return False, "Erro: O usuário administrador não pode ser excluído pela interface."

        cursor.execute('DELETE FROM usuarios WHERE id = ?', (id_usuario,))
        conexao.commit()
        return True, "Usuário excluído com sucesso."
    except DatabaseError as e:
        return False, f"Erro ao excluir usuário: {e}"
    finally:
        conexao.close()
