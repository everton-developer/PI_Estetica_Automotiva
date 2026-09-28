# Documentação do Sistema - Studio Alex Dantas (Martelinho de Ouro)

Este documento detalha o escopo técnico do projeto da aplicação web desenvolvida para a gestão do Studio Alex Dantas.

---

## 1. O que é possível fazer na aplicação (Funcionalidades)

A aplicação atua como um sistema de gestão (ERP/CRM) simplificado e direto ao ponto para um estúdio de estética automotiva. As principais funcionalidades incluem:

*   **Gestão de Clientes (CRUD):** 
    *   Cadastro, listagem, edição e exclusão de clientes.
    *   Preenchimento automático do endereço via integração com a API do ViaCEP.
    *   Busca rápida de clientes por nome ou CPF.
*   **Gestão de Veículos (CRUD):**
    *   Gerenciamento completo do cadastro de veículos, vinculados especificamente a cada cliente (Placa, Marca, Modelo, Ano e Cor).
*   **Gestão de Serviços:**
    *   Tabela de preços pré-definida dividida em três categorias principais: Estética, Reparo e Customização.
    *   Possibilidade de adicionar "Serviços Personalizados" com valores customizados avulsos na hora do orçamento.
*   **Gestão de Orçamentos:**
    *   Criação de orçamentos vinculando **Cliente**, **Veículo** e múltiplos **Itens/Serviços**.
    *   Cálculo automático do Valor Total.
    *   Controle de Status com indicativos visuais (Pendente, Aprovado, Recusado, Concluído).
    *   Campo para observações adicionais.
*   **Impressão e Compartilhamento:**
    *   Geração de versão otimizada do orçamento para impressão (Layout A4 em Preto e Branco / Papel Timbrado).
    *   Botões de compartilhamento direto com mensagem pré-formatada para envio via **WhatsApp** e **E-mail** ao cliente.
*   **Personalização de Interface:**
    *   Suporte nativo a Tema Claro (Light Mode) e Tema Escuro (Dark Mode), com preferência salva localmente no navegador do usuário.

---

## 2. Tecnologias, Linguagens e Complementos Utilizados

A arquitetura do sistema segue o modelo cliente-servidor, com renderização de páginas no servidor (Server-Side Rendering).

### 2.1. Backend (Servidor)
*   **Python (v3.x):** Linguagem de programação central escolhida pela sua clareza, velocidade de desenvolvimento e integração com dados.
*   **Flask:** Micro-framework web utilizado para gerenciar as rotas, requisições HTTP e a lógica da aplicação (Controllers).
*   **Jinja2:** Motor de templates (Template Engine) nativo do Flask, utilizado para mesclar código Python condicional e de repetição dentro do HTML bruto.

### 2.2. Frontend (Interface do Usuário)
*   **HTML5 / CSS3:** Estruturação semântica das páginas e estilização visual das telas.
*   **JavaScript (Vanilla JS):** Linguagem utilizada no navegador do cliente para interatividade (troca de Dark Mode, integração ViaCEP, manipulação do botão de WhatsApp).
*   **Bootstrap 5:** Framework CSS utilizado para garantir que a aplicação seja 100% responsiva (funcione em celulares, tablets e computadores), utilizando seu sistema de Grid e componentes como Modais e Cards.
*   **Bootstrap Icons:** Biblioteca de ícones vetoriais utilizada em botões e enfeites na navegação.

---

## 3. Arquitetura de Banco de Dados

A aplicação foi planejada de forma híbrida para operar em dois ambientes distintos sem necessidade de mudança severa no código-fonte, configurada no arquivo `db.py`:

*   **Ambiente de Desenvolvimento (Local):** 
    *   **SQLite3 (`banco.db`):** Banco de dados relacional embarcado em servidor local para desenvolvimento rápido. Não exige instalação extra.
*   **Ambiente de Produção (Nuvem):**
    *   **PostgreSQL via Neon Serverless:** O banco de dados oficial hospedado pela **Neon**. Robusto, escalável e utilizado na infraestrutura de nuvem, que se conecta à aplicação através do conector psycopg2 e variáveis de ambiente (`DATABASE_URL`).

O banco de dados é composto por 4 tabelas principais totalmente relacionadas: `clientes`, `veiculos`, `servicos`, `orcamentos` e `orcamento_itens`.

---

## 4. Hospedagem e Processo de Deploy (Vercel)

A aplicação web foi arquitetada para ser hospedada e publicada de maneira escalável utilizando a plataforma **Vercel**, uma provedora de hospedagem em nuvem que suporta de forma nativa a execução de aplicações modernas.

*   **Vercel Serverless:** A aplicação Flask não roda em um servidor tradicional 24/7. Ela é empacotada pela Vercel como uma função Serverless (via arquivo de configuração `vercel.json`). Isso significa que o servidor "sobe" instantaneamente sob demanda quando um cliente acessa, gerando grande economia de recursos e performance imediata.
*   **Processo de Publicação (Deploy):** O pipeline de deploy no Vercel é contínuo (CI/CD). Isso significa que integrar o projeto ao GitHub, GitLab e afins permite atualizações automáticas sempre que você envia (`push`) uma alteração no código. Alternativamente, pode ser utilizado o utilitário Vercel CLI (terminal) executando um simples comando `vercel --prod`, publicando e disponibilizando os arquivos em poucos segundos.
*   **Vercel Postgres (Neon):** Conforme mapeado na arquitetura, a infraestrutura da Vercel gerencia e armazena de forma segura a variável `DATABASE_URL`. Durante o acesso à nuvem, é no painel de configurações (Dashboard da Vercel) que definimos de onde o sistema puxa as informações dos orçamentos, garantindo total isolamento da aplicação e do banco.

---

## 5. Bibliografia e Fontes de Dados (Documentação Oficial)

Todo o desenvolvimento técnico, bem como a implementação de integrações, foi respaldado pelas seguintes documentações oficiais sob as quais o código se apoiou:

*   **Fundamentos Python:** Documentação Oficial da Linguagem Python 3 — *https://docs.python.org/3/*
*   **Framework Web:** Flask Official Documentation (Pallets Projects) — *https://flask.palletsprojects.com/*
*   **Template Engine:** Jinja2 Official Documentation — *https://jinja.palletsprojects.com/*
*   **Banco de Dados Neon / Postgres:** Console e Documentação da Neon Serverless PostgreSQL — *https://neon.tech/docs*
*   **Conector PostgreSQL:** Documentação do psycopg2 (Python-PostgreSQL Database Adapter) — *https://www.psycopg.org/docs/*
*   **Framework Visual UI:** Documentação do Bootstrap v5.3 — *https://getbootstrap.com/docs/5.3/getting-started/introduction/*
*   **Integração de CEP:** ViaCEP WEBSERVICE API de Códigos Postais — *https://viacep.com.br/*
*   **Integração Mensageria:** API Universal do WhatsApp (Click to Chat) — *https://faq.whatsapp.com/5913398998672934*

---

## 6. Histórico de Atualizações Recentes (Changelog)

**Atualizações de Regra de Negócio e UX/UI implementadas:**
*   **Armazenamento de Dados Limpos:** Os campos de CPF, Telefone e CEP passaram a ser registrados no banco de dados apenas como números, via higienização em Regex. A formatação visual (com traços e pontos) foi delegada aos Custom Filters do Jinja no Frontend.
*   **Formatação de Placas:** As placas veiculares (ex: `ABC-1D23`) agora são automaticamente convertidas para caixa alta e têm hífens ignorados no banco, mas injetados com Regex customizado via template engine ao exibir.
*   **Flexibilidade no Cadastro de Clientes:** O CPF deixou de ser um campo de preenchimento obrigatório para viabilizar novos modelos de negócio. O banco de dados foi migrado para suprimir restrições do tipo `NOT NULL` referentes a essa coluna.
*   **Orçamentos Simplificados:** A coluna de Quantidade (`qtd`) foi revogada dos modelos de Orçamento, pois os serviços prestados possuem, por sua natureza, uma incidência unitária indivisível na negociação.
*   **Filtro de Sessão e Status:** Ao re-acessar o painel de visualização principal dos orçamentos, o sistema deixou de manter a lembrança forçada do último status (por meio de reset na variável de `session`). O status retornará de forma previsível e absoluta a “Todos”.
*   **Interface em Formulários:** Refinamentos nas listas de seleção suspensa (Ocultamento de preço de tabela no momento da escolha de serviço, pré-definição de select de Tipo como "Selecione") e redimensionamento dinâmico responsivo no botão de inserção de itens (`btn-sm` / `w-100` nas quebras de tela mobile).
*   **Script de Reset:** Adição de um arquivo `reset_db.py` autônomo (não hospedado) que permite purificar tabelas e recriá-las a partir do zero nas bases relacionais em nuvem da Vercel.
