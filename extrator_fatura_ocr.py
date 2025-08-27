import os
import pandas as pd
import pytesseract
from pdf2image import convert_from_path
import google.generativeai as genai
from PIL import Image
import json

# --- CONFIGURAÇÃO INICIAL (AJUSTE ESTES VALORES) ---

# 1. Para usuários de Windows, ajuste o caminho para o executável do Tesseract.
#    Verifique se o caminho está correto para a sua instalação.
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 2. Cole sua chave de API do Google AI Studio (Gemini) aqui.
#    Crie a sua gratuitamente em: https://aistudio.google.com/
GOOGLE_API_KEY = 'SUA_CHAVE_API' # SUBSTITUA PELA SUA CHAVE REAL
genai.configure(api_key=GOOGLE_API_KEY)

# 3. Defina o nome do arquivo PDF que você quer processar.
NOME_ARQUIVO_PDF = 'nome_do_arquivo.pdf'

# 4. Para usuários de Windows, ajuste o caminho para a pasta 'bin' do Poppler.
#    Verifique se o caminho está correto para a sua instalação.
CAMINHO_POPPLER = r"C:\poppler-25.07.0\Library\bin" # Ajuste o caminho se necessário

# --- FIM DA CONFIGURAÇÃO ---


# >>> ALTERAÇÃO 1: O nome da função e o prompt foram ajustados para refletir o processamento do documento inteiro.
def extrair_transacoes_de_texto_completo_com_ia(texto_documento):
    """Envia o texto do DOCUMENTO INTEIRO para a IA e pede a estruturação dos dados."""
    print("   - Enviando texto completo do documento para a IA...")
    
    # Modelo generativo do Gemini
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    # Configuração de segurança para ser menos restritiva
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    # >>> ALTERAÇÃO 2: O prompt foi atualizado para instruir a IA a analisar o documento inteiro.
    prompt = """
    Você é um assistente especialista em finanças. Analise o texto completo de uma fatura de cartão de crédito a seguir, que pode conter várias páginas.
    Sua tarefa é extrair TODAS as transações de compra, crédito ou pagamento listadas NESTE DOCUMENTO.
    
    Ignore subtotais, resumos de fatura e informações que não sejam transações individuais. Se não houver transações no documento, retorne uma lista vazia.
    Observações: os valores da coluna "ultimos_4_digitos_cartao" devem ser os 4 últimos dígitos do cartão. Considere que quando um número de cartão é informado, ele deve ser aplicado em todas as transações subsequentes até que um novo número de cartão seja informado, mesmo através das páginas. Não deixe um campo de "ultimos_4_digitos_cartao" vazio.
    Use valores negativos para despesas e pagamentos, e valores positivos para créditos ou estornos.
    
    Retorne os dados EXCLUSIVAMENTE em formato JSON, como uma lista de objetos, seguindo este modelo:
    [
      {
        "data": "DD/MM/AAAA",
        "descricao": "Nome do estabelecimento ou da transação",
        "ultimos_4_digitos_cartao": "'1234'",
        "parcela_atual": 1,
        "parcela_total": 1,
        "valor_rs": -123.45
      }
    ]
    
    Texto do documento para análise:
    """ + texto_documento
    
    try:
        response = model.generate_content(
            prompt, 
            safety_settings=safety_settings
        )
        
        # Limpa a resposta para garantir que seja um JSON válido
        json_response_text = response.text.strip().replace('```json', '').replace('```', '')
        
        # Converte o texto JSON em uma lista de dicionários Python
        return json.loads(json_response_text)
        
    except Exception as e:
        print(f"   - Erro ao chamar a API ou processar o JSON: {e}")
        return [] # Retorna uma lista vazia em caso de erro

# --- FUNÇÃO PRINCIPAL DE EXECUÇÃO ---
if __name__ == "__main__":
    if 'SUA_CHAVE_API_AQUI' in GOOGLE_API_KEY:
        print("ERRO: Por favor, configure sua GOOGLE_API_KEY na seção de configuração no início do script.")
    elif not os.path.exists(NOME_ARQUIVO_PDF):
        print(f"ERRO: Arquivo PDF '{NOME_ARQUIVO_PDF}' não encontrado. Verifique o nome e o local do arquivo.")
    else:
        print(f"Iniciando processamento do arquivo: {NOME_ARQUIVO_PDF}")
        
        try:
            # Converte todas as páginas do PDF em uma lista de imagens
            imagens = convert_from_path(NOME_ARQUIVO_PDF, poppler_path=CAMINHO_POPPLER)
            
            texto_completo_do_pdf = ""

            # Itera sobre cada imagem (página) para extrair e concatenar o texto
            print("Iniciando extração de texto OCR de todas as páginas...")
            for i, imagem in enumerate(imagens):
                print(f"   - Processando Página {i+1} de {len(imagens)}...")
                texto_da_pagina = pytesseract.image_to_string(imagem, lang='por')
                
                # Adiciona um marcador de página para dar contexto à IA
                texto_completo_do_pdf += f"\n\n--- INÍCIO DA PÁGINA {i+1} ---\n\n"
                texto_completo_do_pdf += texto_da_pagina
            
            print("Extração de texto OCR concluída.")

            todas_as_transacoes = []
            if texto_completo_do_pdf.strip():
                todas_as_transacoes = extrair_transacoes_de_texto_completo_com_ia(texto_completo_do_pdf)
            else:
                print("Nenhum texto foi extraído do documento via OCR.")

            # Após processar o documento inteiro, cria o DataFrame final
            if todas_as_transacoes:
                # Opcional: imprime o número de transações encontradas no documento inteiro
                print(f"\nAnálise da IA concluída. {len(todas_as_transacoes)} transações encontradas no documento.")
                
                df = pd.DataFrame(todas_as_transacoes)
                
                nome_arquivo_csv = 'fatura_final.csv'
                df.to_csv(nome_arquivo_csv, index=False, sep=';', decimal=',', encoding='utf-8-sig')
                
                print(f"\nSUCESSO! Planilha '{nome_arquivo_csv}' criada com um total de {len(df)} transações.")
            else:
                print("\nProcessamento concluído, mas nenhuma transação foi extraída do documento.")

        except Exception as e:
            print(f"\nOcorreu um erro crítico durante o processamento do PDF: {e}")
            print("Verifique os caminhos do Poppler e Tesseract, e se o arquivo PDF não está corrompido.")