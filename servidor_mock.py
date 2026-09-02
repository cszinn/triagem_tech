"""
servidor_mock.py - Servidor de teste local para o Painel de Triagem.
Simula todos os endpoints da API real sem precisar de banco de dados.

Uso:
    pip install flask
    python servidor_mock.py

O servidor sobe em http://localhost:5000/api
Configure o app para apontar para ele em config.json:
    "api_url": "http://localhost:5000/api"
"""

from flask import Flask, jsonify, request

app = Flask(__name__)

_marcas = [
    {"id": 1, "nome": "Apple"},
    {"id": 2, "nome": "Samsung"},
    {"id": 3, "nome": "Motorola"},
    {"id": 4, "nome": "Xiaomi"},
    {"id": 5, "nome": "LG"},
    {"id": 6, "nome": "Nokia"},
    {"id": 7, "nome": "Sony"},
    {"id": 8, "nome": "Huawei"},
]

_modelos_por_marca = {
    "Apple": [
        {"id": 1, "nome": "iPhone 11"},
        {"id": 2, "nome": "iPhone 12"},
        {"id": 3, "nome": "iPhone 13"},
        {"id": 4, "nome": "iPhone 14"},
        {"id": 5, "nome": "iPhone 15"},
        {"id": 6, "nome": "iPhone SE (2a Ger)"},
        {"id": 7, "nome": "iPhone XR"},
        {"id": 8, "nome": "iPhone X"},
    ],
    "Samsung": [
        {"id": 9,  "nome": "Galaxy A54"},
        {"id": 10, "nome": "Galaxy A34"},
        {"id": 11, "nome": "Galaxy S23"},
        {"id": 12, "nome": "Galaxy S21"},
        {"id": 13, "nome": "Galaxy A13"},
    ],
    "Motorola": [
        {"id": 14, "nome": "Moto G73"},
        {"id": 15, "nome": "Moto G52"},
        {"id": 16, "nome": "Edge 30"},
    ],
    "Xiaomi": [
        {"id": 17, "nome": "Redmi Note 12"},
        {"id": 18, "nome": "Redmi 10"},
        {"id": 19, "nome": "POCO X5"},
    ],
}

_modelos_fisicos_por_modelo = {
    "iPhone 11":   [{"id": 1, "nome": "iPhone12,1"}],
    "iPhone 12":   [{"id": 2, "nome": "iPhone13,2"}],
    "iPhone 13":   [{"id": 3, "nome": "iPhone14,5"}],
    "iPhone 14":   [{"id": 4, "nome": "iPhone14,7"}],
    "iPhone 15":   [{"id": 5, "nome": "iPhone15,4"}],
    "iPhone XR":   [{"id": 6, "nome": "iPhone11,8"}],
    "iPhone X":    [{"id": 7, "nome": "iPhone10,3"}, {"id": 8, "nome": "iPhone10,6"}],
    "Galaxy A54":  [{"id": 9, "nome": "SM-A546B"}],
    "Galaxy S23":  [{"id": 10, "nome": "SM-S911B"}],
    "Moto G73":    [{"id": 11, "nome": "XT2237-2"}],
    "Redmi Note 12": [{"id": 12, "nome": "23028RA60L"}],
}

_cores = [
    {"id": 1, "nome": "Preto"},
    {"id": 2, "nome": "Branco"},
    {"id": 3, "nome": "Azul"},
    {"id": 4, "nome": "Vermelho"},
    {"id": 5, "nome": "Verde"},
    {"id": 6, "nome": "Rosa"},
    {"id": 7, "nome": "Dourado"},
    {"id": 8, "nome": "Cinza"},
    {"id": 9, "nome": "Roxo"},
    {"id": 10, "nome": "Prata"},
]

_estados_fisicos = [
    {"id": 1, "nome": "Excelente"},
    {"id": 2, "nome": "Bom"},
    {"id": 3, "nome": "Regular"},
    {"id": 4, "nome": "Ruim"},
    {"id": 5, "nome": "Sucata"},
]

_condicoes_funcionamento = [
    {"id": 1, "nome": "Excelente"},
    {"id": 2, "nome": "Liga Parcialmente"},
    {"id": 3, "nome": "Nao Liga"},
    {"id": 4, "nome": "Bloqueado"},
]

_estados_acesso = [
    {"id": 1, "nome": "Desbloqueado"},
    {"id": 2, "nome": "Bloqueado por Senha"},
    {"id": 3, "nome": "Bloqueado por Operadora"},
    {"id": 4, "nome": "iCloud Ativo"},
    {"id": 5, "nome": "FRP Ativo"},
]

_avarias = [
    {"id": 1,  "nome": "Tela Quebrada"},
    {"id": 2,  "nome": "Tela com Manchas"},
    {"id": 3,  "nome": "Arranhoes na Tela"},
    {"id": 4,  "nome": "Carcaca Amassada"},
    {"id": 5,  "nome": "Arranhoes na Carcaca"},
    {"id": 6,  "nome": "Camera Quebrada"},
    {"id": 7,  "nome": "Botao Volume Quebrado"},
    {"id": 8,  "nome": "Botao Power Quebrado"},
    {"id": 9,  "nome": "Conector Danificado"},
    {"id": 10, "nome": "Sem Bateria"},
    {"id": 11, "nome": "Bateria Inchada"},
    {"id": 12, "nome": "Touch Sem Resposta"},
]

_caixas_recebimentos = [
    {"id": 1, "nome": "Caixa-001"},
    {"id": 2, "nome": "Caixa-002"},
    {"id": 3, "nome": "Caixa-003"},
    {"id": 4, "nome": "Lote RF Marco"},
    {"id": 5, "nome": "Lote RF Abril"},
]

_proximo_id_estoque = 100
_itens_estoque = {}

@app.route("/api/triagem/dominios", methods=["GET"])
def dominios():
    return jsonify({
        "marcas":                  _marcas,
        "modelos":                 [m for lista in _modelos_por_marca.values() for m in lista],
        "cores":                   _cores,
        "estadosFisicos":          _estados_fisicos,
        "condicoesFuncionamento":  _condicoes_funcionamento,
        "estadosAcesso":           _estados_acesso,
        "avarias":                 _avarias,
        "caixasRecebimentos":      _caixas_recebimentos,
    })

@app.route("/api/triagem/marcas/<marca>/modelos", methods=["GET"])
def modelos_por_marca(marca):
    for chave, lista in _modelos_por_marca.items():
        if chave.lower() == marca.lower():
            return jsonify(lista)
    return jsonify([])

@app.route("/api/triagem/modelos/<modelo>/modelos-fisicos", methods=["GET"])
def modelos_fisicos(modelo):
    for chave, lista in _modelos_fisicos_por_modelo.items():
        if chave.lower() == modelo.lower():
            return jsonify(lista)
    return jsonify([{"id": 0, "nome": "N/A"}])

@app.route("/api/triagem/triagem", methods=["POST"])
def salvar_triagem():
    global _proximo_id_estoque
    dados = request.get_json(silent=True) or {}
    modelo_nome = dados.get("modelo", {}).get("modelo", {}).get("nome", "?")
    id_gerado = _proximo_id_estoque
    _proximo_id_estoque += 1
    
    _itens_estoque[id_gerado] = dados
    _itens_estoque[id_gerado]["idItemEstoque"] = id_gerado
    
    print(f"[MOCK] Triagem recebida: {modelo_nome} -> ID Estoque: {id_gerado}")
    return jsonify({"idItemEstoque": id_gerado, "mensagem": "Triagem salva (MODO MOCK)", "modelo": modelo_nome})

@app.route("/api/triagem/triagem/<int:item_id>", methods=["GET"])
def buscar_triagem(item_id):
    if item_id in _itens_estoque:
        return jsonify(_itens_estoque[item_id])
    return jsonify({"mensagem": "Item nao encontrado"}), 404

@app.route("/api/triagem/<int:item_id>", methods=["PUT", "PATCH"])
def atualizar_triagem(item_id):
    if item_id not in _itens_estoque:
        return jsonify({"mensagem": "Item nao encontrado"}), 404
        
    dados = request.get_json(silent=True) or {}
    _itens_estoque[item_id].update(dados)
    
    print(f"[MOCK] Triagem atualizada -> ID Estoque: {item_id}")
    return jsonify({"idItemEstoque": item_id, "mensagem": "Triagem atualizada (MODO MOCK)"})

@app.route("/api/triagem/avarias", methods=["POST"])
def cadastrar_avaria():
    dados = request.get_json(silent=True) or {}
    nome = dados.get("nome", "").strip()
    if not nome:
        return jsonify({"mensagem": "Nome obrigatorio"}), 400
    for a in _avarias:
        if a["nome"].lower() == nome.lower():
            return jsonify({"mensagem": f"Avaria '{nome}' ja existe."}), 400
    novo_id = max(a["id"] for a in _avarias) + 1
    _avarias.append({"id": novo_id, "nome": nome})
    print(f"[MOCK] Nova avaria: '{nome}' (id={novo_id})")
    return jsonify({"id": novo_id, "nome": nome})

if __name__ == "__main__":
    print("=" * 55)
    print("  Servidor MOCK da Triagem - Modo Offline")
    print("=" * 55)
    print("  URL base : http://localhost:5000/api")
    print()
    print('  Coloque no config.json:')
    print('    "api_url": "http://localhost:5000/api"')
    print("=" * 55)
    app.run(host="localhost", port=5000, debug=True, use_reloader=False)
