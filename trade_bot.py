import time
import pandas as pd
from binance.client import Client
from datetime import datetime
import os

class TradeBot:
    def __init__(self, api_key, api_secret, quantidade_btc=0.00003, log_file="trades.xlsx"):
        self.client = Client(api_key, api_secret)
        self.quantidade_btc = quantidade_btc
        self.log_file = log_file
        self.comprado = False
        self.aguardando_primeira_entrada = True
        self.sma7 = 0
        self.sma28 = 0
        self.preco_atual = 0
        self.preco_compra = 0  # Armazena o preço da última compra
        self._verificar_ou_criar_planilha()
    
    def _verificar_ou_criar_planilha(self):
        if not os.path.exists(self.log_file):
            df = pd.DataFrame(columns=[
                "Compra", "Quantidade Compra", "Valor Entrada",
                "Venda", "Quantidade Venda", "Valor Venda",
                "Taxa Total", "Lucro Bruto", "Lucro Líquido"
            ])
            df.to_excel(self.log_file, index=False)
    
    def obter_precos_historicos(self, symbol="BTCBRL", intervalo="1m", limite=28):
        candles = self.client.get_historical_klines(symbol, intervalo, limit=limite)
        return [float(candle[4]) for candle in candles]
    
    def obter_preco_atual(self, symbol="BTCBRL"):
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])
    
    def calcular_sma(self, precos, periodo):
        return sum(precos[-periodo:]) / periodo
    
    def registrar_log_excel(self, preco_compra, quantidade_compra, preco_venda=None, quantidade_venda=None):
        df = pd.read_excel(self.log_file)
        valor_entrada = preco_compra * quantidade_compra
        valor_venda = preco_venda * quantidade_venda if preco_venda else None
        taxa_total = (preco_compra + (preco_venda if preco_venda else 0)) * 0.001 if preco_venda else None
        lucro_bruto = valor_venda - valor_entrada if preco_venda else None
        lucro_liquido = lucro_bruto - taxa_total if preco_venda else None

        nova_linha = {
            "Compra": preco_compra,
            "Quantidade Compra": quantidade_compra,
            "Valor Entrada": valor_entrada,
            "Venda": preco_venda,
            "Quantidade Venda": quantidade_venda,
            "Valor Venda": valor_venda,
            "Taxa Total": taxa_total,
            "Lucro Bruto": lucro_bruto,
            "Lucro Líquido": lucro_liquido
        }
        df = df.append(nova_linha, ignore_index=True)
        df.to_excel(self.log_file, index=False)
    
    def comprar(self):
        try:
            ordem = self.client.order_market_buy(symbol="BTCBRL", quantity="{:.8f}".format(self.quantidade_btc))
            self.preco_compra = float(ordem['fills'][0]['price'])
            quantidade_fechamento = float(ordem['fills'][0]['qty'])
            print(f"💰 COMPRADO! {quantidade_fechamento} BTC a {self.preco_compra} BRL")
            self.registrar_log_excel(self.preco_compra, quantidade_fechamento)
            self.comprado = True
            time.sleep(120)
        except Exception as e:
            print(f"❌ Erro ao comprar: {e}")
    
    def vender(self):
        try:
            ordem = self.client.order_market_sell(symbol="BTCBRL", quantity="{:.8f}".format(self.quantidade_btc))
            preco_venda = float(ordem['fills'][0]['price'])
            quantidade_fechamento = float(ordem['fills'][0]['qty'])
            print(f"📉 VENDIDO! {quantidade_fechamento} BTC a {preco_venda} BRL")
            self.registrar_log_excel(self.preco_compra, self.quantidade_btc, preco_venda, quantidade_fechamento)
            self.comprado = False
            time.sleep(120)
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
                    variacao = abs((self.preco_atual - self.preco_compra) / self.preco_compra)
                    if variacao >= 0.001:
                        self.vender()
            
            print(f"💰 Preço Atual: {self.preco_atual} BRL | SMA7: {self.sma7}, SMA28: {self.sma28}")
            time.sleep(1)
