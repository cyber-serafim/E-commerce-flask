from datetime import datetime
import time
from binance.client import Client

# Создаём клиент Binance
client = Client()
#
#
from binance.exceptions import BinanceAPIException
from requests.exceptions import ReadTimeout, ConnectionError

def get_tickers_with_cur_price():
    working_symbols = ['ATMUSDT', 'BNBUSDT', 'BTCUSDT', 'ETHUSDT', 'OMNIUSDT',
                       'SOLUSDT', 'POLUSDT', 'TRXUSDT', 'XRPUSDT', 'CFXUSDT',
                       'BIOUSDT', 'WINUSDT' ]

    base_url = "https://www.binance.com/en/trade/"
    working_tickers = []

    while True:
        try:
            tickers = client.get_all_tickers()
            for ticker in tickers:
                symbol = ticker['symbol']
                if symbol.endswith('USDT') or symbol.endswith('USD'):
                    if symbol not in working_symbols:
                        continue
                    price = ticker['price']
                    url = f'static/ticker_images/{symbol.split("USDT")[0]}.png'
                    working_tickers.append([symbol, price, url])
            working_tickers.sort(key=lambda x: x[0])
            break  # успех — выходим из цикла

        except (ReadTimeout, ConnectionError):
            print("🔁 Тайм-аут или соединение сброшено. Повтор через 3 секунды...")
            time.sleep(3)

        except BinanceAPIException as e:
            print(f"❌ Binance API ошибка: {e}. Повтор через 5 секунд...")
            time.sleep(5)

        except Exception as e:
            print(f"⚠️ Неизвестная ошибка: {e}. Повтор через 5 секунд...")
            time.sleep(5)
    #
    print(working_tickers)
    # working_tickers = [['ATMUSDT', '1.74300000', 'static/ticker_images/ATM.png'], 
    #                    ['BNBUSDT', '836.75000000', 'static/ticker_images/BNB.png'], 
    #                    ['BTCUSDT', '118130.34000000', 'static/ticker_images/BTC.png'], 
    #                    ['ETHUSDT', '3803.56000000', 'static/ticker_images/ETH.png'], 
    #                    ['POLUSDT', '0.23030000', 'static/ticker_images/POL.png'], 
    #                    ['SOLUSDT', '186.96000000', 'static/ticker_images/SOL.png'],
    #                    ['TRXUSDT', '0.32420000', 'static/ticker_images/TRX.png'], 
    #                    ['XRPUSDT', '3.16070000', 'none']]

    return working_tickers

