from bs4 import element
from flask import Flask, render_template, request
from tradingview_ta import *

with open('KUCOIN_BINANCE_HUOBI.txt') as f:
    lines = f.read()
    line = lines.split('\n')
app = Flask(__name__)
line_list =  []
rsi_list = []
element = {}
@app.route('/snapshot')
def snapshot():
    return {
        "code": "success"
    }
@app.route('/', methods=['GET', 'POST'])
def hoursStore():
    return render_template('index.html', Hourss=["15m", "1h", "4h", "1D", "1W", "1M"])
@app.route('/list', methods=['POST', 'GET'])
def Scan():
    dir = {}
    get = request.form.get("saatler")
    hours = get
    bbw = request.form['bbw']
    a = hours.strip()
    print(bbw)
    analysis = get_multiple_analysis(screener="crypto", interval=a, symbols=line)
    for key, value in analysis.items():
        try:
            if value != None:
                open = value.indicators["open"]
                close = value.indicators["close"]
                macd = value.indicators["MACD.macd"]
                rsi = value.indicators["RSI"]
                sma = value.indicators["SMA20"]
                stoch_rsi = value.indicators["Stoch.RSI.K"]
                ema20 = value.indicators["EMA20"]
                ema50 = value.indicators["EMA50"]
                ema200 = value.indicators["EMA200"]
                lower = value.indicators["BB.lower"]
                upper = value.indicators["BB.upper"]
                BBW = (upper - lower) / sma
                conditions = (
                        BBW > (float)(bbw)
                )
                if BBW and ema50 and rsi:
                    if (conditions):
                        currency = key.split(":")
                        exchange = currency[0]
                        coin = currency[1]
                        dir = {
                            exchange: coin,
                        }
                        print("coin ismi: " ,key)
                        print('bolinger band genişliği', BBW)
                        print('----------------------------------------------------------')
                        line_list.append(key)
                        element={key: rsi}
        except (TypeError):
            print(key + " Bu şekilde bir parametre yok")
        except (ZeroDivisionError):
            print(key + " bu coin 0 a bolunuyor")
    return render_template('data.html', line_list=line_list, hours=hours, dir=dir, rsi_list=rsi_list)
@app.errorhandler(404)
def pageNotFound(error):
    return render_template('error.html')

