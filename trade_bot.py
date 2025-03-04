import time
import pandas as pd
from binance.client import Client
from datetime import datetime
import os

class TradeBot:
    def __init__(self, api_key, api_secret, quantidade_btc=0.00003, log_file="trades.log"):
        self.client = Client(api_key, api_secret)
        self.quantidade_btc = quantidade_btc
        self.log_file = log_file
        self.comprado = False  # Controle se estamos comprados
        self.aguardando_primeira_entrada = True  # Garante que a primeira entrada seja feita no momento correto
        self.sma7 = 0
        self.sma28 = 0
        self.preco_atual = 0

    def obter_precos_historicos(self, symbol="BTCBRL", intervalo="1m", limite=28):
        """Obtém preços históricos de candles (1m) para calcular as médias móveis"""
        candles = self.client.get_historical_klines(symbol, intervalo, limit=limite)
        precos = [float(candle[4]) for candle in candles]  # Preço de fechamento de cada candle
        return precos

    def obter_preco_atual(self, symbol="BTCBRL"):
        """Obtém o preço atual do BTC/BRL"""
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])

    def calcular_sma(self, precos, periodo):
        """Calcula a média móvel simples (SMA)"""
        return sum(precos[-periodo:]) / periodo

    def registrar_log(self, tipo, preco, quantidade, comissao=None, comissao_asset=None):
        with open(self.log_file, "a") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_msg = f"{timestamp} - {tipo} - Preço: {preco} BRL - Quantidade: {quantidade} BTC"
            if comissao:
                log_msg += f" - Comissão: {comissao} {comissao_asset}"
            f.write(log_msg + "\n")
        print(f"📜 {tipo} registrado no log.")

    def comprar(self):
        """Executa uma compra de mercado."""
        try:
            ordem = self.client.order_market_buy(symbol="BTCBRL", quantity="{:.8f}".format(self.quantidade_btc))
            preco_fechamento = float(ordem['fills'][0]['price'])
            quantidade_fechamento = float(ordem['fills'][0]['qty'])
            comissao = float(ordem['fills'][0]['commission'])
            comissao_asset = ordem['fills'][0]['commissionAsset']

            # Se a comissão não for em BRL, converte para BRL
            if comissao_asset != "BRL":
                preco_atual = self.obter_preco_atual()
                comissao = comissao * preco_atual  # Converte a comissão para BRL

            print(f"💰 COMPRADO! {quantidade_fechamento} BTC a {preco_fechamento} BRL")
            self.registrar_log("COMPRA", preco_fechamento, quantidade_fechamento, comissao, comissao_asset)
            self.comprado = True

            # Aguarda 2 minutos antes de operar novamente
            print("⏳ Aguardando 2 minutos antes da próxima operação...")
            time.sleep(120)

        except Exception as e:
            print(f"❌ Erro ao comprar: {e}")

    def vender(self):
        """Executa uma venda de mercado."""
        try:
            ordem = self.client.order_market_sell(symbol="BTCBRL", quantity="{:.8f}".format(self.quantidade_btc))
            preco_fechamento = float(ordem['fills'][0]['price'])
            quantidade_fechamento = float(ordem['fills'][0]['qty'])
            comissao = float(ordem['fills'][0]['commission'])
            comissao_asset = ordem['fills'][0]['commissionAsset']

            # Se a comissão não for em BRL, converte para BRL
            if comissao_asset != "BRL":
                preco_atual = self.obter_preco_atual()
                comissao = comissao * preco_atual  # Converte a comissão para BRL

            print(f"📉 VENDIDO! {quantidade_fechamento} BTC a {preco_fechamento} BRL")
            self.registrar_log("VENDA", preco_fechamento, quantidade_fechamento, comissao, comissao_asset)
            self.comprado = False

            # Aguarda 2 minutos antes de operar novamente
            print("⏳ Aguardando 2 minutos antes da próxima operação...")
            time.sleep(120)

        except Exception as e:
            print(f"❌ Erro ao vender: {e}")

    def executar_estrategia(self):
        """Executa a estratégia de trade baseada nas médias móveis."""
        while True:
            # Obtém os preços históricos
            precos_historicos = self.obter_precos_historicos(limite=28)  # Pegamos 28 candles (1 minuto cada)
            
            # Obtém o preço atual
            self.preco_atual = self.obter_preco_atual()

            # Adiciona o preço atual à lista de históricos antes de calcular as médias
            precos_historicos.append(self.preco_atual)

            # Calcula as médias móveis considerando o preço atual
            self.sma7 = self.calcular_sma(precos_historicos, 7)
            self.sma28 = self.calcular_sma(precos_historicos, 28)

            # Regra para a primeira compra: só comprar quando a SMA7 cruzar a SMA28 para cima
            if self.aguardando_primeira_entrada:
                if self.sma7 > self.sma28:
                    print(f"⏳ Aguardando a SMA7 ficar abaixo da SMA28 antes de iniciar as operações... | Preço Atual: {self.preco_atual} BRL")
                else:
                    print(f"✅ Agora sim podemos operar... | Preço Atual: {self.preco_atual} BRL")
                    self.aguardando_primeira_entrada = False  # Agora ele pode operar normalmente

            else:
                # Operação normal após o primeiro cruzamento
                if self.sma7 > self.sma28 and not self.comprado:
                    self.comprar()
                elif self.sma7 < self.sma28 and self.comprado:
                    self.vender()

            print(f"💰 Preço Atual: {self.preco_atual} BRL | SMA7: {self.sma7}, SMA28: {self.sma28}")
            time.sleep(1)  # Espera 1 segundo antes de verificar novamente