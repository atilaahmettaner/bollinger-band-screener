from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from tradingview_ta import TA_Handler, get_multiple_analysis
import os
from dotenv import load_dotenv
import json
from models import db, Subscriber
from flask_sqlalchemy import SQLAlchemy
from email_validator import validate_email, EmailNotValidError

# New imports from core modules
from core.services.indicators import compute_metrics
from core.services.coinlist import load_symbols
from core.utils.validators import sanitize_timeframe, sanitize_exchange, EXCHANGE_SCREENER, ALLOWED_TIMEFRAMES
from core.services.screener_provider import fetch_screener_indicators, fetch_screener_multi_changes

load_dotenv()

API_KEY = os.getenv('API_KEY')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'developmentsecretkey')

if os.environ.get('DATABASE_URL'):
    db_url = os.environ.get('DATABASE_URL')
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///subscribers.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.before_request
def redirect_to_custom_domain():
    """Redirect from Heroku domain to the custom domain."""
    heroku_domain = 'crypto-scanner-app.herokuapp.com'
    custom_domain = 'cryptosieve.com'
    
    host = request.host.lower()
    
    if host == heroku_domain:
        new_url = request.url.replace(heroku_domain, custom_domain, 1)
        if not new_url.startswith('https://'):
             new_url = new_url.replace('http://', 'https://', 1)
        return redirect(new_url, code=301)

with app.app_context():
    db.create_all()

file_dir='coinlist'

@app.route('/', methods=['GET', 'POST'])
def hours_store():
    return render_template('index.html', Hourss=["4h","5m" ,"15m", "1h" , "1D", "1W", "1M"])

@app.route('/trending', methods=['POST'])
def trending_coins():
    local_element = {}
    local_line_list = []
    local_line_list1 = []
    
    timeframe = request.form.get("timeframe", "5m")
    exchange = request.form.get("exchange", "kucoin")
    filter_type = request.form.get("filter_type", "")
    rating_filter = request.form.get("rating", "")
    
    exchange = "kucoin"
    
    exchange_file = os.path.join(file_dir, f"{exchange}.txt")
    with open(exchange_file) as file:
        lines = file.read()
        line = lines.split('\n')
    
    screener = "crypto"
    
    analysis = get_multiple_analysis(screener=screener, interval=timeframe, symbols=line)
    
    coin_changes = []
    
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
    
    if filter_type != "rating":
        sorted_coins = sorted(coin_changes, key=lambda x: x['change'], reverse=True)
    else:
        sorted_coins = coin_changes
    
    top_coins = sorted_coins[:50]
    
    for coin in top_coins:
        local_element[coin['key']] = [coin['price'], coin['bbw'], coin['change'], coin['rating'], coin['signal']]
    
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
    
    local_line_list.append(local_element)
    return render_template('data.html', line_list=local_line_list, hours=timeframe, line_list1=local_line_list1, element=local_element, 
                          filter_type=filter_type, rating_filter=rating_filter, page_title=page_title)

@app.route('/list', methods=['GET', 'POST'])
def scan():
    local_element = {}
    local_line_list = []
    local_line_list1 = []
    
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
                        local_element[key] = [price, BBW, change, rating, signal]
                        
        except (TypeError):
            print(key ," is not defined ")
        except (ZeroDivisionError):
            print(key," bbw value the is zero")
    
    local_line_list.append(local_element)
    return render_template('data.html', line_list=local_line_list, hours=hours, line_list1=local_line_list1, element=local_element)

@app.route('/getPrice', methods=['POST'])
def handle_list_request():
    request_data = request.json
    hours = request_data.get('hours')
    symbol = request_data.get('symbol')
    exchange = request_data.get('exchange')
    result = scanForApi(hours, symbol, exchange)
    return jsonify(result)

def scanForApi(hours, symbol, exchange):
    local_element = {}
    
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
                local_element["name"] = key
                local_element["current"] = price
                local_element["change"] = change
                local_element["open"] = open_price
                local_element["close"] = close

        except TypeError:
            print(key, " is not defined ")
    
    return local_element

def check_auth_header(request):
    auth_header = request.headers.get('Authorization') 
    if auth_header == API_KEY:
        return True
    return False


@app.errorhandler(404)
def pageNotFound(error):
    # Fix template name case to match templates/Error.html
    return render_template('Error.html')

@app.route('/api/scan', methods=['POST'])
def scan_api():
    try:
        request_data = request.json
        hours = request_data.get('hours', '4h')
        bbw = request_data.get('bbw', '0.04')
        exchange = request_data.get('exchange', 'kucoin')
        
        if not check_auth_header(request):
            return jsonify({'error': 'Unauthorized access'}), 401

        
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
        
        del analysis
                
        return jsonify({
            "status": "success",
            "timeframe": hours,
            "exchange": exchange,
            "count": len(result),
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
        if not check_auth_header(request):
            return jsonify({'error': 'Unauthorized access'}), 401
            
        timeframe_raw = request.args.get("timeframe", "5m")
        exchange_raw = request.args.get("exchange", "kucoin")
        filter_type = request.args.get("filter_type", "")
        rating_filter = request.args.get("rating", "")
        
        timeframe = sanitize_timeframe(timeframe_raw, "5m")
        exchange = sanitize_exchange(exchange_raw, "kucoin")
        
        symbols = load_symbols(exchange)
        if not symbols:
            return jsonify({
                "status": "error",
                "message": f"Exchange symbol list not found for '{exchange}'"
            }), 404
        
        screener = EXCHANGE_SCREENER.get(exchange, "crypto")
        
        analysis = get_multiple_analysis(screener=screener, interval=timeframe, symbols=symbols)
        
        coin_changes = []
        
        for key, value in analysis.items():
            try:
                if value is not None:
                    metrics = compute_metrics(value.indicators)
                    if not metrics or metrics["bbw"] is None:
                        continue

                    if filter_type == "rating" and rating_filter:
                        try:
                            if int(rating_filter) != metrics["rating"]:
                                continue
                        except ValueError:
                            pass
                    
                    coin_changes.append({
                        'symbol': key,
                        'price': metrics['price'],
                        'change': metrics['change'],
                        'bbw': metrics['bbw'],
                        'rating': metrics['rating'],
                        'signal': metrics['signal'],
                        'volume': value.indicators.get("volume", 0)
                    })
            except (TypeError, ZeroDivisionError):
                continue
        
        if filter_type != "rating":
            sorted_coins = sorted(coin_changes, key=lambda x: x['change'], reverse=True)
        else:
            sorted_coins = coin_changes
        
        top_coins = sorted_coins[:50]
        
        del analysis
        
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
                symbols = [s for s in symbols if s]
                
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
        
        analysis = get_multiple_analysis(screener=screener, interval=timeframe, symbols=[symbol_with_exchange])
        
        if symbol_with_exchange not in analysis or analysis[symbol_with_exchange] is None:
            return jsonify({
                "status": "error",
                "message": f"Symbol {symbol} not found or analysis failed"
            }), 404
            
        value = analysis[symbol_with_exchange]
        
        indicators = value.indicators
        
        try:
            open_price = indicators["open"]
            close = indicators["close"]
            change = ((close-open_price)/open_price)*100
            sma = indicators["SMA20"]
            bb_upper = indicators["BB.upper"]
            bb_lower = indicators["BB.lower"]
            bb_middle = sma
            BBW = (bb_upper - bb_lower) / sma
            
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
      
        user_id = request.args.get('user_id', 'anonymous')
        watchlist_file = os.path.join('data', f'watchlist_{user_id}.json')
        
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
                
        elif request.method == 'DELETE':
            try:
                if not os.path.exists(watchlist_file):
                    return jsonify({
                        "status": "success",
                        "message": "Watchlist already empty"
                    })
                    
                symbol = request.args.get('symbol')
                
                if not symbol:
                    os.remove(watchlist_file)
                    return jsonify({
                        "status": "success",
                        "message": "Watchlist cleared successfully"
                    })
                    
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
        min_change = float(request.args.get("min_change", "3.0"))
        min_rating = int(request.args.get("min_rating", "2"))
        max_rating = int(request.args.get("max_rating", "3"))
        exchange = request.args.get("exchange", "kucoin")
        
        exchange = "kucoin"
        
        exchange_file = os.path.join(file_dir, f"{exchange}.txt")
        with open(exchange_file) as file:
            lines = file.read()
            line = lines.split('\n')
        
        screener = "crypto"
        
        analysis = get_multiple_analysis(screener=screener, interval=timeframe, symbols=line)
        
        hot_movers = []
        
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
        
        sorted_movers = sorted(hot_movers, key=lambda x: x['change'], reverse=True)
        
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
    
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        flash(f'Invalid email: {str(e)}', 'danger')
        return redirect(url_for('hours_store'))
    
    existing_subscriber = Subscriber.query.filter_by(email=email).first()
    
    if existing_subscriber:
        if existing_subscriber.is_active:
            flash('You are already subscribed!', 'info')
        else:
            existing_subscriber.is_active = True
            db.session.commit()
            flash('Your subscription has been reactivated!', 'success')
    else:
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

@app.route('/api/demo-screener', methods=['GET'])
def demo_screener():
    try:
        if not check_auth_header(request):
            return jsonify({'error': 'Unauthorized access'}), 401
        
        exchange_raw = request.args.get('exchange', 'kucoin')
        limit_raw = request.args.get('limit', '20')
        
        exchange = sanitize_exchange(exchange_raw, 'kucoin')
        try:
            limit = max(1, min(int(limit_raw), 50))
        except ValueError:
            limit = 20
        
        symbols = load_symbols(exchange)
        if not symbols:
            return jsonify({
                'status': 'error',
                'message': f"Exchange symbol list not found for '{exchange}'"
            }), 404
        
        symbols = symbols[:limit]
        
        try:
            rows = fetch_screener_indicators(exchange, symbols, limit=limit)
        except ImportError as e:
            return jsonify({
                'status': 'error',
                'message': 'tradingview-screener is not installed. Please add it to requirements.txt and install.'
            }), 500
        
        data = []
        for row in rows:
            indicators = row.get('indicators', {})
            metrics = compute_metrics(indicators)
            if not metrics or metrics.get('bbw') is None:
                continue
            data.append({
                'symbol': row.get('symbol'),
                'price': metrics['price'],
                'change': metrics['change'],
                'bbw': metrics['bbw'],
                'rating': metrics['rating'],
                'signal': metrics['signal'],
                'volume': indicators.get('volume', 0)
            })
        
        return jsonify({
            'status': 'success',
            'exchange': exchange,
            'count': len(data),
            'data': data
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/multi-changes', methods=['GET'])
def multi_changes_api():
    try:
        if not check_auth_header(request):
            return jsonify({'error': 'Unauthorized access'}), 401

        exchange_raw = request.args.get('exchange', 'kucoin')
        limit_raw = request.args.get('limit', '50')
        base_tf_raw = request.args.get('base_timeframe', '4h')
        tfs_raw = request.args.get('timeframes', '15m,1h,4h,1D')  # CSV list

        exchange = sanitize_exchange(exchange_raw, 'kucoin')
        base_tf = sanitize_timeframe(base_tf_raw, '4h')

        # Parse timeframe list and sanitize
        req_tfs = [tf.strip() for tf in tfs_raw.split(',') if tf.strip()]
        timeframes = [tf for tf in req_tfs if tf in ALLOWED_TIMEFRAMES]
        if not timeframes:
            timeframes = ['15m', '1h', base_tf, '1D']

        try:
            limit = max(1, min(int(limit_raw), 200))
        except ValueError:
            limit = 50

        # Load symbols from coinlist and cap by limit for performance
        symbols = load_symbols(exchange)
        if not symbols:
            return jsonify({'status': 'error', 'message': f"Exchange symbol list not found for '{exchange}'"}), 404
        symbols = symbols[:limit]

        # Fetch multi-timeframe data
        rows = fetch_screener_multi_changes(
            exchange=exchange,
            symbols=symbols,
            timeframes=timeframes,
            base_timeframe=base_tf,
            limit=limit,
        )

        data = []
        for row in rows:
            base_ind = row.get('base_indicators', {})
            metrics = compute_metrics(base_ind)
            if not metrics or metrics.get('bbw') is None:
                continue
            data.append({
                'symbol': row.get('symbol'),
                'price': metrics['price'],
                'bbw': metrics['bbw'],
                'rating': metrics['rating'],
                'signal': metrics['signal'],
                'changes': row.get('changes', {}),
                'volume': base_ind.get('volume', 0),
            })

        return jsonify({
            'status': 'success',
            'exchange': exchange,
            'base_timeframe': base_tf,
            'timeframes': timeframes,
            'count': len(data),
            'data': data,
        })
    except ImportError as e:
        return jsonify({'status': 'error', 'message': 'tradingview-screener is not installed. Please add it to requirements.txt and install.'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/mcp-server')
def mcp_server():
    """Landing page for TradingView MCP Server"""
    return render_template('mcp_landing.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
