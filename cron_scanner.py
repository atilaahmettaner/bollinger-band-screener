import os
import smtplib
import requests
import sys
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Email configuration
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
API_KEY = os.getenv('API_KEY')

# Scanner configuration - Heroku uygulamasına yönlendirildi
SCAN_URL = 'https://crypto-scanner-app.herokuapp.com/api/scan'  # Canlı Heroku URL'si
HEADERS = {'Authorization': API_KEY}

def get_active_subscribers():
    """
    Aktif aboneleri veritabanından çeker.
    Hem Heroku PostgreSQL hem de yerel SQLite için destek sağlar.
    Sorun olması durumunda varsayılan alıcıyı döndürür.
    """
    try:
        # Heroku postgres veritabanı varsa
        if os.environ.get('DATABASE_URL'):
            try:
                # Burada psycopg2 modülünü içe aktarıyoruz
                import psycopg2
                
                # DB URL'i düzeltme (gerekirse)
                db_url = os.environ.get('DATABASE_URL')
                if db_url.startswith("postgres://"):
                    db_url = db_url.replace("postgres://", "postgresql://", 1)
                
                # SQLAlchemy kullanmadan doğrudan psycopg2 ile bağlantı
                conn = psycopg2.connect(db_url)
                cur = conn.cursor()
                
                # Aktif aboneleri sorgula
                cur.execute("SELECT email FROM subscriber WHERE is_active = True")
                
                # Sonuçları al
                subscribers = [row[0] for row in cur.fetchall()]
                
                # Bağlantıyı kapat
                cur.close()
                conn.close()
                
                if subscribers:
                    print(f"Found {len(subscribers)} active subscribers")
                    return subscribers
                else:
                    print("No active subscribers found in database")
                    return [os.getenv('EMAIL_RECIPIENT', 'atilaahmet07@gmail.com')]
                    
            except ImportError:
                print("Error: psycopg2 module not found, using default recipient")
                return [os.getenv('EMAIL_RECIPIENT', 'atilaahmet07@gmail.com')]
            except Exception as e:
                print(f"Database error: {str(e)}")
                return [os.getenv('EMAIL_RECIPIENT', 'atilaahmet07@gmail.com')]
        else:
            # Yerel SQLite veritabanı - ihtiyaca göre ayarla
            try:
                import sqlite3
                conn = sqlite3.connect('subscribers.db')
                cur = conn.cursor()
                cur.execute("SELECT email FROM subscriber WHERE is_active = 1")
                subscribers = [row[0] for row in cur.fetchall()]
                cur.close()
                conn.close()
                
                if subscribers:
                    print(f"Found {len(subscribers)} active subscribers in SQLite")
                    return subscribers
                else:
                    print("No active subscribers found in SQLite database")
                    return [os.getenv('EMAIL_RECIPIENT', 'atilaahmet07@gmail.com')]
            except Exception as e:
                print(f"SQLite error: {str(e)}")
                return [os.getenv('EMAIL_RECIPIENT', 'atilaahmet07@gmail.com')]
    except Exception as e:
        print(f"Error getting subscribers: {str(e)}")
        return [os.getenv('EMAIL_RECIPIENT', 'atilaahmet07@gmail.com')]

def run_scan(timeframe='1D', bbw='0.04', exchange='kucoin'):
    """Run the Bollinger Band scan via the API"""
    payload = {
        'hours': timeframe,
        'bbw': bbw,
        'exchange': exchange
    }
    
    try:
        response = requests.post(SCAN_URL, json=payload, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Scan error: {e}")
        return None

def format_email_html(scan_results, timeframe):
    """Format the scan results as HTML for email"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Timeframe'i TradingView formatına çevir
    tv_timeframe = timeframe.upper()  # '4h' -> '4H', '1d' -> '1D'
    
    if scan_results is None:
        return f"<h2>Error: Failed to run Bollinger Band scan at {current_time}</h2>"
    
    if scan_results.get('status') != 'success':
        return f"<h2>Error: {scan_results.get('message', 'Unknown error')}</h2>"
    
    data = scan_results.get('data', [])
    exchange = scan_results.get('exchange', 'kucoin')
    
    if not data:
        return f"<h2>No results found for {exchange} at {tv_timeframe} timeframe (BBW scan)</h2>"
    
    html = f"""
    <html>
    <head>
        <style>
            table {{
                border-collapse: collapse;
                width: 100%;
                font-family: Arial, sans-serif;
            }}
            th, td {{
                border: 1px solid #dddddd;
                text-align: left;
                padding: 8px;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            .positive {{
                color: green;
            }}
            .negative {{
                color: red;
            }}
            a {{
                color: #0066cc;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .footer {{
                margin-top: 20px;
                font-size: 12px;
                color: #666;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <h2>Bollinger Band Scan Results - {exchange.upper()} ({tv_timeframe})</h2>
        <p>Scan Time: {current_time}</p>
        <table>
            <tr>
                <th>Symbol</th>
                <th>Price</th>
                <th>BBW</th>
                <th>Change (%)</th>
                <th>RSI</th>
                <th>Volume</th>
            </tr>
    """
    
    for item in data:
        symbol = item.get('symbol', '')
        clean_symbol = symbol.split(':')[-1] if ':' in symbol else symbol
        
        # TradingView linki için büyük harf timeframe kullan
        tv_link = f"https://www.tradingview.com/chart/?symbol={exchange}:{clean_symbol}&interval={tv_timeframe}"
        
        change_class = "positive" if item.get('change', 0) >= 0 else "negative"
        html += f"""
            <tr>
                <td><a href="{tv_link}" target="_blank">{clean_symbol}</a></td>
                <td>{item.get('price')}</td>
                <td>{item.get('bbw')}</td>
                <td class="{change_class}">{item.get('change')}</td>
                <td>{item.get('rsi')}</td>
                <td>{item.get('volume')}</td>
            </tr>
        """
    
    html += """
        </table>
        <div class="footer">
            <p>You received this email because you subscribed to Bollinger Band Scanner alerts.</p>
            <p>To unsubscribe, <a href="https://crypto-scanner-app.herokuapp.com/subscription">click here</a>.</p>
        </div>
    </body>
    </html>
    """
    
    return html

def send_email(subject, html_content, recipients):
    """Send an email with the scan results to multiple recipients"""
    if not all([EMAIL_HOST, EMAIL_USER, EMAIL_PASSWORD]):
        print("Email configuration incomplete. Check your .env file.")
        return False
    
    if not recipients:
        print("No recipients to send email to.")
        return False
    
    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        
        success_count = 0
        error_count = 0
        
        for recipient in recipients:
            try:
                msg = MIMEMultipart()
                msg['From'] = EMAIL_USER
                msg['To'] = recipient
                msg['Subject'] = subject
                
                msg.attach(MIMEText(html_content, 'html'))
                
                server.send_message(msg)
                success_count += 1
                print(f"Email sent successfully to {recipient}")
            except Exception as e:
                error_count += 1
                print(f"Failed to send email to {recipient}: {e}")
        
        server.quit()
        print(f"Email sending complete. Success: {success_count}, Errors: {error_count}")
        return success_count > 0
    except Exception as e:
        print(f"Failed to connect to email server: {e}")
        return False

def get_fear_greed_index():
    """Fear & Greed Index'i alternative.me API'sinden al"""
    try:
        response = requests.get('https://api.alternative.me/fng/')
        data = response.json()
        
        if data['metadata']['error'] is None:
            # En son değeri al
            latest = data['data'][0]
            
            # Fear & Greed değeri ve sınıflandırması
            value = latest['value']
            classification = latest['value_classification']
            timestamp = latest['timestamp']
            
            return {
                'value': value,
                'classification': classification,
                'timestamp': timestamp,
                'success': True
            }
    except Exception as e:
        print(f"Fear & Greed Index hatası: {e}")
    
    return {'success': False}

def format_fear_greed_html(fear_greed_data):
    """Fear & Greed Index HTML formatla"""
    if not fear_greed_data['success']:
        return "<p>Fear & Greed Index verisi alınamadı.</p>"
    
    # Fear & Greed renk kodu belirle
    value = int(fear_greed_data['value'])
    
    # Renk gradyan hesapla (Kırmızı: Aşırı Korku - Yeşil: Aşırı Açgözlülük)
    if value <= 25:  # Korku veya Aşırı Korku
        color = f"rgb(255, {value * 10}, 0)"
    elif value <= 50:  # Nötr'e yakın
        green_value = (value - 25) * 10
        color = f"rgb(255, {200 - green_value}, 0)"
    else:  # Açgözlülük veya Aşırı Açgözlülük
        red_value = 255 - ((value - 50) * 5)
        color = f"rgb({red_value}, 200, 0)"
    
    html = f"""
    <div style="background-color: #f9f9f9; padding: 15px; border-radius: 10px; margin: 20px 0; text-align: center;">
        <h3>Fear & Greed Index</h3>
        <div style="display: inline-block; width: 150px; height: 150px; border-radius: 50%; background-color: {color}; 
                    line-height: 150px; color: white; font-size: 40px; font-weight: bold; margin: 10px;">
            {value}
        </div>
        <p style="font-size: 20px; font-weight: bold; margin: 10px;">{fear_greed_data['classification']}</p>
        <p style="color: #666; font-size: 14px;">Güncellenme: {fear_greed_data['timestamp']}</p>
    </div>
    """
    
    return html

def main():
    """Main function to run the scan and send email"""
    # Zaman dilimlerini büyük harfle tanımla
    scan_configs = [
        {'timeframe': '4H', 'bbw': '0.05', 'exchange': 'binance'},
        {'timeframe': '1D', 'bbw': '0.13', 'exchange': 'binance'}
    ]
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    all_results = []
    
    # Fear & Greed Index'i al
    fear_greed_data = get_fear_greed_index()
    
    for config in scan_configs:
        scan_results = run_scan(
            timeframe=config['timeframe'], 
            bbw=config['bbw'], 
            exchange=config['exchange']
        )
        if scan_results:
            all_results.append({
                'timeframe': config['timeframe'],
                'results': scan_results
            })
    
    # Fear & Greed Index HTML'ini oluştur
    fear_greed_html = format_fear_greed_html(fear_greed_data)
    
    # Tüm tarama sonuçlarını birleştir
    combined_html = fear_greed_html  # Önce Fear & Greed Index'i göster
    
    for result in all_results:
        html_content = format_email_html(result['results'], result['timeframe'])
        combined_html += f"<br><hr><br>{html_content}"
    
    if combined_html:
        # Get all active subscribers
        subscribers = get_active_subscribers()
        
        if subscribers:
            subject = f"Bollinger Band Scan Results - Multiple Timeframes - {current_date}"
            send_email(subject, combined_html, subscribers)
        else:
            print("No active subscribers found. Email not sent.")

if __name__ == "__main__":
    main() 