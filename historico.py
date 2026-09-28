from db import conectar, DatabaseError
from datetime import datetime, timezone, timedelta

BRT = timezone(timedelta(hours=-3))


def registrar_acao(usuario_nome, usuario_login, acao, detalhes):
    """Registra uma ação no histórico do sistema."""
    conexao = conectar()
    if conexao is None:
        print("Erro: não foi possível registrar ação no histórico (sem conexão).")
        return

    cursor = conexao.cursor()
    try:
        agora = datetime.now(tz=BRT).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO historico (data_hora, usuario_nome, usuario_login, acao, detalhes)
            VALUES (?, ?, ?, ?, ?)
        ''', (agora, usuario_nome, usuario_login, acao, detalhes))
        conexao.commit()
    except DatabaseError as e:
        print(f"Erro ao registrar ação no histórico: {e}")
    finally:
        conexao.close()


def listar_historico(filtro=None, limite=100):
    """Lista os registros do histórico, opcionalmente filtrados."""
    conexao = conectar()
    if conexao is None:
        return []

    cursor = conexao.cursor()
    try:
        query = '''
            SELECT id, data_hora, usuario_nome, usuario_login, acao, detalhes
            FROM historico
        '''
        params = []

        if filtro:
            like = f'%{filtro}%'
            query += ' WHERE usuario_nome LIKE ? OR usuario_login LIKE ? OR acao LIKE ? OR detalhes LIKE ?'
            params = [like, like, like, like]

        query += ' ORDER BY id DESC'

        if limite:
            query += ' LIMIT ?'
            params.append(limite)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Formata a data/hora para exibição
        resultado = []
        for row in rows:
            row_list = list(row)
            try:
                dt_obj = datetime.strptime(str(row_list[1]), '%Y-%m-%d %H:%M:%S')
                row_list[1] = dt_obj.strftime('%d/%m/%Y %H:%M:%S')
            except ValueError:
                try:
                    dt_obj = datetime.strptime(str(row_list[1]), '%Y-%m-%d %H:%M')
                    row_list[1] = dt_obj.strftime('%d/%m/%Y %H:%M')
                except ValueError:
                    pass
            resultado.append(tuple(row_list))
        return resultado
    except DatabaseError as e:
        print(f"Erro ao listar histórico: {e}")
        return []
    finally:
        conexao.close()
