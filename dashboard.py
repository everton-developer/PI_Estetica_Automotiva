from db import conectar, DatabaseError
from datetime import datetime, timedelta, timezone

BRT = timezone(timedelta(hours=-3))


def _consultar(query, params=None):
    conexao = conectar()
    if not conexao: return []
    cursor = conexao.cursor()
    try:
        cursor.execute(query, params or [])
        return cursor.fetchall()
    except DatabaseError as e:
        print(f"Erro no dashboard: {e}")
        return []
    finally:
        conexao.close()


def _fmt_br(data_iso):
    """'2025-01-15' -> '15/01/2025'"""
    if not data_iso: return ''
    try:
        p = data_iso.split('-')
        return f"{p[2]}/{p[1]}/{p[0]}"
    except Exception:
        return data_iso


def calcular_periodo(periodo, data_inicio_raw=None, data_fim_raw=None):
    """Retorna (data_inicio_iso, data_fim_iso, periodo) com base no filtro escolhido."""
    hoje = datetime.now(BRT)

    if periodo == 'hoje':
        d_ini = d_fim = hoje.strftime('%Y-%m-%d')
    elif periodo == '7d':
        d_ini = (hoje - timedelta(days=6)).strftime('%Y-%m-%d')
        d_fim = hoje.strftime('%Y-%m-%d')
    elif periodo == 'mes':
        d_ini = hoje.replace(day=1).strftime('%Y-%m-%d')
        d_fim = hoje.strftime('%Y-%m-%d')
    elif periodo == 'ultimo_mes':
        prim_dia_mes = hoje.replace(day=1)
        ult_dia_ant = prim_dia_mes - timedelta(days=1)
        d_ini = ult_dia_ant.replace(day=1).strftime('%Y-%m-%d')
        d_fim = ult_dia_ant.strftime('%Y-%m-%d')
    elif periodo == 'custom':
        d_ini = data_inicio_raw or hoje.strftime('%Y-%m-%d')
        d_fim = data_fim_raw or hoje.strftime('%Y-%m-%d')
        # Garante ordem correta
        if d_ini > d_fim:
            d_ini, d_fim = d_fim, d_ini
    else:
        d_ini = (hoje - timedelta(days=6)).strftime('%Y-%m-%d')
        d_fim = hoje.strftime('%Y-%m-%d')
        periodo = '7d'

    return d_ini, d_fim, periodo


def obter_dados_dashboard(data_inicio, data_fim, status_filtro='Todos'):
    # Para pegar o dia inteiro, comparamos com data_fim + 1 dia
    data_fim_inclusivo = (datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

    # ===== RESUMO COMPLETO POR STATUS NO PERÍODO (Sempre disponível) =====
    status_raw = _consultar("""
        SELECT status,
               COUNT(*),
               COALESCE(SUM(valor_total), 0)
        FROM orcamentos
        WHERE data_atualizacao >= ? AND data_atualizacao < ?
        GROUP BY status
    """, [data_inicio, data_fim_inclusivo])

    resumo_status = {
        'Pendente': {'qtd': 0, 'valor': 0.0},
        'Aprovado': {'qtd': 0, 'valor': 0.0},
        'Concluído': {'qtd': 0, 'valor': 0.0},
        'Recusado': {'qtd': 0, 'valor': 0.0}
    }
    total_geral_orcamentos = 0
    total_geral_valor = 0.0

    for st, qtd, val in status_raw:
        if st in resumo_status:
            resumo_status[st] = {'qtd': int(qtd), 'valor': float(val)}
        total_geral_orcamentos += int(qtd)
        total_geral_valor += float(val)

    # ===== KPIs CONDICIONADOS AO STATUS_FILTRO =====
    params_kpi = [data_inicio, data_fim_inclusivo]
    where_status_kpi = ""
    label_faturamento = "Faturamento (Aprovados + Concluídos)"

    if status_filtro == 'Todos':
        # No geral, o faturamento efetivo reflete orçamentos fechados (Aprovados e Concluídos),
        # mas o total de orçamentos e clientes reflete TODOS os status.
        where_status_kpi = "AND status IN ('Aprovado', 'Concluído')"
        
        # Consulta faturamento efetivo
        kpi_fat = _consultar(f"""
            SELECT COALESCE(SUM(valor_total), 0),
                   COALESCE(AVG(valor_total), 0)
            FROM orcamentos
            WHERE data_atualizacao >= ? AND data_atualizacao < ?
              {where_status_kpi}
        """, params_kpi)
        faturamento_valor = float(kpi_fat[0][0]) if kpi_fat else 0.0
        ticket_medio = float(kpi_fat[0][1]) if kpi_fat else 0.0

        # Total de orçamentos de todos os status
        total_orcamentos = total_geral_orcamentos

        # Clientes atendidos de todos os status
        novos = _consultar("""
            SELECT COUNT(DISTINCT cliente_id) FROM orcamentos
            WHERE data_atualizacao >= ? AND data_atualizacao < ?
        """, [data_inicio, data_fim_inclusivo])
        novos_clientes = int(novos[0][0]) if novos else 0

        # Para serviços e tipos no modo 'Todos', considera todos os orçamentos do período
        filtro_servicos_status = ""
        params_servicos = [data_inicio, data_fim_inclusivo]
    else:
        # Filtrado por um status específico (Pendente, Aprovado, Concluído ou Recusado)
        label_faturamento = f"Valor Total ({status_filtro})"
        where_status = "AND o.status = ?"
        
        kpi = _consultar("""
            SELECT COALESCE(SUM(valor_total), 0),
                   COUNT(id),
                   COALESCE(AVG(valor_total), 0)
            FROM orcamentos
            WHERE status = ?
              AND data_atualizacao >= ? AND data_atualizacao < ?
        """, [status_filtro, data_inicio, data_fim_inclusivo])
        kpi = kpi[0] if kpi else (0, 0, 0)
        
        faturamento_valor = float(kpi[0])
        total_orcamentos = int(kpi[1])
        ticket_medio = float(kpi[2])

        novos = _consultar("""
            SELECT COUNT(DISTINCT cliente_id) FROM orcamentos
            WHERE status = ?
              AND data_atualizacao >= ? AND data_atualizacao < ?
        """, [status_filtro, data_inicio, data_fim_inclusivo])
        novos_clientes = int(novos[0][0]) if novos else 0

        filtro_servicos_status = "AND o.status = ?"
        params_servicos = [data_inicio, data_fim_inclusivo, status_filtro]

    # ===== SERVIÇOS MAIS REALIZADOS NO PERÍODO =====
    # Usa COALESCE(servico_nome, descricao_personalizada, 'Personalizado') para pegar o nome real
    servicos_raw = _consultar(f"""
        SELECT COALESCE(NULLIF(oi.servico_nome, ''), NULLIF(oi.descricao_personalizada, ''), 'Personalizado') AS nome,
               COUNT(*) AS qtd
        FROM orcamento_itens oi
        JOIN orcamentos o ON oi.orcamento_id = o.id
        WHERE o.data_atualizacao >= ? AND o.data_atualizacao < ?
          {filtro_servicos_status}
        GROUP BY COALESCE(NULLIF(oi.servico_nome, ''), NULLIF(oi.descricao_personalizada, ''), 'Personalizado')
        ORDER BY qtd DESC
        LIMIT 6
    """, params_servicos)
    max_s = max([s[1] for s in servicos_raw]) if servicos_raw else 1
    servicos = [{'nome': s[0], 'qtd': s[1], 'porcentagem': (s[1] / max_s) * 100} for s in servicos_raw]

    # ===== PARTICULAR X SEGURO =====
    tipos_raw = _consultar(f"""
        SELECT COALESCE(oi.servico_tipo, 'Particular') AS tipo,
               COUNT(*) AS qtd,
               COALESCE(SUM(oi.valor_unitario), 0) AS total
        FROM orcamento_itens oi
        JOIN orcamentos o ON oi.orcamento_id = o.id
        WHERE o.data_atualizacao >= ? AND o.data_atualizacao < ?
          {filtro_servicos_status}
        GROUP BY COALESCE(oi.servico_tipo, 'Particular')
    """, params_servicos)
    total_t = sum([t[1] for t in tipos_raw]) or 1
    tipos = [{'nome': t[0], 'qtd': t[1], 'valor': float(t[2]),
              'porcentagem': (t[1] / total_t) * 100} for t in tipos_raw]
    particular = next((t for t in tipos if t['nome'] == 'Particular'), {'valor': 0})

    # ===== FATURAMENTO MENSAL (ÚLTIMOS 12 MESES) =====
    if status_filtro == 'Todos':
        status_mensal_sql = "WHERE status IN ('Aprovado', 'Concluído')"
        params_mensal = []
    else:
        status_mensal_sql = "WHERE status = ?"
        params_mensal = [status_filtro]

    mensal_raw = _consultar(f"""
        SELECT SUBSTR(data_atualizacao, 1, 7) AS mes,
               COALESCE(SUM(valor_total), 0) AS total
        FROM orcamentos
        {status_mensal_sql}
        GROUP BY mes
        ORDER BY mes DESC
        LIMIT 12
    """, params_mensal)
    mensal_raw = list(reversed(mensal_raw))

    meses_pt = {'01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr',
                '05': 'Mai', '06': 'Jun', '07': 'Jul', '08': 'Ago',
                '09': 'Set', '10': 'Out', '11': 'Nov', '12': 'Dez'}
    max_f = max([float(f[1]) for f in mensal_raw]) if mensal_raw else 1
    faturamento = []
    for f in mensal_raw:
        mes_num = f[0][5:7] if f[0] else '01'
        faturamento.append({
            'mes': meses_pt.get(mes_num, mes_num),
            'valor': float(f[1]),
            'altura': (float(f[1]) / max_f) * 100
        })

    return {
        'faturamento_total': faturamento_valor,
        'label_faturamento': label_faturamento,
        'total_orcamentos': total_orcamentos,
        'total_geral_orcamentos': total_geral_orcamentos,
        'total_geral_valor': total_geral_valor,
        'ticket_medio': ticket_medio,
        'novos_clientes': novos_clientes,
        'resumo_status': resumo_status,
        'servicos': servicos,
        'tipos': tipos,
        'particular_valor': float(particular['valor']),
        'faturamento_mensal': faturamento,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'data_inicio_fmt': _fmt_br(data_inicio),
        'data_fim_fmt': _fmt_br(data_fim),
        'status_filtro': status_filtro,
    }
