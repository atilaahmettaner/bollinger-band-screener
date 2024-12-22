import os
import smtplib
import requests
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
EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT')
API_KEY = os.getenv('API_KEY')

# Scanner configuration - Heroku uygulamasına yönlendirildi
SCAN_URL = 'https://crypto-scanner-app.herokuapp.com/api/scan'  # Canlı Heroku URL'si
HEADERS = {'Authorization': API_KEY}

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
    </body>
    </html>
    """
    
    return html

def send_email(subject, html_content):
    """Send an email with the scan results"""
    if not all([EMAIL_HOST, EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        print("Email configuration incomplete. Check your .env file.")
        return False
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_RECIPIENT
    msg['Subject'] = subject
    
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email sent successfully to {EMAIL_RECIPIENT}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def main():
    """Main function to run the scan and send email"""
    # Zaman dilimlerini büyük harfle tanımla
    scan_configs = [
        {'timeframe': '4H', 'bbw': '0.05', 'exchange': 'kucoin'},
        {'timeframe': '1D', 'bbw': '0.13', 'exchange': 'kucoin'}
    ]
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    all_results = []
    
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
    
    combined_html = ""
    for result in all_results:
        html_content = format_email_html(result['results'], result['timeframe'])
        combined_html += f"<br><hr><br>{html_content}"
    
    if combined_html:
        subject = f"Bollinger Band Scan Results - Multiple Timeframes - {current_date}"
        send_email(subject, combined_html)

if __name__ == "__main__":
    main() 