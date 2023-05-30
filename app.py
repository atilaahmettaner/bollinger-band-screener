from flask import Flask, render_template, request
from tradingview_ta import *
import os
with open('KUCOIN_BINANCE_HUOBI.txt') as f:
    lines = f.read()
    line = lines.split('\n')
app = Flask(__name__)

class Crypto:
    def __init__(self, coinName, bbw_value, rsi_value):
        self.coinName = coinName
        self.bbw_value = bbw_value
        self.rsi_value = rsi_value


line_list = []
line_list1 = []
data = {}
element = {}
element.clear()
line_list.clear()

@app.route('/', methods=['GET', 'POST'])
def hours_store():
    return render_template('index.html', Hourss=["5m", "15m", "1h", "4h", "1D", "1W", "1M"])


@app.route('/list', methods=['GET', 'POST'])
def scan():
    element.clear()
    line_list.clear()
    hours = request.form.get("saatler")
    bbw = request.form['bbw']
    striphours = hours.strip()

    analysis = get_multiple_analysis(screener="crypto", interval=striphours, symbols=line)
    for key, value in analysis.items():
        try:
            if value != None:
                open = value.indicators["open"]
                close = value.indicators["close"]

                change = ((close-open)/open)*100
                print(change)
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
                        1 > BBW and BBW < float(bbw)
                )
                if BBW and ema50 and rsi:
                    if (conditions):
                        currency = key.split(":")
                        price = round(close, 4)
                        BBW = round(BBW, 4)
                        change = round(change, 3)
                        element[key] = [price, BBW, change]
        except (TypeError):
            print(key ," is not defined ")
        except (ZeroDivisionError):
            print(key," bbw value the is zero")
    line_list.append(element)

    return render_template('data.html', line_list=line_list, hours=hours, line_list1=line_list1, element=element)


@app.errorhandler(404)
def pageNotFound(error):
    return render_template('error.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))