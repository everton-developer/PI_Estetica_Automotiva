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
    """Retorna (data_inicio_iso, data_fim_iso) com base no filtro escolhido."""
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


def obter_dados_dashboard(data_inicio, data_fim):
    # Para pegar o dia inteiro, comparamos com data_fim + 1 dia
    data_fim_inclusivo = (datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

    # ===== KPIs do período =====
    kpi = _consultar("""
        SELECT COALESCE(SUM(valor_total), 0),
               COUNT(id),
               COALESCE(AVG(valor_total), 0)
        FROM orcamentos
        WHERE status IN ('Aprovado', 'Concluído')
          AND data_atualizacao >= ? AND data_atualizacao < ?
    """, [data_inicio, data_fim_inclusivo])
    kpi = kpi[0] if kpi else (0, 0, 0)

    # ===== Clientes atendidos no período (proxy de "novos clientes") =====
    novos = _consultar("""
        SELECT COUNT(DISTINCT cliente_id) FROM orcamentos
        WHERE data_atualizacao >= ? AND data_atualizacao < ?
    """, [data_inicio, data_fim_inclusivo])
    novos_clientes = int(novos[0][0]) if novos else 0

    # ===== Serviços mais realizados no período =====
    servicos_raw = _consultar("""
        SELECT COALESCE(oi.servico_nome, 'Personalizado') AS nome,
               COUNT(*) AS qtd
        FROM orcamento_itens oi
        JOIN orcamentos o ON oi.orcamento_id = o.id
        WHERE o.data_atualizacao >= ? AND o.data_atualizacao < ?
        GROUP BY COALESCE(oi.servico_nome, 'Personalizado')
        ORDER BY qtd DESC
        LIMIT 5
    """, [data_inicio, data_fim_inclusivo])
    max_s = max([s[1] for s in servicos_raw]) if servicos_raw else 1
    servicos = [{'nome': s[0], 'qtd': s[1], 'porcentagem': (s[1] / max_s) * 100} for s in servicos_raw]

    # ===== Particular x Seguro =====
    tipos_raw = _consultar("""
        SELECT COALESCE(oi.servico_tipo, 'Particular') AS tipo,
               COUNT(*) AS qtd,
               COALESCE(SUM(oi.valor_unitario), 0) AS total
        FROM orcamento_itens oi
        JOIN orcamentos o ON oi.orcamento_id = o.id
        WHERE o.data_atualizacao >= ? AND o.data_atualizacao < ?
        GROUP BY COALESCE(oi.servico_tipo, 'Particular')
    """, [data_inicio, data_fim_inclusivo])
    total_t = sum([t[1] for t in tipos_raw]) or 1
    tipos = [{'nome': t[0], 'qtd': t[1], 'valor': float(t[2]),
              'porcentagem': (t[1] / total_t) * 100} for t in tipos_raw]
    particular = next((t for t in tipos if t['nome'] == 'Particular'), {'valor': 0})

    # ===== Faturamento mensal (últimos 12 meses, independe do filtro) =====
    mensal_raw = _consultar("""
        SELECT SUBSTR(data_atualizacao, 1, 7) AS mes,
               COALESCE(SUM(valor_total), 0) AS total
        FROM orcamentos
        WHERE status IN ('Aprovado', 'Concluído')
        GROUP BY mes
        ORDER BY mes DESC
        LIMIT 12
    """)
    mensal_raw = list(reversed(mensal_raw))  # ordem cronológica

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
        'faturamento_total': float(kpi[0]),
        'total_orcamentos': int(kpi[1]),
        'ticket_medio': float(kpi[2]),
        'novos_clientes': novos_clientes,
        'servicos': servicos,
        'tipos': tipos,
        'particular_valor': float(particular['valor']),
        'faturamento_mensal': faturamento,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'data_inicio_fmt': _fmt_br(data_inicio),
        'data_fim_fmt': _fmt_br(data_fim),
    }
