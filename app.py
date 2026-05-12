from flask import Flask, request, redirect, render_template, Blueprint, flash, jsonify, session

import cliente
import servico
import veiculo
import orcamento
from db import criar_tabelas, conectar, DatabaseError

app = Flask(__name__)
app.secret_key = 'l_brothers_sistema_2025'

# Cria as tabelas no início
criar_tabelas()

# ==================== FILTROS JINJA ====================
def format_cpf(cpf):
    if not cpf or len(cpf) != 11: return cpf
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

def format_telefone(telefone):
    if not telefone: return telefone
    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    elif len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    return telefone

def format_cep(cep):
    if not cep or len(cep) != 8: return cep
    return f"{cep[:5]}-{cep[5:]}"

app.jinja_env.filters['format_cpf'] = format_cpf
app.jinja_env.filters['format_telefone'] = format_telefone
app.jinja_env.filters['format_cep'] = format_cep


# ==================== PÁGINA INICIAL ====================
index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def home():
    # Dados para o dashboard
    conexao = conectar()
    if not conexao:
        return "Erro ao conectar ao banco de dados.", 500
        
    cursor = conexao.cursor()
    try:
        cursor.execute('SELECT COUNT(*) FROM clientes')
        total_clientes = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM veiculos')
        total_veiculos = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM servicos')
        total_servicos = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM orcamentos')
        total_orcamentos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orcamentos WHERE status = 'Pendente'")
        orcamentos_pendentes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orcamentos WHERE status = 'Aprovado'")
        orcamentos_aprovados = cursor.fetchone()[0]
    except DatabaseError as e:
        print(f"Erro no dashboard: {e}")
        total_clientes = total_veiculos = total_servicos = total_orcamentos = 0
        orcamentos_pendentes = orcamentos_aprovados = 0
    finally:
        conexao.close()

    return render_template('index.html',
                           total_clientes=total_clientes,
                           total_veiculos=total_veiculos,
                           total_servicos=total_servicos,
                           total_orcamentos=total_orcamentos,
                           orcamentos_pendentes=orcamentos_pendentes,
                           orcamentos_aprovados=orcamentos_aprovados)


# ==================== CLIENTES ====================
clientes_bp = Blueprint('clientes', __name__)


@clientes_bp.route('/clientes', methods=['GET'])
def clientes_page():
    termo_busca = request.args.get('busca', '').strip()
    clientes_list = cliente.listar_clientes(termo_busca)
    return render_template('clientes.html', clientes=clientes_list, busca=termo_busca)


@clientes_bp.route('/clientes/cadastrar', methods=['POST'])
def cadastrar_cliente_route():
    nome = request.form['nome']
    telefone = request.form['telefone']
    email = request.form['email']
    cpf = request.form['cpf']
    cep = request.form.get('cep', '')
    rua = request.form.get('rua', '')
    numero = request.form.get('numero', '')
    complemento = request.form.get('complemento', '')
    bairro = request.form.get('bairro', '')
    cidade = request.form.get('cidade', '')
    estado = request.form.get('estado', '')

    sucesso, mensagem = cliente.cadastrar_cliente(nome, telefone, email, cpf, cep, rua, numero, complemento, bairro, cidade, estado)
    flash(mensagem, "success" if sucesso else "error")
    return redirect('/clientes')


@clientes_bp.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
def editar_cliente_route(id):
    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']
        email = request.form['email']
        cpf = request.form['cpf']
        cep = request.form.get('cep', '')
        rua = request.form.get('rua', '')
        numero = request.form.get('numero', '')
        complemento = request.form.get('complemento', '')
        bairro = request.form.get('bairro', '')
        cidade = request.form.get('cidade', '')
        estado = request.form.get('estado', '')

        sucesso, mensagem = cliente.atualizar_cliente(id, nome, telefone, email, cpf, cep, rua, numero, complemento, bairro, cidade, estado)
        flash(mensagem, "success" if sucesso else "error")
        return redirect('/clientes')
    else:
        cliente_editar = cliente.buscar_cliente_por_id(id)
        if cliente_editar is None:
            flash("Cliente não encontrado.", "error")
            return redirect('/clientes')
        clientes_list = cliente.listar_clientes()
        return render_template('clientes.html', clientes=clientes_list, cliente_editar=cliente_editar)


@clientes_bp.route('/clientes/excluir/<int:id>', methods=['POST'])
def excluir_cliente_route(id):
    sucesso, mensagem = cliente.excluir_cliente(id)
    flash(mensagem, "success" if sucesso else "error")
    return redirect('/clientes')


# ==================== VEÍCULOS ====================
veiculos_bp = Blueprint('veiculos', __name__)


@veiculos_bp.route('/veiculos', methods=['GET'])
def veiculos_page():
    termo_busca = request.args.get('busca', '').strip()
    veiculos_list = veiculo.listar_veiculos(termo_busca)
    clientes_list = cliente.listar_clientes()
    return render_template('veiculos.html', veiculos=veiculos_list, clientes=clientes_list, busca=termo_busca)


@veiculos_bp.route('/veiculos/cadastrar', methods=['POST'])
def cadastrar_veiculo_route():
    marca = request.form.get('marca')
    modelo = request.form.get('modelo')
    ano = request.form.get('ano', '')
    cor = request.form.get('cor', '')
    placa = request.form.get('placa')
    cliente_id = request.form.get('cliente_id')

    if not all([marca, modelo, placa, cliente_id]):
        flash("Marca, modelo, placa e cliente são obrigatórios.", "error")
        return redirect('/veiculos')

    try:
        cliente_id = int(cliente_id)
        sucesso, mensagem = veiculo.cadastrar_veiculo(marca, modelo, ano, cor, placa, cliente_id)
        flash(mensagem, "success" if sucesso else "error")
    except ValueError:
        flash("ID do cliente inválido.", "error")

    return redirect('/veiculos')


@veiculos_bp.route('/veiculos/editar/<int:id>', methods=['GET', 'POST'])
def editar_veiculo_route(id):
    if request.method == 'POST':
        marca = request.form['marca']
        modelo = request.form['modelo']
        ano = request.form.get('ano', '')
        cor = request.form.get('cor', '')
        placa = request.form['placa']
        cliente_id = request.form['cliente_id']

        sucesso, mensagem = veiculo.editar_veiculo(id, marca, modelo, ano, cor, placa, cliente_id)
        flash(mensagem, "success" if sucesso else "error")
        return redirect('/veiculos')
    else:
        veiculo_editar = veiculo.buscar_veiculo_por_id(id)
        if veiculo_editar is None:
            flash("Veículo não encontrado.", "error")
            return redirect('/veiculos')
        veiculos_list = veiculo.listar_veiculos()
        clientes_list = cliente.listar_clientes()
        return render_template('veiculos.html', veiculos=veiculos_list, clientes=clientes_list,
                               veiculo_editar=veiculo_editar)


@veiculos_bp.route('/veiculos/excluir/<int:id>', methods=['POST'])
def excluir_veiculo_route(id):
    sucesso, mensagem = veiculo.excluir_veiculo(id)
    flash(mensagem, "success" if sucesso else "error")
    return redirect('/veiculos')


# ==================== SERVIÇOS ====================
servicos_bp = Blueprint('servicos', __name__)


@servicos_bp.route('/servicos', methods=['GET'])
def servicos_page():
    termo_busca = request.args.get('busca', '').strip()
    servicos_list = servico.listar_servicos(termo_busca)
    return render_template('servicos.html', servicos=servicos_list, busca=termo_busca)


@servicos_bp.route('/servicos/cadastrar', methods=['POST'])
def cadastrar_servico_route():
    nome = request.form['nome']
    descricao = request.form['descricao']
    valor = request.form['valor']
    tipo = request.form.get('tipo', 'Particular')

    if not all([nome, valor]):
        flash("Nome e valor são obrigatórios.", "error")
        return redirect('/servicos')

    try:
        valor = float(valor)
        sucesso, mensagem = servico.cadastrar_servico(nome, descricao, valor, tipo)
        flash(mensagem, "success" if sucesso else "error")
    except ValueError:
        flash("Valor inválido. Use um número.", "error")

    return redirect('/servicos')


@servicos_bp.route('/servicos/editar/<int:id>', methods=['GET', 'POST'])
def editar_servico_route(id):
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        valor = request.form['valor']
        tipo = request.form.get('tipo', 'Particular')

        try:
            valor = float(valor)
            sucesso, mensagem = servico.editar_servico(id, nome, descricao, valor, tipo)
            flash(mensagem, "success" if sucesso else "error")
        except ValueError:
            flash("Valor inválido.", "error")

        return redirect('/servicos')
    else:
        servico_editar = servico.buscar_servico_por_id(id)
        if servico_editar is None:
            flash("Serviço não encontrado.", "error")
            return redirect('/servicos')
        servicos_list = servico.listar_servicos()
        return render_template('servicos.html', servicos=servicos_list, servico_editar=servico_editar)


@servicos_bp.route('/servicos/excluir/<int:id>', methods=['POST'])
def excluir_servico_route(id):
    sucesso, mensagem = servico.excluir_servico(id)
    flash(mensagem, "success" if sucesso else "error")
    return redirect('/servicos')


# ==================== ORÇAMENTOS ====================
orcamentos_bp = Blueprint('orcamentos', __name__)


@orcamentos_bp.route('/orcamentos', methods=['GET'])
def orcamentos_page():
    limpar = request.args.get('limpar')
    if limpar == '1':
        session.pop('filtro_busca', None)
        return redirect('/orcamentos')

    if 'busca' in request.args:
        termo_busca = request.args.get('busca', '').strip()
        session['filtro_busca'] = termo_busca
    else:
        termo_busca = session.get('filtro_busca', '')

    # Não lembra o status, usa o dos parâmetros ou o padrão "Todos"
    status_filtro = request.args.get('status', 'Todos')

    orcamentos_list = orcamento.listar_orcamentos(filtro=termo_busca, status_filtro=status_filtro)
    clientes_list = cliente.listar_clientes()
    veiculos_list = veiculo.listar_veiculos()
    return render_template('orcamentos.html',
                           orcamentos=orcamentos_list,
                           clientes=clientes_list,
                           veiculos=veiculos_list,
                           busca=termo_busca,
                           status_filtro=status_filtro)


@orcamentos_bp.route('/orcamentos/criar', methods=['POST'])
def criar_orcamento_route():
    cliente_id = request.form.get('cliente_id')
    veiculo_id = request.form.get('veiculo_id')
    observacoes = request.form.get('observacoes', '')

    if not all([cliente_id, veiculo_id]):
        flash("Cliente e veículo são obrigatórios.", "error")
        return redirect('/orcamentos')

    try:
        cliente_id = int(cliente_id)
        veiculo_id = int(veiculo_id)
        sucesso, mensagem, orcamento_id = orcamento.criar_orcamento(cliente_id, veiculo_id, observacoes)
        if sucesso:
            flash(mensagem, "success")
            return redirect(f'/orcamentos/{orcamento_id}')
        else:
            flash(mensagem, "error")
    except ValueError:
        flash("IDs inválidos.", "error")

    return redirect('/orcamentos')


@orcamentos_bp.route('/orcamentos/<int:id>', methods=['GET'])
def detalhe_orcamento_route(id):
    orc = orcamento.buscar_orcamento_por_id(id)
    if orc is None:
        flash("Orçamento não encontrado.", "error")
        return redirect('/orcamentos')

    itens = orcamento.listar_itens_orcamento(id)
    servicos_list = servico.listar_servicos()
    return render_template('orcamento_detalhe.html', orcamento=orc, itens=itens, servicos=servicos_list)


@orcamentos_bp.route('/orcamentos/<int:id>/adicionar_item', methods=['POST'])
def adicionar_item_route(id):
    tipo = request.form.get('tipo', 'Particular')
    servico_id = request.form.get('servico_id')
    descricao_personalizada = request.form.get('descricao_personalizada', '')
    valor_unitario = request.form.get('valor_unitario')

    if not valor_unitario:
        flash("O valor unitário é obrigatório.", "error")
        return redirect(f'/orcamentos/{id}')

    try:
        valor_unitario = float(valor_unitario)
        servico_id_int = int(servico_id) if servico_id else None
        sucesso, mensagem = orcamento.adicionar_item(id, servico_id_int, descricao_personalizada,
                                                     valor_unitario, tipo)
        flash(mensagem, "success" if sucesso else "error")
    except ValueError:
        flash("Valores inválidos.", "error")

    return redirect(f'/orcamentos/{id}')


@orcamentos_bp.route('/orcamentos/<int:id>/remover_item/<int:item_id>', methods=['POST'])
def remover_item_route(id, item_id):
    sucesso, mensagem = orcamento.remover_item(item_id)
    flash(mensagem, "success" if sucesso else "error")
    return redirect(f'/orcamentos/{id}')


@orcamentos_bp.route('/orcamentos/<int:id>/status', methods=['POST'])
def alterar_status_route(id):
    novo_status = request.form.get('status')
    sucesso, mensagem = orcamento.atualizar_status(id, novo_status)
    flash(mensagem, "success" if sucesso else "error")
    return redirect(f'/orcamentos/{id}')


@orcamentos_bp.route('/orcamentos/<int:id>/observacoes', methods=['POST'])
def atualizar_observacoes_route(id):
    observacoes = request.form.get('observacoes', '')
    sucesso, mensagem = orcamento.atualizar_observacoes(id, observacoes)
    flash(mensagem, "success" if sucesso else "error")
    return redirect(f'/orcamentos/{id}')


@orcamentos_bp.route('/orcamentos/excluir/<int:id>', methods=['POST'])
def excluir_orcamento_route(id):
    sucesso, mensagem = orcamento.excluir_orcamento(id)
    flash(mensagem, "success" if sucesso else "error")
    return redirect('/orcamentos')


# API para buscar veículos de um cliente (usada dinamicamente nos formulários)
@orcamentos_bp.route('/api/veiculos_cliente/<int:cliente_id>')
def api_veiculos_cliente(cliente_id):
    veiculos_list = veiculo.listar_veiculos_por_cliente(cliente_id)
    return jsonify([{
        'id': v[0],
        'marca': v[1],
        'modelo': v[2],
        'ano': v[3],
        'cor': v[4],
        'placa': v[5]
    } for v in veiculos_list])


# ==================== REGISTRO DOS BLUEPRINTS ====================
app.register_blueprint(index_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(veiculos_bp)
app.register_blueprint(servicos_bp)
app.register_blueprint(orcamentos_bp)


# ==================== EXECUÇÃO ====================
if __name__ == '__main__':
    app.run(debug=True)
