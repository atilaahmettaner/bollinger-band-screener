from flask import Flask, render_template, request
from tradingview_ta import *

with open('KUCOIN_BINANCE_HUOBI.txt') as f:
    lines = f.read()
    line = lines.split('\n')


app = Flask(__name__)
class crypto:
 def __init__(self,coinName,BBW_value,rsi_value):
    self.coinName =coinName
    self.BBW_value=BBW_value
    self.rsi_value=rsi_value
line_list =[]
line_list1 =[]
data={}
element = {}
@app.route('/', methods=['GET', 'POST'])
def hoursStore():
    return render_template('index.html', Hourss=["15m", "1h", "4h", "1D", "1W", "1M"])
@app.route('/list', methods=['GET', 'POST'])
def Scan():
    dir = {}
    get = request.form.get("saatler")
    hours = get
    bbw = request.form['bbw']
    a = hours.strip()

    analysis = get_multiple_analysis(screener="crypto", interval=a, symbols=line)
    for key, value  in analysis.items():
        try:
            if value != None:
                open = value.indicators["open"]
                close = value.indicators["close"]
                change = value.indicators["change"]
                macd = value.indicators["MACD.macd"]
                rsi = value.indicators["RSI"]
                sma = value.indicators["SMA20"]
                ema20 = value.indicators["EMA20"]
                ema50 = value.indicators["EMA50"]
                ema200 = value.indicators["EMA200"]
                lower = value.indicators["BB.lower"]
                upper = value.indicators["BB.upper"]
                BBW = (upper - lower) / sma
                conditions = (
                        BBW < (float)(bbw)
                )
                if BBW and ema50 and rsi:
                    if (conditions):
                        currency = key.split(":")
                        coin = currency[1]
                        exchange = currency[0]
                        price=round(close,4)
                        BBW=round(BBW,4)
                        change=round(change,3)
                        element[key] = [price, BBW,change ]

        except (TypeError):
            k = 1
        except (ZeroDivisionError):
            k=0
    line_list.append(element)
    print(line_list)
    return render_template('data.html', line_list=line_list, hours=hours, line_list1=line_list1,element=element )

@app.errorhandler(404)
def pageNotFound(error):
    return render_template('error.html')



