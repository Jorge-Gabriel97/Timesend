import shutil
import os
import time

def limpar_sessao():
    pasta_sessao = "sessao_zap"
    
    if os.path.exists(pasta_sessao):
        print(f"Encontrei a sessão antiga em '{pasta_sessao}'.")
        print("Apagando para solicitar novo QR Code...")
        try:
            # Tenta apagar a pasta e tudo que tem dentro
            shutil.rmtree(pasta_sessao)
            print(" SUCESSO! Sessão limpa.")
            print("Na próxima vez que o robô abrir, ele pedirá o QR Code.")
        except Exception as e:
            print(f" ERRO: Não consegui apagar a pasta. O Chrome está aberto?")
            print(f"Detalhe: {e}")
            print("DICA: Feche todas as janelas do Chrome e tente de novo.")
    else:
        print("ℹ️ Nenhuma sessão encontrada. O robô já vai pedir QR Code na próxima vez.")

if __name__ == "__main__":
    limpar_sessao()
    time.sleep(3)