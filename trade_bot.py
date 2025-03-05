import time
import pandas as pd
from binance.client import Client
from datetime import datetime
import os

class TradeBot:
    def __init__(self, api_key, api_secret, quantidade_btc=0.0003, log_file="trades.log"):
        self.client = Client(api_key, api_secret)
        self.quantidade_btc = quantidade_btc
        self.log_file = log_file
        self.comprado = False
        self.aguardando_primeira_entrada = True
        self.sma7 = 0
        self.sma28 = 0
        self.preco_atual = 0
        self.preco_compra = 0  # Armazena o preço da última compra
        self.taxa_compra = 0

    def obter_precos_historicos(self, symbol="BTCBRL", intervalo="1m", limite=28):
        candles = self.client.get_historical_klines(symbol, intervalo, limit=limite)
        return [float(candle[4]) for candle in candles]
    
    def obter_preco_atual(self, symbol="BTCBRL"):
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])
    
    def calcular_sma(self, precos, periodo):
        return sum(precos[-periodo:]) / periodo
    
    def registrar_log(self, tipo, preco, quantidade, preco_venda=None, quantidade_venda=None, taxa_venda=0):
        with open(self.log_file, "a") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_msg = f"{timestamp} - {tipo} - Preço: {preco} BRL - Quantidade: {quantidade} BTC"
            if preco_venda:
                valor_entrada = preco * quantidade
                valor_venda = preco_venda * quantidade_venda
                taxa_total = self.taxa_compra + taxa_venda
                lucro_bruto = valor_venda - valor_entrada
                lucro_liquido = lucro_bruto - taxa_total
                log_msg += f" - Venda: {preco_venda} BRL - Quantidade: {quantidade_venda} BTC - Taxa: {taxa_total} BRL - Lucro Bruto: {lucro_bruto} BRL - Lucro Líquido: {lucro_liquido} BRL"
            f.write(log_msg + "\n")
        print(f"📜 {tipo} registrado no log.")
    
    def comprar(self):
        try:
            ordem = self.client.order_market_buy(symbol="BTCBRL", quantity="{:.8f}".format(self.quantidade_btc))
            self.preco_compra = float(ordem['fills'][0]['price'])
            quantidade_fechamento = float(ordem['fills'][0]['qty'])
            self.taxa_compra = float(ordem['fills'][0]['commission'])
            print(f"💰 COMPRADO! {quantidade_fechamento} BTC a {self.preco_compra} BRL")
            self.registrar_log("COMPRA", self.preco_compra, quantidade_fechamento)
            self.comprado = True
            print("⏳ Aguardando 3 minutos antes da próxima operação...")
            time.sleep(180)  # Aguarda 3 minutos
        except Exception as e:
            print(f"❌ Erro ao comprar: {e}")
    
    def vender(self):
        try:
            ordem = self.client.order_market_sell(symbol="BTCBRL", quantity="{:.8f}".format(self.quantidade_btc))
            preco_venda = float(ordem['fills'][0]['price'])
            quantidade_fechamento = float(ordem['fills'][0]['qty'])
            taxa_venda = float(ordem['fills'][0]['commission'])
            print(f"📉 VENDIDO! {quantidade_fechamento} BTC a {preco_venda} BRL")
            self.registrar_log("VENDA", self.preco_compra, self.quantidade_btc, preco_venda, quantidade_fechamento, taxa_venda)
            self.comprado = False
            print("⏳ Aguardando 3 minutos antes da próxima operação...")
            time.sleep(180)  # Aguarda 3 minutos
            self.aguardando_primeira_entrada = True # depois da venda, esperar sinal novamente
        except Exception as e:
            print(f"❌ Erro ao vender: {e}")
    
    def executar_estrategia(self):
        while True:
            precos_historicos = self.obter_precos_historicos(limite=28)
            self.preco_atual = self.obter_preco_atual()
            precos_historicos.append(self.preco_atual)
            self.sma7 = self.calcular_sma(precos_historicos, 7)
            self.sma28 = self.calcular_sma(precos_historicos, 28)
            
            if self.aguardando_primeira_entrada:
                if self.sma7 > self.sma28:
                    print(f"⏳ Aguardando a SMA7 ficar abaixo da SMA28 antes de iniciar...")
                else:
                    print(f"✅ Podemos operar agora...")
                    self.aguardando_primeira_entrada = False
            else:
                if self.sma7 > self.sma28 and not self.comprado:
                    self.comprar()
                elif self.sma7 < self.sma28 and self.comprado:
                    variacao = (self.preco_atual - self.preco_compra) / self.preco_compra
                    print(f"🔍 Variação calculada: {variacao * 100:.4f}%")
                    print(f"🔍 Preço de compra: {self.preco_compra} | Preço atual: {self.preco_atual}")
                    if abs(variacao) > 0.001:  # Agora vende tanto se a variação for positiva quanto negativa
                        self.vender()
            
            print(f"💰 Preço Atual: {self.preco_atual} BRL | SMA7: {self.sma7}, SMA28: {self.sma28}")
            time.sleep(1)
