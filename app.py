from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from datetime import datetime
import sqlite3
import os
import json

app = Flask(__name__)

# Banco de dados
DB_FILE = "pedidos_acougue.db"

def init_db():
    """Cria tabela se não existir"""
    nova_tabela = not os.path.exists(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if nova_tabela:
        c.execute('''
            CREATE TABLE pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente TEXT NOT NULL,
                telefone TEXT,
                itens TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pendente',
                retirar_as TEXT
            )
        ''')
    else:
        # Garante que a coluna retirar_as exista (ignora erro se já existir)
        try:
            c.execute("ALTER TABLE pedidos ADD COLUMN retirar_as TEXT")
            conn.commit()
        except Exception:
            pass

        # Garante que a coluna modificado exista
        try:
            c.execute("ALTER TABLE pedidos ADD COLUMN modificado INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass   

    conn.close()

def get_pedidos_pendentes():
    """Retorna pedidos pendentes ordenados por horário de criação"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM pedidos WHERE status = "pendente" ORDER BY criado_em ASC')
    pedidos = c.fetchall()
    conn.close()
    return pedidos

def salvar_pedido(cliente, telefone, itens, retirar_as=None):
    """Salva novo pedido no banco"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    itens_json = json.dumps(itens)
    c.execute('''
        INSERT INTO pedidos (cliente, telefone, itens, retirar_as)
        VALUES (?, ?, ?, ?)
    ''', (cliente, telefone, itens_json, retirar_as))
    conn.commit()
    conn.close()

def marcar_pronto(pedido_id):
    """Marca pedido como pronto"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE pedidos SET status = "pronto" WHERE id = ?', (pedido_id,))
    conn.commit()
    conn.close()

def cancelar_item_pedido(pedido_id, item_index):
    """Remove um item específico do pedido"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT itens FROM pedidos WHERE id = ?', (pedido_id,))
    resultado = c.fetchone()
    
    if resultado:
        itens = json.loads(resultado[0])
        if 0 <= item_index < len(itens):
            itens.pop(item_index)
        if len(itens) == 0:
            c.execute('UPDATE pedidos SET status = "pronto" WHERE id = ?', (pedido_id,))
        else:
            itens_json = json.dumps(itens)
            c.execute('UPDATE pedidos SET itens = ? WHERE id = ?', (itens_json, pedido_id))
        conn.commit()
    conn.close()

def modificar_item_pedido(pedido_id, item_index, novo_item):
    """Modifica um item específico do pedido e marca como modificado"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT itens FROM pedidos WHERE id = ?', (pedido_id,))
    resultado = c.fetchone()
    
    if resultado:
        itens = json.loads(resultado[0])
        if 0 <= item_index < len(itens):
            itens[item_index] = novo_item
            itens_json = json.dumps(itens)
            c.execute('''
                UPDATE pedidos 
                SET itens = ?, modificado = 1 
                WHERE id = ?
            ''', (itens_json, pedido_id))
            conn.commit()
    conn.close()

# Templates HTML

TEMPLATE_OPERADOR = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Operador - Casa de Carnes Bom Sabor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #111111;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
            padding: 32px 32px 16px 32px;
            max-width: 640px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
        }
        
        h1 {
            color: #b00020;
            margin-bottom: 16px;
            text-align: center;
            font-size: 24px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .brand-header {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            margin-bottom: 8px;
        }

        .brand-logo {
            height: 56px;
            width: auto;
        }

        .brand-text-main {
            font-size: 20px;
            font-weight: 700;
            color: #222222;
            letter-spacing: 1px;
        }

        .brand-text-sub {
            font-size: 11px;
            text-transform: uppercase;
            color: #888888;
        }

        .divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, #b00020, transparent);
            margin: 12px 0 24px 0;
        }
        
        .form-group {
            margin-bottom: 18px;
        }
        
        label {
            display: block;
            color: #444444;
            font-weight: 600;
            margin-bottom: 6px;
            font-size: 13px;
        }
        
        .required::after {
            content: " *";
            color: #b00020;
        }
        
        input[type="text"],
        input[type="tel"],
        input[type="number"],
        input[type="time"],
        textarea {
            width: 100%;
            padding: 10px 11px;
            border: 1px solid #dddddd;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.2s, box-shadow 0.2s;
            font-family: inherit;
        }
        
        input[type="text"]:focus,
        input[type="tel"]:focus,
        input[type="number"]:focus,
        input[type="time"]:focus,
        textarea:focus {
            outline: none;
            border-color: #b00020;
            box-shadow: 0 0 0 2px rgba(176, 0, 32, 0.15);
        }
        
        textarea {
            resize: vertical;
            min-height: 60px;
        }
        
        .cortes-group {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 8px;
        }
        
        .corte-btn {
            padding: 8px;
            border: 1px solid #e0e0e0;
            background: #fafafa;
            border-radius: 8px;
            cursor: pointer;
            font-size: 11px;
            font-weight: 500;
            transition: all 0.2s;
            text-align: center;
            color: #444444;
        }
        
        .corte-btn:hover {
            border-color: #b00020;
            background: #fff5f7;
        }
        
        .corte-btn.active {
            background: #b00020;
            color: white;
            border-color: #b00020;
        }
        
        .temperar-group {
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }
        
        .temperar-btn {
            flex: 1;
            padding: 9px;
            border: 1px solid #e0e0e0;
            background: #fafafa;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            transition: all 0.2s;
            color: #333333;
        }
        
        .temperar-btn:hover {
            border-color: #b00020;
            background: #fff5f7;
        }
        
        .temperar-btn.active {
            background: #b00020;
            color: white;
            border-color: #b00020;
        }
        
        .btn-remove-item {
            position: absolute;
            top: 8px;
            right: 8px;
            background: #b00020;
            color: white;
            border: none;
            border-radius: 50%;
            width: 26px;
            height: 26px;
            cursor: pointer;
            font-size: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        
        .btn-remove-item:hover {
            background: #8d001a;
            transform: scale(1.05);
        }
        
        .btn-add-item {
            width: 100%;
            padding: 11px;
            background: #b00020;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            margin: 12px 0 4px 0;
        }
        
        .btn-add-item:hover {
            background: #8d001a;
            box-shadow: 0 8px 18px rgba(176, 0, 32, 0.35);
        }
        
        .btn-submit {
            width: 100%;
            padding: 13px;
            background: linear-gradient(135deg, #000000 0%, #b00020 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.15s, box-shadow 0.15s;
            margin-top: 12px;
        }
        
        .btn-submit:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35);
        }
        
        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 16px;
            text-align: center;
            display: none;
            font-size: 13px;
        }
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 16px;
            text-align: center;
            display: none;
            font-size: 13px;
        }
        
        .moido-input {
            margin-top: 8px;
            display: none;
        }
        
        .moido-input.show {
            display: block;
        }

        .item-form {
            position: relative;
        }

        .item-form.removivel .btn-remove-item {
            display: flex;
        }

        .item-form:not(.removivel) .btn-remove-item {
            display: none;
        }

        footer {
            margin-top: 18px;
            text-align: center;
            font-size: 11px;
            color: #777777;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="brand-header">
            <img src="{{ url_for('static', filename='logo-bom-sabor.png') }}" alt="Casa de Carnes Bom Sabor" class="brand-logo">
            <div>
                <div class="brand-text-main">Casa de Carnes Bom Sabor</div>
                <div class="brand-text-sub">Qualidade em cada corte</div>
            </div>
        </div>
        <div class="divider"></div>
        <h1>Novo Pedido</h1>
        
        <div class="success-message" id="successMsg">Pedido enviado com sucesso!</div>
        <div class="error-message" id="errorMsg"></div>
        
        <form id="formPedido" onsubmit="submitPedido(event)">
            <div class="form-group">
                <label for="cliente" class="required">Nome do Cliente</label>
                <input type="text" id="cliente" name="cliente" required placeholder="Ex: João Silva">
            </div>
            
            <div class="form-group">
                <label for="telefone">Telefone (opcional)</label>
                <input type="tel" id="telefone" name="telefone" placeholder="Ex: (34) 99999-9999">
            </div>

            <div class="form-group">
                <label for="retirar_as">Retirar às (opcional)</label>
                <input type="time" id="retirar_as" name="retirar_as">
            </div>
            
            <div id="itensContainer">
                <!-- Primeiro item sempre visível - SEM botão de remover -->
                <div class="item-form" id="item-0">
                    <h3 style="margin-bottom: 12px; color: #333; font-size:15px;">Item #1</h3>
                    
                    <div class="form-group">
                        <label for="descricao-0" class="required">Quantidade</label>
                        <input type="text" id="descricao-0" name="descricao-0" placeholder="Ex: 1kg, 500g, 2 unidades">
                    </div>
                    
                    <div class="form-group">
                        <label class="required">Tipo de corte</label>
                        <div class="cortes-group">
                            <button type="button" class="corte-btn" data-corte="Bife" onclick="selecionarCorte(this, 0)">Bife</button>
                            <button type="button" class="corte-btn" data-corte="Bife fino" onclick="selecionarCorte(this, 0)">Bife fino</button>
                            <button type="button" class="corte-btn" data-corte="Bife grosso" onclick="selecionarCorte(this, 0)">Bife grosso</button>
                            <button type="button" class="corte-btn" data-corte="Grelha" onclick="selecionarCorte(this, 0)">Grelha</button>
                            <button type="button" class="corte-btn" data-corte="Iscas" onclick="selecionarCorte(this, 0)">Iscas</button>
                            <button type="button" class="corte-btn" data-corte="Cubos" onclick="selecionarCorte(this, 0)">Cubos</button>
                            <button type="button" class="corte-btn" data-corte="Feijoada" onclick="selecionarCorte(this, 0)">Feijoada</button>
                            <button type="button" class="corte-btn" data-corte="Inteiro" onclick="selecionarCorte(this, 0)">Inteiro</button>
                            <button type="button" class="corte-btn" data-corte="Peça" onclick="selecionarCorte(this, 0)">Peça</button>
                            <button type="button" class="corte-btn" data-corte="Medalhão" onclick="selecionarCorte(this, 0)">Medalhão</button>
                            <button type="button" class="corte-btn" data-corte="Moído X vezes" onclick="selecionarCorte(this, 0)">Moído X vezes</button>
                            <button type="button" class="corte-btn" data-corte="Para panela" onclick="selecionarCorte(this, 0)">Para panela</button>
                            <button type="button" class="corte-btn" data-corte="Para picadinho" onclick="selecionarCorte(this, 0)">Para picadinho</button>
                            <button type="button" class="corte-btn" data-corte="Para strogonoff" onclick="selecionarCorte(this, 0)">Para strogonoff</button>
                            <button type="button" class="corte-btn" data-corte="Para espeto" onclick="selecionarCorte(this, 0)">Para espeto</button>
                            <button type="button" class="corte-btn" data-corte="NAO IMPORTA" onclick="selecionarCorte(this, 0)">NAO IMPORTA</button>
                        </div>
                        <input type="hidden" id="corte-0" name="corte-0" value="">
                    </div>
                    
                    <div class="moido-input" id="moido-container-0">
                        <div class="form-group">
                            <label for="moido-0" class="required">Quantas vezes moído?</label>
                            <input type="number" id="moido-0" name="moido-0" min="1" max="10" placeholder="Ex: 2">
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label class="required">Temperar?</label>
                        <div class="temperar-group">
                            <button type="button" class="temperar-btn" data-temperar="Sim" onclick="selecionarTemperar(this, 0)">Sim</button>
                            <button type="button" class="temperar-btn" data-temperar="Não" onclick="selecionarTemperar(this, 0)">Não</button>
                            <button type="button" class="temperar-btn" data-temperar="Não Importa" onclick="selecionarTemperar(this, 0)">Não importa</button>
                        </div>
                        <input type="hidden" id="temperar-0" name="temperar-0" value="">
                    </div>
                    
                    <hr style="margin: 16px 0; border: none; border-top: 1px solid #e0e0e0;">
                </div>
            </div>
            
            <button type="button" class="btn-add-item" onclick="adicionarItem()">+ Adicionar outro item</button>
            
            <button type="submit" class="btn-submit">Confirmar pedido</button>
        </form>

        <footer>
            Casa de Carnes Bom Sabor · Sistema de Pedidos
        </footer>
    </div>
    
    <script>
        let itemCount = 1;
        
        function selecionarCorte(btn, itemIndex) {
            event.preventDefault();
            const corte = btn.getAttribute('data-corte');
            const botoesDesse = document.querySelectorAll(`#item-${itemIndex} .corte-btn`);
            
            if (btn.classList.contains('active')) {
                btn.classList.remove('active');
                document.getElementById(`corte-${itemIndex}`).value = '';
                
                const moidoContainer = document.getElementById(`moido-container-${itemIndex}`);
                moidoContainer.classList.remove('show');
                const moidoInput = document.getElementById(`moido-${itemIndex}`);
                if (moidoInput) moidoInput.required = false;
            } else {
                botoesDesse.forEach(b => b.classList.remove('active'));
                
                btn.classList.add('active');
                document.getElementById(`corte-${itemIndex}`).value = corte;
                
                const moidoContainer = document.getElementById(`moido-container-${itemIndex}`);
                const moidoInput = document.getElementById(`moido-${itemIndex}`);
                if (corte === "Moído X vezes") {
                    moidoContainer.classList.add('show');
                    if (moidoInput) moidoInput.required = true;
                } else {
                    moidoContainer.classList.remove('show');
                    if (moidoInput) moidoInput.required = false;
                }
            }
        }
        
        function selecionarTemperar(btn, itemIndex) {
            event.preventDefault();
            const temperar = btn.getAttribute('data-temperar');
            const botoesDesse = document.querySelectorAll(`#item-${itemIndex} .temperar-btn`);
            
            if (btn.classList.contains('active')) {
                btn.classList.remove('active');
                document.getElementById(`temperar-${itemIndex}`).value = '';
            } else {
                botoesDesse.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById(`temperar-${itemIndex}`).value = temperar;
            }
        }
        
        function adicionarItem() {
            event.preventDefault();
            
            const container = document.getElementById('itensContainer');
            const novoItem = document.createElement('div');
            novoItem.className = 'item-form removivel';
            novoItem.id = `item-${itemCount}`;
            
            novoItem.innerHTML = `
                <h3 style="margin-bottom: 12px; color: #333; font-size:15px;">Item #${itemCount + 1}</h3>
                <button type="button" class="btn-remove-item" onclick="removerItem(${itemCount})" title="Cancelar este item">✕</button>
                
                <div class="form-group">
                    <label for="descricao-${itemCount}" class="required">Quantidade</label>
                    <input type="text" id="descricao-${itemCount}" name="descricao-${itemCount}" placeholder="Ex: 1kg, 500g, 2 unidades">
                </div>
                
                <div class="form-group">
                    <label class="required">Tipo de corte</label>
                    <div class="cortes-group">
                        <button type="button" class="corte-btn" data-corte="Bife" onclick="selecionarCorte(this, ${itemCount})">Bife</button>
                        <button type="button" class="corte-btn" data-corte="Bife fino" onclick="selecionarCorte(this, ${itemCount})">Bife fino</button>
                        <button type="button" class="corte-btn" data-corte="Bife grosso" onclick="selecionarCorte(this, ${itemCount})">Bife grosso</button>
                        <button type="button" class="corte-btn" data-corte="Grelha" onclick="selecionarCorte(this, ${itemCount})">Grelha</button>
                        <button type="button" class="corte-btn" data-corte="Iscas" onclick="selecionarCorte(this, ${itemCount})">Iscas</button>
                        <button type="button" class="corte-btn" data-corte="Cubos" onclick="selecionarCorte(this, ${itemCount})">Cubos</button>
                        <button type="button" class="corte-btn" data-corte="Feijoada" onclick="selecionarCorte(this, ${itemCount})">Feijoada</button>
                        <button type="button" class="corte-btn" data-corte="Inteiro" onclick="selecionarCorte(this, ${itemCount})">Inteiro</button>
                        <button type="button" class="corte-btn" data-corte="Peça" onclick="selecionarCorte(this, ${itemCount})">Peça</button>
                        <button type="button" class="corte-btn" data-corte="Medalhão" onclick="selecionarCorte(this, ${itemCount})">Medalhão</button>
                        <button type="button" class="corte-btn" data-corte="Moído X vezes" onclick="selecionarCorte(this, ${itemCount})">Moído X vezes</button>
                        <button type="button" class="corte-btn" data-corte="Para panela" onclick="selecionarCorte(this, ${itemCount})">Para panela</button>
                        <button type="button" class="corte-btn" data-corte="Para picadinho" onclick="selecionarCorte(this, ${itemCount})">Para picadinho</button>
                        <button type="button" class="corte-btn" data-corte="Para strogonoff" onclick="selecionarCorte(this, ${itemCount})">Para strogonoff</button>
                        <button type="button" class="corte-btn" data-corte="Para espeto" onclick="selecionarCorte(this, ${itemCount})">Para espeto</button>
                        <button type="button" class="corte-btn" data-corte="NAO IMPORTA" onclick="selecionarCorte(this, ${itemCount})">NAO IMPORTA</button>
                    </div>
                    <input type="hidden" id="corte-${itemCount}" name="corte-${itemCount}" value="">
                </div>
                
                <div class="moido-input" id="moido-container-${itemCount}">
                    <div class="form-group">
                        <label for="moido-${itemCount}" class="required">Quantas vezes moído?</label>
                        <input type="number" id="moido-${itemCount}" name="moido-${itemCount}" min="1" max="10" placeholder="Ex: 2">
                    </div>
                </div>
                
                <div class="form-group">
                    <label class="required">Temperar?</label>
                    <div class="temperar-group">
                        <button type="button" class="temperar-btn" data-temperar="Sim" onclick="selecionarTemperar(this, ${itemCount})">Sim</button>
                        <button type="button" class="temperar-btn" data-temperar="Não" onclick="selecionarTemperar(this, ${itemCount})">Não</button>
                        <button type="button" class="temperar-btn" data-temperar="Não Importa" onclick="selecionarTemperar(this, ${itemCount})">Não importa</button>
                    </div>
                    <input type="hidden" id="temperar-${itemCount}" name="temperar-${itemCount}" value="">
                </div>
                
                <hr style="margin: 16px 0; border: none; border-top: 1px solid #e0e0e0;">
            `;
            
            container.appendChild(novoItem);
            itemCount++;
        }
        
        function removerItem(index) {
            event.preventDefault();
            const el = document.getElementById(`item-${index}`);
            if (el) el.remove();
        }
        
        function submitPedido(event) {
            event.preventDefault();
            
            const cliente = document.getElementById('cliente').value.trim();
            const telefone = document.getElementById('telefone').value.trim();
            const retirarAs = document.getElementById('retirar_as').value;
            
            if (!cliente) {
                showError('Nome do cliente é obrigatório!');
                return;
            }
            
            const itens = [];
            for (let i = 0; i < itemCount; i++) {
                const descricao = document.getElementById(`descricao-${i}`);
                const corte = document.getElementById(`corte-${i}`);
                const temperar = document.getElementById(`temperar-${i}`);
                
                if (descricao && descricao.value && descricao.value.trim()) {
                    if (!corte.value || !temperar.value) {
                        showError(`Item #${i + 1}: preencha o corte e se deve temperar.`);
                        return;
                    }
                    
                    const item = {
                        descricao: descricao.value.trim(),
                        corte: corte.value,
                        temperar: temperar.value
                    };
                    
                    if (corte.value === "Moído X vezes") {
                        const moidoInput = document.getElementById(`moido-${i}`);
                        const moido = moidoInput ? moidoInput.value : '';
                        if (!moido) {
                            showError(`Item #${i + 1}: informe quantas vezes moído.`);
                            return;
                        }
                        item.moido = moido;
                    }
                    
                    itens.push(item);
                }
            }
            
            if (itens.length === 0) {
                showError('Adicione pelo menos um item com quantidade.');
                return;
            }
            
            fetch('/api/novo-pedido', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    cliente: cliente,
                    telefone: telefone,
                    retirar_as: retirarAs,
                    itens: itens
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.sucesso) {
                    showSuccess('Pedido enviado com sucesso!');
                    
                    document.getElementById('formPedido').reset();
                    
                    for (let i = 1; i < itemCount; i++) {
                        const item = document.getElementById(`item-${i}`);
                        if (item) item.remove();
                    }
                    itemCount = 1;
                    
                    setTimeout(() => {
                        document.getElementById('successMsg').style.display = 'none';
                    }, 2500);
                } else {
                    showError('Erro ao salvar pedido.');
                }
            })
            .catch(error => {
                showError('Erro na conexão.');
            });
        }
        
        function showSuccess(msg) {
            const msgDiv = document.getElementById('successMsg');
            msgDiv.textContent = msg;
            msgDiv.style.display = 'block';
        }
        
        function showError(msg) {
            const msgDiv = document.getElementById('errorMsg');
            msgDiv.textContent = msg;
            msgDiv.style.display = 'block';
            setTimeout(() => {
                msgDiv.style.display = 'none';
            }, 5000);
        }
    </script>
</body>
</html>
'''

TEMPLATE_PRODUCAO = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Produção - Casa de Carnes Bom Sabor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: radial-gradient(circle at top, #b00020 0%, #000000 55%, #000000 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .brand-header {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            margin-bottom: 6px;
        }

        .brand-logo {
            height: 56px;
            width: auto;
        }

        .brand-text-main {
            font-size: 22px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: 1px;
        }

        .brand-text-sub {
            font-size: 11px;
            text-transform: uppercase;
            color: #f3cfd6;
        }

        .divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, #ffffff, transparent);
            margin: 10px 0 18px 0;
        }

        h1 {
            color: #ffffff;
            margin-bottom: 18px;
            text-align: center;
            font-size: 24px;
            text-transform: uppercase;
            letter-spacing: 0.12em;
        }
        
        .grid-pedidos {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 18px;
            margin-bottom: 18px;
        }
        
        .pedido-card {
            background: #ffffff;
            border-radius: 12px;
            padding: 22px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
            animation: slideIn 0.3s ease-out;
            border-left: 8px solid #b00020;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 320px;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-18px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        .pedido-info {
            flex: 1;
        }
        
        .pedido-cliente {
            font-size: 20px;
            font-weight: 700;
            color: #222222;
            margin-bottom: 4px;
        }
        
        .pedido-telefone {
            font-size: 13px;
            color: #777777;
            margin-bottom: 4px;
        }

        .pedido-retirada {
            font-size: 13px;
            font-weight: 700;
            color: #b00020;
            margin-bottom: 8px;
            background: #fff5f7;
            border-radius: 6px;
            padding: 4px 8px;
            display: inline-block;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .item-list {
            margin-bottom: 14px;
        }
        
        .item-list h4 {
            font-size: 11px;
            color: #999999;
            text-transform: uppercase;
            margin-bottom: 8px;
            letter-spacing: 0.12em;
        }
        
        .item {
            background: #fafafa;
            padding: 11px 11px 11px 11px;
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 13px;
            position: relative;
            padding-right: 40px;
            border: 1px solid #eeeeee;
        }
        
        .item-descricao {
            font-weight: 600;
            color: #333333;
            margin-bottom: 4px;
        }
        
        .item-corte {
            font-size: 12px;
            color: #555555;
            margin-bottom: 2px;
        }
        
        .item-temperar {
            display: inline-block;
            font-size: 13px;
            font-weight: 700;
            padding: 6px 14px;
            border-radius: 999px;
            margin-top: 6px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        
        .item-temperar.sim {
            background: #b00020;
            color: #ffffff;
            border: 1px solid #7d0016;
        }
        
        .item-temperar.nao {
            background: #12b981;
            color: #ffffff;
            border: 1px solid #0f8f64;
        }
        
        .item-temperar.nao-importa {
            background: #e5e7eb;
            color: #111827;
            border: 1px solid #d1d5db;
        }
        
        .btn-cancelar-item {
            position: absolute;
            right: 8px;
            top: 8px;
            background: #b00020;
            color: white;
            border: none;
            border-radius: 50%;
            width: 22px;
            height: 22px;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            padding: 0;
            line-height: 1;
        }
        
        .btn-cancelar-item:hover {
            background: #8d001a;
            transform: scale(1.05);
        }
        
        .pedido-tempo {
            font-size: 12px;
            color: #999999;
            margin-bottom: 14px;
            padding-top: 8px;
            border-top: 1px solid #eeeeee;
        }
        
        .btn-pronto {
            background: linear-gradient(135deg, #000000 0%, #b00020 100%);
            color: white;
            border: none;
            padding: 12px;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            width: 100%;
        }
        
        .btn-pronto:hover {
            transform: scale(1.02);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.45);
        }
        
        .btn-pronto:active {
            transform: scale(0.99);
        }
        
        .vazio {
            background: rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 50px 20px;
            text-align: center;
            color: #f0f0f0;
            font-size: 17px;
            grid-column: 1 / -1;
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        
        .vazio-emoji {
            font-size: 40px;
            margin-bottom: 12px;
        }
        
        .link-operador {
            text-align: center;
            margin-top: 18px;
        }
        
        .link-operador a {
            color: #ffe6eb;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
        }
        
        .link-operador a:hover {
            text-decoration: underline;
        }
        
        .info-refresh {
            text-align: center;
            color: #f5d7de;
            font-size: 11px;
            margin-top: 8px;
            opacity: 0.8;
        }

        footer {
            margin-top: 18px;
            text-align: center;
            font-size: 11px;
            color: #f0cdd5;
        }

        .btn-editar-pedido {
            position: absolute;
            top: 12px;
            right: 12px;
            background: #fbbf24;
            color: #000000;
            border: none;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 4px;
            box-shadow: 0 2px 8px rgba(251, 191, 36, 0.35);
        }
        .btn-editar-pedido:hover {
            background: #f59e0b;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(251, 191, 36, 0.45);
        }
        
        .pedido-card {
            position: relative; /* Garante que o botão absolute funcione */
        }

        .pedido-modificado {
            background: #fef3c7;
            border-left: 8px solid #f59e0b !important;
            border: 2px solid #fbbf24;
        }

        .alerta-modificado {
            background: #fef3c7;
            color: #92400e;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 12px;
            text-align: center;
            border: 1px solid #fbbf24;

        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.75);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            padding: 20px;
}

        .modal-overlay.show {
            display: flex;
}

        .modal-content {
            background: #ffffff;
            border-radius: 12px;
            padding: 24px;
            max-width: 600px;
            width: 100%;
            max-height: 85vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid #eeeeee;
}

        .modal-header h2 {
            color: #b00020;
            margin: 0;
            font-size: 20px;
}

        .btn-fechar-modal {
            background: #666666;
            color: white;
            border: none;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            cursor: pointer;
            font-size: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
}

        .btn-fechar-modal:hover {
        background: #333333;
        transform: scale(1.05);
}

.item-edicao {
    background: #fafafa;
    border: 1px solid #eeeeee;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
}

.item-edicao h4 {
    color: #333333;
    margin: 0 0 12px 0;
    font-size: 14px;
}

.form-group-modal {
    margin-bottom: 12px;
}

.form-group-modal label {
    display: block;
    color: #444444;
    font-weight: 600;
    margin-bottom: 6px;
    font-size: 12px;
}

.form-group-modal input {
    width: 100%;
    padding: 8px;
    border: 1px solid #dddddd;
    border-radius: 6px;
    font-size: 13px;
}

.cortes-group-modal {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    margin-top: 6px;
}

.corte-btn-modal {
    padding: 6px;
    border: 1px solid #e0e0e0;
    background: #fafafa;
    border-radius: 6px;
    cursor: pointer;
    font-size: 10px;
    font-weight: 500;
    transition: all 0.2s;
    text-align: center;
    color: #444444;
}

.corte-btn-modal:hover {
    border-color: #b00020;
    background: #fff5f7;
}

.corte-btn-modal.active {
    background: #b00020;
    color: white;
    border-color: #b00020;
}

.temperar-group-modal {
    display: flex;
    gap: 6px;
    margin-top: 6px;
}

.temperar-btn-modal {
    flex: 1;
    padding: 8px;
    border: 1px solid #e0e0e0;
    background: #fafafa;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    transition: all 0.2s;
    color: #333333;
}

.temperar-btn-modal:hover {
    border-color: #b00020;
    background: #fff5f7;
}

.temperar-btn-modal.active {
    background: #b00020;
    color: white;
    border-color: #b00020;
}

.btn-salvar-edicao {
    width: 100%;
    padding: 12px;
    background: linear-gradient(135deg, #000000 0%, #b00020 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    margin-top: 8px;
}

.btn-salvar-edicao:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
}
        }

    </style>
</head>
<body>
    <div class="container">
        <div class="brand-header">
            <img src="{{ url_for('static', filename='logo-bom-sabor.png') }}" alt="Casa de Carnes Bom Sabor" class="brand-logo">
            <div>
                <div class="brand-text-main">Casa de Carnes Bom Sabor</div>
                <div class="brand-text-sub">Qualidade em cada corte</div>
            </div>
        </div>
        <div class="divider"></div>
        <h1>Fila de Produção</h1>
        
        <div class="grid-pedidos" id="fila">
            <div class="vazio">
                <div class="vazio-emoji">✓</div>
                <div>Nenhum pedido no momento</div>
            </div>
        </div>
        
        <div class="info-refresh">Atualiza automaticamente a cada 2 segundos</div>
        
        <div class="link-operador">
            <a href="/operador" target="_blank">Ir para tela do operador</a>
        </div>

        <footer>
            Casa de Carnes Bom Sabor · Sistema de Pedidos
        </footer>
    </div>
    
    <script>
        function formatarTempo(dataString) {
            const data = new Date(dataString);
            const agora = new Date();
            const diff = Math.floor((agora - data) / 1000);
            
            if (diff < 60) return 'agora';
            if (diff < 3600) return Math.floor(diff / 60) + 'min atrás';
            return Math.floor(diff / 3600) + 'h atrás';
        }
        
        function editarPedido(pedidoId) {
    alert(`Editar pedido #${pedidoId} - Funcionalidade em desenvolvimento`);
}


        function carregarPedidos() {
    fetch('/api/pedidos-pendentes')
        .then(response => response.json())
        .then(data => {
            const filaDiv = document.getElementById('fila');
            
            if (data.pedidos.length === 0) {
                filaDiv.innerHTML = `
                    <div class="vazio">
                        <div class="vazio-emoji">🍖</div>
                        <div>Nenhum pedido no momento</div>
                    </div>
                `;
                return;
            }

            filaDiv.innerHTML = data.pedidos.map(pedido => {
                const itens = JSON.parse(pedido.itens);
                
                let itensHTML = '';
                itens.forEach((item, idx) => {
                    let tempeInfo = '';
                    if (item.temperar === 'Sim') {
                        tempeInfo = `<span class="item-temperar sim">Temperar</span>`;
                    } else if (item.temperar === 'Não') {
                        tempeInfo = `<span class="item-temperar nao">Sem tempero</span>`;
                    } else {
                        tempeInfo = `<span class="item-temperar nao-importa">Não importa</span>`;
                    }

                    let corteInfo = item.corte;
                    if (item.corte === 'Moído X vezes' && item.moido) {
                        corteInfo = `${item.corte} (${item.moido}x)`;
                    }

                    itensHTML += `
                        <div class="item">
                            <button class="btn-cancelar-item" onclick="cancelarItem(${pedido.id}, ${idx})" title="Cancelar item">×</button>
                            <div style="margin-bottom:4px">${tempeInfo}</div>
                            <div class="item-descricao">${item.descricao}</div>
                            <div class="item-corte">Corte: ${corteInfo}</div>
                        </div>
                    `;
                });

                // Alerta de pedido modificado
                let alertaModificado = '';
                if (pedido.modificado === 1) {
                    alertaModificado = '<div class="alerta-modificado">⚠️ Pedido foi modificado pelo operador</div>';
                }

                // Classe adicional se modificado
                let classeModificado = pedido.modificado === 1 ? 'pedido-modificado' : '';

                return `
                    <div class="pedido-card ${classeModificado}">
                        <button class="btn-editar-pedido" onclick="editarPedido(${pedido.id})">
                            Editar pedido ✏️
                        </button>
                        
                        <div class="pedido-info">
                            ${alertaModificado}
                            <div class="pedido-cliente">${pedido.cliente}</div>
                            ${pedido.telefone ? `<div class="pedido-telefone">Telefone: ${pedido.telefone}</div>` : ''}
                            ${pedido.retirar_as ? `<div class="pedido-retirada">Retirar às ${pedido.retirar_as}</div>` : ''}
                            
                            <div class="item-list">
                                <h4>Itens</h4>
                                ${itensHTML}
                            </div>
                        </div>
                        
                        <div class="pedido-tempo">#${pedido.id} • ${formatarTempo(pedido.criado_em)}</div>
                        <button class="btn-pronto" onclick="marcarPronto(${pedido.id})">✓ Marcar como pronto</button>
                    </div>
                `;
            }).join('');
        });
}

        
        function marcarPronto(pedidoId) {
            fetch('/api/marcar-pronto', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: pedidoId })
            })
            .then(response => response.json())
            .then(data => {
                carregarPedidos();
            });
        }
        
        function cancelarItem(pedidoId, itemIndex) {
            fetch('/api/cancelar-item', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ pedido_id: pedidoId, item_index: itemIndex })
            })
            .then(response => response.json())
            .then(data => {
                carregarPedidos();
            });
        }
        
        carregarPedidos();
        setInterval(carregarPedidos, 2000);
    </script>
</body>
</html>
'''

# Rotas

@app.route('/')
def index():
    return redirect('/operador')

@app.route('/operador')
def operador():
    return render_template_string(TEMPLATE_OPERADOR)

@app.route('/producao')
def producao():
    return render_template_string(TEMPLATE_PRODUCAO)

@app.route('/api/novo-pedido', methods=['POST'])
def novo_pedido():
    data = request.get_json()
    cliente = data.get('cliente', '').strip()
    telefone = data.get('telefone', '').strip()
    itens = data.get('itens', [])
    retirar_as = data.get('retirar_as', '').strip()
    
    if not cliente:
        return jsonify({'sucesso': False, 'erro': 'Nome do cliente é obrigatório'})
    
    if not itens:
        return jsonify({'sucesso': False, 'erro': 'Adicione pelo menos um item'})
    
    salvar_pedido(cliente, telefone, itens, retirar_as or None)
    return jsonify({'sucesso': True})

@app.route('/api/pedidos-pendentes', methods=['GET'])
def pedidos_pendentes():
    pedidos = get_pedidos_pendentes()
    pedidos_list = [
        {
            'id': p['id'],
            'cliente': p['cliente'],
            'telefone': p['telefone'],
            'itens': p['itens'],
            'criado_em': p['criado_em'],
            'retirar_as': p['retirar_as'],
            'modificado': p['modificado'],
        }
    
        for p in pedidos
    ]
    return jsonify({'pedidos': pedidos_list})

@app.route('/api/marcar-pronto', methods=['POST'])
def marcar_como_pronto():
    data = request.get_json()
    pedido_id = data.get('id')
    marcar_pronto(pedido_id)
    return jsonify({'sucesso': True})

@app.route('/api/cancelar-item', methods=['POST'])
def cancelar_item():
    data = request.get_json()
    pedido_id = data.get('pedido_id')
    item_index = data.get('item_index')
    cancelar_item_pedido(pedido_id, item_index)
    return jsonify({'sucesso': True})

@app.route('/api/modificar-item', methods=['POST'])
def modificar_item():
    data = request.get_json()
    pedido_id = data.get('pedido_id')
    item_index = data.get('item_index')
    novo_item = data.get('novo_item')
    
    if pedido_id is not None and item_index is not None and novo_item:
        modificar_item_pedido(pedido_id, item_index, novo_item)
        return jsonify({'sucesso': True})
    
    return jsonify({'sucesso': False, 'erro': 'Dados inválidos'})

if __name__ == '__main__':
    init_db()
    print("🚀 Servidor rodando!")
    print("📋 Operador: http://localhost:5000/operador")
    print("⚡ Produção: http://localhost:5000/producao")
    app.run(host="0.0.0.0", debug=True, port=5000)

