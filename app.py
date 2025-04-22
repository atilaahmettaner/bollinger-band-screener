from flask import Flask, render_template, request, jsonify
from tradingview_ta import TA_Handler, get_multiple_analysis
import os
from dotenv import load_dotenv

load_dotenv()  # .env dosyasını yükle

# API_KEY'i .env dosyasından al
API_KEY = os.getenv('API_KEY')

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

@app.route('/trending', methods=['POST'])
def trending_coins():
    element.clear()
    line_list.clear()
    
    timeframe = request.form.get("timeframe", "5m")
    exchange = request.form.get("exchange", "kucoin")  # Default to kucoin
    filter_type = request.form.get("filter_type", "")  # Can be "rating" or empty
    rating_filter = request.form.get("rating", "")  # BB rating to filter by
    
    # Ensure exchange is kucoin
    exchange = "kucoin"
    
    exchange_file = os.path.join(file_dir, f"{exchange}.txt")
    with open(exchange_file) as file:
        lines = file.read()
        line = lines.split('\n')
    
    screener = "crypto"  # Default to crypto for trending coins
    
    # Get analysis for all coins in the specified timeframe
    analysis = get_multiple_analysis(screener=screener, interval=timeframe, symbols=line)
    
    # Sort by price change (gains)
    coin_changes = []
    
    for key, value in analysis.items():
        try:
            if value is not None:
                open_price = value.indicators["open"]
                close = value.indicators["close"]
                change = ((close-open_price)/open_price)*100
                
                # Calculate BBW
                sma = value.indicators["SMA20"]
                bb_upper = value.indicators["BB.upper"]
                bb_lower = value.indicators["BB.lower"]
                bb_middle = sma
                BBW = (bb_upper - bb_lower) / sma
                
                # Calculate BB rating
                rating = 0
                if close > bb_upper:
                    rating = 3
                elif close > bb_middle + ((bb_upper - bb_middle) / 2):
                    rating = 2
                elif close > bb_middle:
                    rating = 1
                elif close < bb_lower:
                    rating = -3
                elif close < bb_middle - ((bb_middle - bb_lower) / 2):
                    rating = -2
                elif close < bb_middle:
                    rating = -1
                    
                signal = "NEUTRAL"
                if rating == 2:
                    signal = "BUY"
                elif rating == -2:
                    signal = "SELL"
                
                # Check if we need to filter by BB rating
                if filter_type == "rating" and rating_filter and int(rating_filter) != rating:
                    continue
                
                coin_changes.append({
                    'key': key,
                    'price': round(close, 4),
                    'change': round(change, 3),
                    'bbw': round(BBW, 4),
                    'rating': rating,
                    'signal': signal
                })
        except (TypeError, ZeroDivisionError):
            continue
    
    # Sort by change value (descending) if not filtering by rating
    # Otherwise, no need to sort as we're already filtering for specific rating
    if filter_type != "rating":
        sorted_coins = sorted(coin_changes, key=lambda x: x['change'], reverse=True)
    else:
        sorted_coins = coin_changes
    
    # Take top 50 coins
    top_coins = sorted_coins[:50]
    
    # Format for template
    for coin in top_coins:
        element[coin['key']] = [coin['price'], coin['bbw'], coin['change'], coin['rating'], coin['signal']]
    
    # Create a page title that reflects the operation
    page_title = ""
    if filter_type == "rating":
        rating_value = int(rating_filter)
        if rating_value == 3:
            page_title = "Strong Buy (+3)"
        elif rating_value == 2:
            page_title = "Buy (+2)"
        elif rating_value == 1:
            page_title = "Weak Buy (+1)"
        elif rating_value == -1:
            page_title = "Weak Sell (-1)"
        elif rating_value == -2:
            page_title = "Sell (-2)"
        elif rating_value == -3:
            page_title = "Strong Sell (-3)"
    else:
        page_title = "Top Gainers"
    
    line_list.append(element)
    return render_template('data.html', line_list=line_list, hours=timeframe, line_list1=line_list1, element=element, 
                          filter_type=filter_type, rating_filter=rating_filter, page_title=page_title)

@app.route('/list', methods=['GET', 'POST'])
def scan():
    element.clear()
    line_list.clear()
    hours = request.form.get("times")
    bbw = request.form['bbw']
    exchange = request.form['exchange']
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
                sma = value.indicators["SMA20"]
                bb_upper = value.indicators["BB.upper"]
                bb_lower = value.indicators["BB.lower"]
                bb_middle = sma
                bb_upper_1 = bb_middle + ((bb_upper - bb_middle) / 2)
                bb_lower_1 = bb_middle - ((bb_middle - bb_lower) / 2)
                BBW = (bb_upper - bb_lower) / sma
                rating = 0
                if close > bb_upper:
                    rating = 3
                elif close > bb_upper_1:
                    rating = 2
                elif close > bb_middle:
                    rating = 1
                elif close < bb_lower:
                    rating = -3
                elif close < bb_lower_1:
                    rating = -2
                elif close < bb_middle:
                    rating = -1
                signal = "NEUTRAL"
                if rating == 2:
                    signal = "BUY"
                elif rating == -2:
                    signal = "SELL"

                conditions = (
                    1 > BBW and BBW < float(bbw)
                )
                
                if BBW and value.indicators["EMA50"] and value.indicators["RSI"]:
                    if (conditions):
                        currency = key.split(":")
                        price = round(close, 4)
                        BBW = round(BBW, 4)
                        change = round(change, 3)
                        element[key] = [price, BBW, change, rating, signal]
                        
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

def check_auth_header(request):
    auth_header = request.headers.get('Authorization') 
    if auth_header == API_KEY:
        return True
    return False


@app.errorhandler(404)
def pageNotFound(error):
    return render_template('error.html')

@app.route('/api/scan', methods=['POST'])
def scan_api():
    try:
        request_data = request.json
        hours = request_data.get('hours', '4h')  # Default 4h
        bbw = request_data.get('bbw', '0.04')   # Default 0.04
        exchange = request_data.get('exchange', 'kucoin')  # Default binance
        
        if not check_auth_header(request):
            return jsonify({'error': 'Unauthorized access'}), 401

        element.clear()
        line_list.clear()
        
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
            "nasdaq": "america"
        }
        
        screener = exchange_screener_mapping.get(stripexchange, "crypto")
        analysis = get_multiple_analysis(screener=screener, interval=striphours, symbols=line)
        
        result = []
        
        for key, value in analysis.items():
            try:
                if value is not None:
                    open_price = value.indicators["open"]
                    close = value.indicators["close"]
                    change = ((close-open_price)/open_price)*100
                    sma = value.indicators["SMA20"]
                    bb_upper = value.indicators["BB.upper"]
                    bb_lower = value.indicators["BB.lower"]
                    bb_middle = sma
                    BBW = (bb_upper - bb_lower) / sma
                    
                    if BBW and value.indicators["EMA50"] and value.indicators["RSI"]:
                        if 1 > BBW and BBW < float(bbw):
                            result.append({
                                "symbol": key,
                                "price": round(close, 4),
                                "bbw": round(BBW, 4),
                                "change": round(change, 3),
                                "rsi": value.indicators["RSI"],
                                "volume": value.indicators["volume"]
                            })
                            
            except (TypeError, ZeroDivisionError) as e:
                continue
                
        return jsonify({
            "status": "success",
            "timeframe": hours,
            "exchange": exchange,
            "data": result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/favorites', methods=['GET'])
def favorites():
    return render_template('favorites.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))