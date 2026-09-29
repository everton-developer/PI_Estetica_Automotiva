from flask import Flask, request, redirect, render_template, Blueprint, flash, jsonify, session
from functools import wraps
import urllib.parse

import cliente
import servico
import veiculo
import orcamento
import usuario
import historico
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

def format_placa(placa):
    if not placa or len(placa) < 4: return placa
    return f"{placa[:3]}-{placa[3:]}"

app.jinja_env.filters['format_cpf'] = format_cpf
app.jinja_env.filters['format_telefone'] = format_telefone
app.jinja_env.filters['format_cep'] = format_cep
app.jinja_env.filters['format_placa'] = format_placa


# ==================== DECORADORES DE AUTENTICAÇÃO ====================
def login_obrigatorio(f):
    """Decorator que exige login de usuário (adm ou comum)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash("Faça login para acessar o sistema.", "error")
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


def somente_adm(f):
    """Decorator que exige login de usuário administrador."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash("Faça login para acessar o sistema.", "error")
            return redirect('/login')
        if session['usuario'].get('tipo') != 'adm':
            flash("Acesso restrito ao administrador.", "error")
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function


def registrar_log(acao, detalhes):
    """Registra uma ação no histórico se houver usuário logado."""
    if 'usuario' in session:
        usuario_info = session['usuario']
        historico.registrar_acao(
            usuario_info.get('nome', 'Desconhecido'),
            usuario_info.get('login', 'desconhecido'),
            acao,
            detalhes
        )


# ==================== LOGIN/LOGOUT ====================
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    # Se já está logado, redireciona
    if 'usuario' in session:
        return redirect('/')

    if request.method == 'POST':
        # Verifica se é login com código de orçamento
        codigo_orcamento = request.form.get('codigo_orcamento', '').strip()
        if codigo_orcamento:
            orc = orcamento.buscar_orcamento_por_codigo(codigo_orcamento)
            if orc:
                # Salva na sessão como acesso de cliente
                session['cliente_orcamento'] = {
                    'codigo': codigo_orcamento,
                    'orcamento_id': orc[0]
                }
                codigo_url = urllib.parse.quote(codigo_orcamento, safe='')
                return redirect(f'/orcamento/visualizar/{codigo_url}')
            else:
                flash("Código de orçamento inválido ou não encontrado.", "error")
                return render_template('login.html')

        # Login com usuário e senha
        login_input = request.form.get('login', '').strip()
        senha_input = request.form.get('senha', '').strip()

        if not login_input or not senha_input:
            flash("Preencha o login e a senha.", "error")
            return render_template('login.html')

        usuario_data = usuario.autenticar_usuario(login_input, senha_input)
        if usuario_data:
            session['usuario'] = usuario_data
            registrar_log('Login', f"Usuário '{usuario_data['login']}' realizou login no sistema.")
            flash(f"Bem-vindo(a), {usuario_data['nome']}!", "success")
            return redirect('/')
        else:
            flash("Login ou senha incorretos.", "error")
            return render_template('login.html')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    if 'usuario' in session:
        registrar_log('Logout', f"Usuário '{session['usuario']['login']}' saiu do sistema.")
    session.clear()
    flash("Você saiu do sistema.", "success")
    return redirect('/login')


# ==================== VISUALIZAÇÃO DE ORÇAMENTO PELO CLIENTE ====================
@auth_bp.route('/orcamento/visualizar/<path:codigo>')
def visualizar_orcamento_cliente(codigo):
    codigo = urllib.parse.unquote(codigo).strip()
    cliente_orc = session.get('cliente_orcamento')
    usuario_logado = session.get('usuario')

    # Recupera código completo da sessão caso tenha sido truncado por '#' no navegador
    if cliente_orc:
        sess_codigo = cliente_orc.get('codigo', '')
        if sess_codigo == codigo or (sess_codigo and sess_codigo.startswith(codigo)):
            codigo = sess_codigo

    orc = orcamento.buscar_orcamento_por_codigo(codigo)
    if orc is None:
        # Se não encontrou e não está logado, tenta resolver via hash no navegador
        if not usuario_logado:
            return render_template('resolver_codigo.html', codigo_parcial=codigo)
        flash("Orçamento não encontrado ou foi excluído.", "error")
        return redirect('/orcamentos')

    # Se cliente não logado visualizou com sucesso, garante que a sessão está salva
    if not usuario_logado:
        session['cliente_orcamento'] = {
            'codigo': orc[14],
            'orcamento_id': orc[0]
        }

    itens = orcamento.listar_itens_orcamento(orc[0])
    return render_template('orcamento_cliente.html', orcamento=orc, itens=itens)


# ==================== PÁGINA INICIAL ====================
index_bp = Blueprint('index', __name__)


@index_bp.route('/')
@login_obrigatorio
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
@login_obrigatorio
def clientes_page():
    termo_busca = request.args.get('busca', '').strip()
    clientes_list = cliente.listar_clientes(termo_busca)
    return render_template('clientes.html', clientes=clientes_list, busca=termo_busca)


@clientes_bp.route('/clientes/cadastrar', methods=['POST'])
@login_obrigatorio
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
    if sucesso:
        registrar_log('Cadastro de Cliente', f"Cliente '{nome}' cadastrado.")
    return redirect('/clientes')


@clientes_bp.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
@login_obrigatorio
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
        if sucesso:
            registrar_log('Edição de Cliente', f"Cliente '{nome}' (ID: {id}) atualizado.")
        return redirect('/clientes')
    else:
        cliente_editar = cliente.buscar_cliente_por_id(id)
        if cliente_editar is None:
            flash("Cliente não encontrado.", "error")
            return redirect('/clientes')
        clientes_list = cliente.listar_clientes()
        return render_template('clientes.html', clientes=clientes_list, cliente_editar=cliente_editar)


@clientes_bp.route('/clientes/excluir/<int:id>', methods=['POST'])
@login_obrigatorio
def excluir_cliente_route(id):
    # Buscar nome do cliente antes de excluir para o log
    cl = cliente.buscar_cliente_por_id(id)
    nome_cliente = cl[1] if cl else f"ID {id}"
    sucesso, mensagem = cliente.excluir_cliente(id)
    flash(mensagem, "success" if sucesso else "error")
    if sucesso:
        registrar_log('Exclusão de Cliente', f"Cliente '{nome_cliente}' (ID: {id}) excluído.")
    return redirect('/clientes')


# ==================== VEÍCULOS ====================
veiculos_bp = Blueprint('veiculos', __name__)


@veiculos_bp.route('/veiculos', methods=['GET'])
@login_obrigatorio
def veiculos_page():
    termo_busca = request.args.get('busca', '').strip()
    veiculos_list = veiculo.listar_veiculos(termo_busca)
    clientes_list = cliente.listar_clientes()
    return render_template('veiculos.html', veiculos=veiculos_list, clientes=clientes_list, busca=termo_busca)


@veiculos_bp.route('/veiculos/cadastrar', methods=['POST'])
@login_obrigatorio
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
        if sucesso:
            registrar_log('Cadastro de Veículo', f"Veículo '{marca} {modelo}' (Placa: {placa}) cadastrado.")
    except ValueError:
        flash("ID do cliente inválido.", "error")

    return redirect('/veiculos')


@veiculos_bp.route('/veiculos/editar/<int:id>', methods=['GET', 'POST'])
@login_obrigatorio
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
        if sucesso:
            registrar_log('Edição de Veículo', f"Veículo '{marca} {modelo}' (ID: {id}) atualizado.")
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
@login_obrigatorio
def excluir_veiculo_route(id):
    v = veiculo.buscar_veiculo_por_id(id)
    desc = f"{v[1]} {v[2]} (Placa: {v[5]})" if v else f"ID {id}"
    sucesso, mensagem = veiculo.excluir_veiculo(id)
    flash(mensagem, "success" if sucesso else "error")
    if sucesso:
        registrar_log('Exclusão de Veículo', f"Veículo '{desc}' (ID: {id}) excluído.")
    return redirect('/veiculos')


# ==================== SERVIÇOS ====================
servicos_bp = Blueprint('servicos', __name__)


@servicos_bp.route('/servicos', methods=['GET'])
@login_obrigatorio
def servicos_page():
    termo_busca = request.args.get('busca', '').strip()
    servicos_list = servico.listar_servicos(termo_busca)
    return render_template('servicos.html', servicos=servicos_list, busca=termo_busca)


@servicos_bp.route('/servicos/cadastrar', methods=['POST'])
@login_obrigatorio
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
        if sucesso:
            registrar_log('Cadastro de Serviço', f"Serviço '{nome}' ({tipo}) - R$ {valor:.2f} cadastrado.")
    except ValueError:
        flash("Valor inválido. Use um número.", "error")

    return redirect('/servicos')


@servicos_bp.route('/servicos/editar/<int:id>', methods=['GET', 'POST'])
@login_obrigatorio
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
            if sucesso:
                registrar_log('Edição de Serviço', f"Serviço '{nome}' (ID: {id}) atualizado.")
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
@login_obrigatorio
def excluir_servico_route(id):
    sv = servico.buscar_servico_por_id(id)
    nome_servico = sv[1] if sv else f"ID {id}"
    sucesso, mensagem = servico.excluir_servico(id)
    flash(mensagem, "success" if sucesso else "error")
    if sucesso:
        registrar_log('Exclusão de Serviço', f"Serviço '{nome_servico}' (ID: {id}) excluído.")
    return redirect('/servicos')


# ==================== ORÇAMENTOS ====================
orcamentos_bp = Blueprint('orcamentos', __name__)


@orcamentos_bp.route('/orcamentos', methods=['GET'])
@login_obrigatorio
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
@login_obrigatorio
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
            # Buscar orçamento para pegar o código gerado
            orc = orcamento.buscar_orcamento_por_id(orcamento_id)
            codigo = orc[14] if orc else 'N/A'
            registrar_log('Criação de Orçamento', f"Orçamento #{orcamento_id} (Código: {codigo}) criado.")
            return redirect(f'/orcamentos/{orcamento_id}')
        else:
            flash(mensagem, "error")
    except ValueError:
        flash("IDs inválidos.", "error")

    return redirect('/orcamentos')


@orcamentos_bp.route('/orcamentos/<int:id>', methods=['GET'])
@login_obrigatorio
def detalhe_orcamento_route(id):
    orc = orcamento.buscar_orcamento_por_id(id)
    if orc is None:
        flash("Orçamento não encontrado.", "error")
        return redirect('/orcamentos')

    itens = orcamento.listar_itens_orcamento(id)
    servicos_list = servico.listar_servicos()
    return render_template('orcamento_detalhe.html', orcamento=orc, itens=itens, servicos=servicos_list)


@orcamentos_bp.route('/orcamentos/<int:id>/adicionar_item', methods=['POST'])
@login_obrigatorio
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
        if sucesso:
            desc = descricao_personalizada or f"Serviço ID {servico_id}"
            registrar_log('Adição de Item', f"Item '{desc}' (R$ {valor_unitario:.2f}) adicionado ao orçamento #{id}.")
    except ValueError:
        flash("Valores inválidos.", "error")

    return redirect(f'/orcamentos/{id}')


@orcamentos_bp.route('/orcamentos/<int:id>/remover_item/<int:item_id>', methods=['POST'])
@login_obrigatorio
def remover_item_route(id, item_id):
    sucesso, mensagem = orcamento.remover_item(item_id)
    flash(mensagem, "success" if sucesso else "error")
    if sucesso:
        registrar_log('Remoção de Item', f"Item #{item_id} removido do orçamento #{id}.")
    return redirect(f'/orcamentos/{id}')


@orcamentos_bp.route('/orcamentos/<int:id>/status', methods=['POST'])
@login_obrigatorio
def alterar_status_route(id):
    novo_status = request.form.get('status')
    sucesso, mensagem = orcamento.atualizar_status(id, novo_status)
    flash(mensagem, "success" if sucesso else "error")
    if sucesso:
        registrar_log('Alteração de Status', f"Status do orçamento #{id} alterado para '{novo_status}'.")
    return redirect(f'/orcamentos/{id}')


@orcamentos_bp.route('/orcamentos/<int:id>/observacoes', methods=['POST'])
@login_obrigatorio
def atualizar_observacoes_route(id):
    observacoes = request.form.get('observacoes', '')
    sucesso, mensagem = orcamento.atualizar_observacoes(id, observacoes)
    flash(mensagem, "success" if sucesso else "error")
    if sucesso:
        registrar_log('Atualização de Observações', f"Observações do orçamento #{id} atualizadas.")
    return redirect(f'/orcamentos/{id}')


@orcamentos_bp.route('/orcamentos/excluir/<int:id>', methods=['POST'])
@login_obrigatorio
def excluir_orcamento_route(id):
    orc = orcamento.buscar_orcamento_por_id(id)
    codigo = orc[14] if orc else 'N/A'
    sucesso, mensagem = orcamento.excluir_orcamento(id)
    flash(mensagem, "success" if sucesso else "error")
    if sucesso:
        registrar_log('Exclusão de Orçamento', f"Orçamento #{id} (Código: {codigo}) excluído.")
    return redirect('/orcamentos')


# API para buscar veículos de um cliente (usada dinamicamente nos formulários)
@orcamentos_bp.route('/api/veiculos_cliente/<int:cliente_id>')
@login_obrigatorio
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


# ==================== GERENCIAMENTO DE USUÁRIOS (SOMENTE ADM) ====================
usuarios_bp = Blueprint('usuarios', __name__)


@usuarios_bp.route('/usuarios', methods=['GET'])
@somente_adm
def usuarios_page():
    usuarios_list = usuario.listar_usuarios()
    return render_template('usuarios.html', usuarios=usuarios_list)


@usuarios_bp.route('/usuarios/cadastrar', methods=['POST'])
@somente_adm
def cadastrar_usuario_route():
    nome = request.form.get('nome', '').strip()
    login_input = request.form.get('login', '').strip()
    senha = request.form.get('senha', '').strip()
    email = request.form.get('email', '').strip()

    if not all([nome, login_input, senha, email]):
        flash("Todos os campos são obrigatórios.", "error")
        return redirect('/usuarios')

    sucesso, mensagem = usuario.cadastrar_usuario(nome, login_input, senha, email)
    flash(mensagem, "success" if sucesso else "error")
    if sucesso:
        registrar_log('Cadastro de Usuário', f"Usuário '{login_input}' ({nome}) cadastrado pelo administrador.")
    return redirect('/usuarios')


@usuarios_bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@somente_adm
def editar_usuario_route(id):
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        login_input = request.form.get('login', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()

        if not all([nome, login_input, email]):
            flash("Nome, login e e-mail são obrigatórios.", "error")
            return redirect('/usuarios')

        # Se senha vazia, não atualiza a senha
        senha_param = senha if senha else None
        sucesso, mensagem = usuario.atualizar_usuario(id, nome, login_input, email, senha_param)
        flash(mensagem, "success" if sucesso else "error")
        if sucesso:
            registrar_log('Edição de Usuário', f"Usuário '{login_input}' (ID: {id}) atualizado pelo administrador.")
        return redirect('/usuarios')
    else:
        usuario_editar = usuario.buscar_usuario_por_id(id)
        if usuario_editar is None:
            flash("Usuário não encontrado.", "error")
            return redirect('/usuarios')
        if usuario_editar[4] == 'adm':
            flash("O usuário administrador não pode ser editado pela interface.", "error")
            return redirect('/usuarios')
        usuarios_list = usuario.listar_usuarios()
        return render_template('usuarios.html', usuarios=usuarios_list, usuario_editar=usuario_editar)


@usuarios_bp.route('/usuarios/excluir/<int:id>', methods=['POST'])
@somente_adm
def excluir_usuario_route(id):
    usr = usuario.buscar_usuario_por_id(id)
    nome_usuario = f"{usr[1]} ({usr[2]})" if usr else f"ID {id}"
    sucesso, mensagem = usuario.excluir_usuario(id)
    flash(mensagem, "success" if sucesso else "error")
    if sucesso:
        registrar_log('Exclusão de Usuário', f"Usuário '{nome_usuario}' (ID: {id}) excluído pelo administrador.")
    return redirect('/usuarios')


# ==================== HISTÓRICO (SOMENTE ADM) ====================
historico_bp = Blueprint('historico', __name__)


@historico_bp.route('/historico', methods=['GET'])
@somente_adm
def historico_page():
    termo_busca = request.args.get('busca', '').strip()
    registros = historico.listar_historico(filtro=termo_busca if termo_busca else None, limite=200)
    return render_template('historico.html', registros=registros, busca=termo_busca)


# ==================== REGISTRO DOS BLUEPRINTS ====================
app.register_blueprint(auth_bp)
app.register_blueprint(index_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(veiculos_bp)
app.register_blueprint(servicos_bp)
app.register_blueprint(orcamentos_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(historico_bp)


# ==================== EXECUÇÃO ====================
if __name__ == '__main__':
    app.run(debug=True)
