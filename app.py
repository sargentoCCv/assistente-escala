from flask import Flask, request, jsonify, render_template
import spacy
import nltk
import re
from nltk.sentiment import SentimentIntensityAnalyzer

app = Flask(__name__)

print('Carregando modelos...')
nlp = spacy.load('pt_core_news_sm')
sia = SentimentIntensityAnalyzer()
print('Tudo carregado senhor')

def extrair_entidades_militar(texto):
    entidades = {'postos': [], 'nomes': [], 'datas': [], 'unidades': []}
    postos = ['Soldado', 'Cabo', 'Sargento', 'Terceiro-Sargento', 'Segundo-Sargento', 'Primeiro-Sargento', 'Subtenente', 'Tenente', 'Capitão', 'Major', 'Coronel', 'General']
    for posto in postos:
        padrao = rf'{posto}\s+([A-Z][a-záéíóú]+)'
        matches = re.findall(padrao, texto)
        for nome in matches:
            entidades['postos'].append(posto)
            entidades['nomes'].append(f'{posto} {nome}')
    dias_semana = re.findall(r'(segunda|terça|quarta|quinta|sexta|sábado|domingo)(?:-feira)?', texto, re.IGNORECASE)
    entidades['datas'].extend(dias_semana)
    datas_num = re.findall(r'dia\s+(\d{1,2}(?:\s+de\s+\w+)?)', texto, re.IGNORECASE)
    entidades['datas'].extend(datas_num)
    unidades = re.findall(r'\d+[ºª]\s*\w+', texto)
    entidades['unidades'].extend(unidades)
    return entidades

def classificar_intencao(texto):
    texto_lower = texto.lower()
    intencoes = {'TROCA_SERVICO': ['trocar', 'troca', 'permuta', 'permutar', 'substituir', 'substituição'], 'CONSULTA_ESCALA': ['consultar', 'consulta', 'ver', 'qual', 'quando', 'horário', 'escala', 'minha escala'], 'RECLAMACAO': ['absurdo', 'injusto', 'insatisfeito', 'reclamar', 'reclamação', 'problema', 'errado'], 'CONFIRMACAO': ['confirmo', 'confirmar', 'presente', 'estarei', 'ok', 'ciente', 'afirmativo'], 'SAUDACAO': ['bom dia', 'boa tarde', 'boa noite', 'olá', 'oi']}
    scores = {}
    for intencao, palavras in intencoes.items():
        score = sum(1 for p in palavras if p in texto_lower)
        if score > 0:
            scores[intencao] = score
    if scores:
        return max(scores, key=scores.get)
    return 'NAO_IDENTIFICADO'

def gerar_resposta(intencao, entidades, sentimento):
    respostas = {'TROCA_SERVICO': 'Pedido de troca registrado. Vou verificar a disponibilidade e retorno em breve.', 'CONSULTA_ESCALA': 'Consultando a escala de serviço... Sua próxima escala está prevista para os dias indicados no quadro de serviço.', 'RECLAMACAO': 'Sua reclamação foi registrada e será encaminhada ao responsável pela escala para análise.', 'CONFIRMACAO': 'Presença confirmada com sucesso. Obrigado pela confirmação.', 'SAUDACAO': 'Bom dia! Sou o assistente de escala de serviço. Como posso ajudar?', 'NAO_IDENTIFICADO': 'Não entendi sua solicitação. Pode reformular? Posso ajudar com consultas, trocas e confirmações de escala.'}
    resposta = respostas.get(intencao, respostas['NAO_IDENTIFICADO'])
    if entidades['nomes']:
        resposta += f'\n Militar(es) envolvido(s): {", ".join(entidades["nomes"])}'
    if entidades['datas']:
        resposta += f'\n Data(s) mencionada(s): {", ".join(entidades["datas"])}'
    if entidades['unidades']:
        resposta += f'\n Unidade: {", ".join(entidades["unidades"])}'
    if sentimento == "negativo":
        resposta += "\n Detectei insatisfação - priorizando atendimento"
    return resposta

def assistente_escala(pergunta):
    score = sia.polarity_scores(pergunta)
    if score['compound'] >= 0.05:
        sentimento = 'positivo'
    elif score['compound'] <= -0.05:
        sentimento = 'negativo'
    else:
        sentimento = 'neutro'
    entidades = extrair_entidades_militar(pergunta)
    intencao = classificar_intencao(pergunta)
    return gerar_resposta(intencao, entidades, sentimento)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    mensagem = request.json["mensagem"]
    resposta = assistente_escala(mensagem)
    return jsonify({"resposta": resposta})

if __name__ == "__main__":
    app.run()
