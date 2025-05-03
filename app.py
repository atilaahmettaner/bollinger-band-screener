from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from tradingview_ta import TA_Handler, get_multiple_analysis
import os
from dotenv import load_dotenv
import json
from models import db, Subscriber
from flask_sqlalchemy import SQLAlchemy
from email_validator import validate_email, EmailNotValidError

load_dotenv()  # .env dosyasını yükle

# API_KEY'i .env dosyasından al
API_KEY = os.getenv('API_KEY')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'developmentsecretkey')

# DATABASE_URL varsa (Heroku), PostgreSQL kullan, yoksa SQLite kullan
if os.environ.get('DATABASE_URL'):
    # Heroku PostgreSQL
    db_url = os.environ.get('DATABASE_URL')
    # PostgreSQL URL formatı için düzeltme (eğer gerekirse)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    # Local SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///subscribers.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

@app.before_request
def redirect_to_custom_domain():
    """Redirect from Heroku domain to the custom domain."""
    heroku_domain = 'crypto-scanner-app.herokuapp.com'
    custom_domain = 'cryptosieve.com'
    
    host = request.host.lower() # Gelen isteğin host adını al (küçük harfe çevir)
    
    if host == heroku_domain:
        # Gelen istek Heroku domain'inden ise, custom domain'e yönlendir
        new_url = request.url.replace(heroku_domain, custom_domain, 1)
        # HTTPS protokolünü zorunlu kıl
        if not new_url.startswith('https://'):
             new_url = new_url.replace('http://', 'https://', 1)
             
        return redirect(new_url, code=301) # 301 Kalıcı Yönlendirme

# Create database tables
with app.app_context():
    db.create_all()

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

@app.route('/api/trending', methods=['GET'])
def trending_api():
    try:
        # API key kontrolü
        if not check_auth_header(request):
            return jsonify({'error': 'Unauthorized access'}), 401
            
        timeframe = request.args.get("timeframe", "5m")
        exchange = request.args.get("exchange", "kucoin")
        filter_type = request.args.get("filter_type", "")
        rating_filter = request.args.get("rating", "")
        
        # Ensure exchange is kucoin
        exchange = "kucoin"
        
        exchange_file = os.path.join(file_dir, f"{exchange}.txt")
        with open(exchange_file) as file:
            lines = file.read()
            line = lines.split('\n')
        
        screener = "crypto"
        
        # Get analysis for all coins
        analysis = get_multiple_analysis(screener=screener, interval=timeframe, symbols=line)
        
        # Process results
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
                        'symbol': key,
                        'price': round(close, 4),
                        'change': round(change, 3),
                        'bbw': round(BBW, 4),
                        'rating': rating,
                        'signal': signal,
                        'volume': value.indicators.get("volume", 0)
                    })
            except (TypeError, ZeroDivisionError):
                continue
        
        # Sort by change value (descending) if not filtering by rating
        if filter_type != "rating":
            sorted_coins = sorted(coin_changes, key=lambda x: x['change'], reverse=True)
        else:
            sorted_coins = coin_changes
        
        # Take top 50 coins
        top_coins = sorted_coins[:50]
        
        return jsonify({
            "status": "success",
            "timeframe": timeframe,
            "exchange": exchange,
            "filter_type": filter_type,
            "rating_filter": rating_filter,
            "data": top_coins
        })
                
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/symbols', methods=['GET'])
def symbols_api():
    try:
        if not check_auth_header(request):
            return jsonify({'error': 'Unauthorized access'}), 401
            
        exchange = request.args.get('exchange', 'kucoin')
        exchange_file = os.path.join(file_dir, f"{exchange}.txt")
        
        try:
            with open(exchange_file) as file:
                lines = file.read()
                symbols = lines.split('\n')
                symbols = [s for s in symbols if s]  # Remove empty strings
                
            return jsonify({
                "status": "success",
                "exchange": exchange,
                "symbols": symbols
            })
        except FileNotFoundError:
            return jsonify({
                "status": "error",
                "message": f"Exchange {exchange} not found"
            }), 404
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/coin-details', methods=['GET'])
def coin_details_api():
    try:
        if not check_auth_header(request):
            return jsonify({'error': 'Unauthorized access'}), 401
            
        symbol = request.args.get('symbol')
        exchange = request.args.get('exchange', 'kucoin')
        timeframe = request.args.get('timeframe', '4h')
        
        if not symbol:
            return jsonify({
                "status": "error",
                "message": "Symbol parameter is required"
            }), 400
            
        symbol_with_exchange = f"{exchange}:{symbol}"
        
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
        
        screener = exchange_screener_mapping.get(exchange, "crypto")
        
        # Get detailed analysis
        analysis = get_multiple_analysis(screener=screener, interval=timeframe, symbols=[symbol_with_exchange])
        
        if symbol_with_exchange not in analysis or analysis[symbol_with_exchange] is None:
            return jsonify({
                "status": "error",
                "message": f"Symbol {symbol} not found or analysis failed"
            }), 404
            
        value = analysis[symbol_with_exchange]
        
        # Extract all indicators
        indicators = value.indicators
        
        # Calculate BB related values
        try:
            open_price = indicators["open"]
            close = indicators["close"]
            change = ((close-open_price)/open_price)*100
            sma = indicators["SMA20"]
            bb_upper = indicators["BB.upper"]
            bb_lower = indicators["BB.lower"]
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
                
            # Prepare detailed response
            coin_data = {
                "symbol": symbol_with_exchange,
                "timeframe": timeframe,
                "price": round(close, 4),
                "open": round(open_price, 4),
                "high": indicators.get("high", 0),
                "low": indicators.get("low", 0),
                "volume": indicators.get("volume", 0),
                "change": round(change, 3),
                "bb_rating": rating,
                "signal": signal,
                "bbwidth": round(BBW, 4),
                "bb_upper": round(bb_upper, 4),
                "bb_middle": round(bb_middle, 4),
                "bb_lower": round(bb_lower, 4),
                "rsi": indicators.get("RSI", 0),
                "ema_50": indicators.get("EMA50", 0),
                "ema_200": indicators.get("EMA200", 0),
                "macd": indicators.get("MACD.macd", 0),
                "macd_signal": indicators.get("MACD.signal", 0),
                "adx": indicators.get("ADX", 0),
                "oscillators": value.oscillators if hasattr(value, "oscillators") else {},
                "moving_averages": value.moving_averages if hasattr(value, "moving_averages") else {}
            }
            
            return jsonify({
                "status": "success",
                "data": coin_data
            })
            
        except (TypeError, ZeroDivisionError, KeyError) as e:
            return jsonify({
                "status": "error",
                "message": f"Error calculating indicators: {str(e)}"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/watchlist', methods=['GET', 'POST', 'DELETE'])
def watchlist_api():
    try:
        if not check_auth_header(request):
            return jsonify({'error': 'Unauthorized access'}), 401
            
        # Burada gerçek bir veritabanı kullanılabilir
        # Örnek olarak bir dosya-tabanlı yaklaşım gösteriyoruz
        user_id = request.args.get('user_id', 'anonymous')
        watchlist_file = os.path.join('data', f'watchlist_{user_id}.json')
        
        # GET: Mevcut favori listesini al
        if request.method == 'GET':
            try:
                if not os.path.exists('data'):
                    os.makedirs('data')
                    
                if os.path.exists(watchlist_file):
                    with open(watchlist_file, 'r') as f:
                        watchlist = json.load(f)
                else:
                    watchlist = []
                    
                return jsonify({
                    "status": "success",
                    "watchlist": watchlist
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Error reading watchlist: {str(e)}"
                }), 500
                
        # POST: Yeni bir favori ekle veya listeyi güncelle
        elif request.method == 'POST':
            try:
                data = request.json
                
                if not data or 'watchlist' not in data:
                    return jsonify({
                        "status": "error",
                        "message": "Watchlist data is required"
                    }), 400
                    
                watchlist = data['watchlist']
                
                if not os.path.exists('data'):
                    os.makedirs('data')
                    
                with open(watchlist_file, 'w') as f:
                    json.dump(watchlist, f)
                    
                return jsonify({
                    "status": "success",
                    "message": "Watchlist updated successfully",
                    "watchlist": watchlist
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Error updating watchlist: {str(e)}"
                }), 500
                
        # DELETE: Favorilerden bir öğe sil veya tüm listeyi temizle
        elif request.method == 'DELETE':
            try:
                if not os.path.exists(watchlist_file):
                    return jsonify({
                        "status": "success",
                        "message": "Watchlist already empty"
                    })
                    
                symbol = request.args.get('symbol')
                
                # Tüm listeyi sil
                if not symbol:
                    os.remove(watchlist_file)
                    return jsonify({
                        "status": "success",
                        "message": "Watchlist cleared successfully"
                    })
                    
                # Sadece belirli bir sembolü sil
                with open(watchlist_file, 'r') as f:
                    watchlist = json.load(f)
                    
                if symbol in watchlist:
                    watchlist.remove(symbol)
                    
                    with open(watchlist_file, 'w') as f:
                        json.dump(watchlist, f)
                        
                    return jsonify({
                        "status": "success",
                        "message": f"{symbol} removed from watchlist",
                        "watchlist": watchlist
                    })
                else:
                    return jsonify({
                        "status": "error",
                        "message": f"{symbol} not found in watchlist"
                    }), 404
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Error processing watchlist request: {str(e)}"
                }), 500
                
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/hot-movers', methods=['GET'])
def hot_movers_api():
    try:
        if not check_auth_header(request):
            return jsonify({'error': 'Unauthorized access'}), 401
            
        timeframe = request.args.get("timeframe", "5m")
        min_change = float(request.args.get("min_change", "3.0"))  # Varsayılan olarak %3 ve üzeri değişim
        min_rating = int(request.args.get("min_rating", "2"))  # Varsayılan olarak +2 ve üzeri rating
        max_rating = int(request.args.get("max_rating", "3"))  # Varsayılan olarak maksimum +3 rating
        exchange = request.args.get("exchange", "kucoin")
        
        # Ensure exchange is kucoin (or adjust as needed)
        exchange = "kucoin"
        
        exchange_file = os.path.join(file_dir, f"{exchange}.txt")
        with open(exchange_file) as file:
            lines = file.read()
            line = lines.split('\n')
        
        screener = "crypto"
        
        # Get analysis for all coins
        analysis = get_multiple_analysis(screener=screener, interval=timeframe, symbols=line)
        
        # Process and filter results
        hot_movers = []
        
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
                    
                    # Filter for high change and rating within specified range
                    if change >= min_change and min_rating <= rating <= max_rating:
                        hot_movers.append({
                            'symbol': key,
                            'price': round(close, 4),
                            'change': round(change, 3),
                            'bbw': round(BBW, 4),
                            'rating': rating,
                            'signal': signal,
                            'volume': value.indicators.get("volume", 0),
                            'alert_message': f"{key.split(':')[1]} {timeframe} zaman diliminde %{round(change, 1)} yükseldi ve BB Rating {rating}!"
                        })
            except (TypeError, ZeroDivisionError):
                continue
        
        # Sort by change value (descending)
        sorted_movers = sorted(hot_movers, key=lambda x: x['change'], reverse=True)
        
        # Take top 20 coins
        top_movers = sorted_movers[:20]
        
        return jsonify({
            "status": "success",
            "timeframe": timeframe,
            "exchange": exchange,
            "min_change": min_change,
            "min_rating": min_rating,
            "max_rating": max_rating,
            "count": len(top_movers),
            "data": top_movers
        })
                
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/hot-movers', methods=['GET'])
def hot_movers_page():
    timeframes = ["5m", "15m", "1h", "4h", "1D", "1W"]
    return render_template('hot_movers.html', timeframes=timeframes)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email')
    
    # Validate email
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        flash(f'Invalid email: {str(e)}', 'danger')
        return redirect(url_for('hours_store'))
    
    # Check if email already exists
    existing_subscriber = Subscriber.query.filter_by(email=email).first()
    
    if existing_subscriber:
        if existing_subscriber.is_active:
            flash('You are already subscribed!', 'info')
        else:
            # Reactivate subscription
            existing_subscriber.is_active = True
            db.session.commit()
            flash('Your subscription has been reactivated!', 'success')
    else:
        # Add new subscriber
        new_subscriber = Subscriber(email=email)
        db.session.add(new_subscriber)
        db.session.commit()
        flash('Thank you for subscribing!', 'success')
    
    return redirect(url_for('hours_store'))

@app.route('/unsubscribe', methods=['GET', 'POST'])
def unsubscribe():
    if request.method == 'POST':
        email = request.form.get('email')
        
        try:
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError as e:
            flash(f'Invalid email: {str(e)}', 'danger')
            return render_template('subscription.html')
        
        # Find subscriber
        subscriber = Subscriber.query.filter_by(email=email).first()
        
        if subscriber:
            if subscriber.is_active:
                subscriber.is_active = False
                db.session.commit()
                flash('You have been unsubscribed successfully.', 'success')
            else:
                flash('This email is already unsubscribed.', 'info')
        else:
            flash('Email not found in our subscriber list.', 'danger')
        
        return render_template('subscription.html')
    
    return render_template('subscription.html')

@app.route('/subscription', methods=['GET'])
def subscription():
    return render_template('subscription.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))