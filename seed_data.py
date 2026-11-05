"""
Gera dados fictícios para testar o dashboard.
⚠️ APAGA TODOS OS DADOS (exceto usuários). Use só na branch de teste!
"""
import random
from datetime import datetime, timedelta, timezone
from db import conectar
from orcamento import gerar_codigo_orcamento

BRT = timezone(timedelta(hours=-3))

NOMES = [
    "Carlos Oliveira", "Ana Costa", "José Pereira", "Maria Silva",
    "Pedro Santos", "Camila Rocha", "Marcos Ribeiro", "Juliana Lima",
    "Ricardo Alves", "Fernanda Souza", "Lucas Martins", "Beatriz Ferreira",
    "Rafael Cardoso", "Patrícia Gomes", "Thiago Barbosa", "Aline Araújo",
]

VEICULOS = [
    ("Toyota", "Corolla", "2020", "Prata"), ("Hyundai", "HB20", "2021", "Branco"),
    ("Volkswagen", "Jetta", "2019", "Preto"), ("Jeep", "Compass", "2022", "Cinza"),
    ("Honda", "Civic", "2020", "Azul"), ("Chevrolet", "Onix", "2023", "Vermelho"),
    ("Fiat", "Toro", "2021", "Prata"), ("Renault", "Kwid", "2022", "Branco"),
    ("Nissan", "Kicks", "2020", "Cinza"), ("Ford", "Ka", "2019", "Azul"),
    ("Toyota", "Hilux", "2022", "Preto"), ("Hyundai", "Creta", "2023", "Vermelho"),
]

SERVICOS = [
    ("Reparo de porta", "Martelinho na porta", 450.00, "Particular"),
    ("Reparo de capô", "Martelinho no capô", 550.00, "Particular"),
    ("Reparo de porta-malas", "Reparo do porta-malas", 400.00, "Particular"),
    ("Reparo de paralama", "Martelinho no paralama", 380.00, "Particular"),
    ("Reparo de teto", "Reparo de amassado no teto", 600.00, "Particular"),
    ("Reparo de porta (Seguro)", "Porta via seguro", 450.00, "Seguro"),
    ("Reparo de capô (Seguro)", "Capô via seguro", 550.00, "Seguro"),
    ("Reparo de paralama (Seguro)", "Paralama via seguro", 380.00, "Seguro"),
    ("Polimento técnico", "Polimento completo", 280.00, "Particular"),
    ("Cristalização", "Cristalização de pintura", 350.00, "Particular"),
]

OBSERVACOES = ["", "Cliente pediu urgência.", "Aguardando aprovação do seguro.",
               "Serviço agendado para próxima semana.", "Serviço concluído no prazo."]


def seed():
    print("=" * 55)
    print("  ⚠️  GERADOR DE DADOS FICTÍCIOS PARA O DASHBOARD")
    print("=" * 55)
    print("  Este script APAGA todos os dados (exceto usuários)!")
    print("  Rode APENAS na branch de teste do Neon.")
    print("=" * 55)
    resposta = input("\nDigite 'SIM' para continuar: ")
    if resposta.strip().upper() != 'SIM':
        print("Cancelado.")
        return

    conexao = conectar()
    if not conexao:
        print("❌ Erro ao conectar.")
        return
    cursor = conexao.cursor()

    try:
        # Limpa tudo
        print("\n🧹 Limpando dados antigos...")
        for t in ['orcamento_itens', 'orcamentos', 'veiculos', 'servicos', 'clientes']:
            cursor.execute(f"DELETE FROM {t}")
        conexao.commit()
        print("✓ Limpeza concluída.\n")

        # ===== CLIENTES =====
        print("👥 Criando clientes...")
        clientes_ids = []
        for nome in NOMES:
            cursor.execute("""
                INSERT INTO clientes (nome, telefone, email, cpf, cep, rua, numero, complemento, bairro, cidade, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nome, f"11{random.randint(900000000, 999999999)}",
                  f"{nome.lower().replace(' ', '.')}@email.com", None, "01000000",
                  "Rua das Flores", str(random.randint(10, 999)), "", "Centro", "São Paulo", "SP"))
            clientes_ids.append(cursor.lastrowid)
        conexao.commit()
        print(f"✓ {len(clientes_ids)} clientes.\n")

        # ===== VEÍCULOS =====
        print("🚗 Criando veículos...")
        veiculos_ids = []
        for i, (marca, modelo, ano, cor) in enumerate(VEICULOS):
            placa = f"{random.choice('ABCDEFG')}{random.choice('ABCDEFG')}{random.choice('ABCDEFG')}{random.randint(1000, 9999)}"
            cursor.execute("""
                INSERT INTO veiculos (marca, modelo, ano, cor, placa, cliente_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (marca, modelo, ano, cor, placa, clientes_ids[i % len(clientes_ids)]))
            veiculos_ids.append(cursor.lastrowid)
        conexao.commit()
        print(f"✓ {len(veiculos_ids)} veículos.\n")

        # ===== SERVIÇOS =====
        print("🔧 Criando serviços...")
        servicos_map = {}
        for nome, desc, valor, tipo in SERVICOS:
            cursor.execute("""
                INSERT INTO servicos (nome, descricao, valor, tipo) VALUES (?, ?, ?, ?)
            """, (nome, desc, valor, tipo))
            servicos_map[nome] = (cursor.lastrowid, valor, tipo)
        conexao.commit()
        print(f"✓ {len(servicos_map)} serviços.\n")

        # ===== ORÇAMENTOS (distribuídos nos últimos 12 meses) =====
        print("📋 Criando 100 orçamentos espalhados nos últimos 12 meses...")
        hoje = datetime.now(BRT)
        total_orc = 0

        for _ in range(100):
            # triangular: concentra mais em ~25 dias atrás, espalha até 350 dias
            dias_atras = int(random.triangular(0, 350, 25))
            data_orc = hoje - timedelta(days=dias_atras, hours=random.randint(0, 10))
            data_str = data_orc.strftime('%Y-%m-%d %H:%M')

            cli_id = random.choice(clientes_ids)
            vei_id = random.choice(veiculos_ids)

            cursor.execute("SELECT nome, telefone, cpf FROM clientes WHERE id = ?", (cli_id,))
            cli = cursor.fetchone()
            cursor.execute("SELECT placa, marca, modelo, ano, cor FROM veiculos WHERE id = ?", (vei_id,))
            vei = cursor.fetchone()

            # Status realista
            status = random.choices(
                ['Concluído', 'Aprovado', 'Pendente', 'Recusado'],
                weights=[45, 25, 20, 10]
            )[0]

            codigo = gerar_codigo_orcamento()

            cursor.execute("""
                INSERT INTO orcamentos (
                    cliente_id, veiculo_id, cliente_nome, cliente_telefone, cliente_cpf,
                    veiculo_placa, veiculo_marca, veiculo_modelo, veiculo_ano, veiculo_cor,
                    data_criacao, data_atualizacao, status, observacoes, valor_total, codigo_orcamento
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?)
            """, (cli_id, vei_id, cli[0], cli[1], cli[2], vei[0], vei[1], vei[2], vei[3], vei[4],
                  data_str, data_str, status, random.choice(OBSERVACOES), codigo))
            orc_id = cursor.lastrowid

            # 1 a 3 itens por orçamento
            num_itens = random.randint(1, 3)
            nomes_escolhidos = random.sample(list(servicos_map.keys()), num_itens)
            valor_total = 0

            for nome_srv in nomes_escolhidos:
                srv_id, srv_valor, srv_tipo = servicos_map[nome_srv]
                valor_final = round(srv_valor * random.uniform(0.9, 1.1), 2)
                valor_total += valor_final
                cursor.execute("""
                    INSERT INTO orcamento_itens (
                        orcamento_id, servico_id, servico_nome, servico_tipo,
                        descricao_personalizada, valor_unitario
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (orc_id, srv_id, nome_srv, srv_tipo, "", valor_final))

            cursor.execute("UPDATE orcamentos SET valor_total = ? WHERE id = ?", (valor_total, orc_id))
            total_orc += 1

        conexao.commit()
        print(f"✓ {total_orc} orçamentos criados.\n")

        # ===== RESUMO =====
        print("=" * 55)
        print("  ✅ BANCO POPULADO COM SUCESSO!")
        print("=" * 55)
        for tabela in ['clientes', 'veiculos', 'servicos', 'orcamentos', 'orcamento_itens']:
            cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
            print(f"  {tabela:>20}: {cursor.fetchone()[0]}")
        print("=" * 55)
        print("\n➡️  Agora vá em http://127.0.0.1:5000/dashboard e teste os filtros!")

    except Exception as e:
        conexao.rollback()
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conexao.close()


if __name__ == '__main__':
    seed()