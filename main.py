import os
from dotenv import load_dotenv
from trade_bot import TradeBot

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

if not API_KEY or not API_SECRET:
    raise ValueError("⚠️ API_KEY ou API_SECRET não foram encontradas! Verifique seu arquivo .env.")

# Inicializa o bot e executa a estratégia
bot = TradeBot(API_KEY, API_SECRET)
bot.executar_estrategia()
