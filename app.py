from flask import Flask, render_template, request, jsonify
from tradingview_ta import *
import os

app = Flask(__name__)
file_dir='coinlist'

line_list = []
line_list1 = []
data = {}
element = {}
element.clear()
line_list.clear()

@app.route('/', methods=['GET', 'POST'])
def hours_store():
    return render_template('index.html', Hourss=["4h","5m" ,"15m", "1h" , "1D", "1W", "1M"])


@app.route('/list', methods=['GET', 'POST'])
def scan():
    element.clear()
    line_list.clear()
    hours = request.form.get("times")
    bbw = request.form['bbw']
    exchange= request.form['exchange']
    striphours = hours.strip()
    stripexchange = exchange.strip()
    exchange_file = os.path.join(file_dir, f"{stripexchange}.txt")
    with open(exchange_file) as file:
        lines = file.read()
        line = lines.split('\n')
        exchange_screener_mapping = {
        "all": "crypto",
        "huobi": "crypto",
        "kucoin": "crypto",
        "coinbase": "crypto",
        "gateio": "crypto",
        "binance": "crypto",
        "bitfinex": "crypto",
        "bybit": "crypto",
        "okx": "crypto",
        "bist": "turkey",
        "nasdaq": "america",
          }
    screener = exchange_screener_mapping.get(stripexchange, "crypto")

    analysis = get_multiple_analysis(screener=screener, interval=striphours, symbols=line)
    for key, value in analysis.items():
        try:
            if value != None:
                open_price = value.indicators["open"]
                close = value.indicators["close"]

                change = ((close-open_price)/open_price)*100
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


@app.route('/getPrice', methods=['POST'])
def handle_list_request():
    request_data = request.json
    hours = request_data.get('hours')
    symbol = request_data.get('symbol')
    exchange = request_data.get('exchange')
    scanForApi(hours, symbol, exchange)
    return jsonify(element)




def scanForApi(hours, symbol, exchange):
    element.clear()
    striphours = hours.strip()
    symbol_with_exchange = f"{exchange}:{symbol}"
    if exchange == "kucoin":
        analysis = get_multiple_analysis(screener="crypto", interval=striphours, symbols=[symbol_with_exchange])
    elif exchange == "bist":
        analysis = get_multiple_analysis(screener="turkey", interval=striphours, symbols=[symbol_with_exchange])
    elif exchange == "nasdaq":
        analysis = get_multiple_analysis(screener="america", interval=striphours, symbols=[symbol_with_exchange])
    for key, value in analysis.items():
        try:
            if value is not None:
                open_price = value.indicators["open"]
                close = value.indicators["close"]
                change = ((close - open_price) / open_price) * 100
                price = round(close, 4)
                change = round(change, 3)
                element["name"] = key
                element["current"] = price
                element["change"] = change
                element["open"] = open_price
                element["close"] = close

        except TypeError:
            print(key, " is not defined ")


API_KEY = "c29d28e35cd02672bd295c4c5f52eccb"
def check_auth_header(request):
    auth_header = request.headers.get('Authorization')
    if auth_header==API_KEY:
        return True
    return False

@app.before_request
def before_request():
    if request.endpoint != 'handle_list_request':
        return
    if not check_auth_header(request):
        return jsonify({'error': 'Unauthorized access'}), 401



@app.errorhandler(404)
def pageNotFound(error):
    return render_template('error.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))