import os
import smtplib
import requests
import sys
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime
import json # Import json

# Load environment variables
load_dotenv()

# Email configuration
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
API_KEY = os.getenv('API_KEY') # Ensure API_KEY is loaded

# Base URL for the CryptoSieve API (using the custom domain)
BASE_API_URL = 'https://cryptosieve.com/api' 

# API Endpoints
SQUEEZE_SCAN_URL = f'{BASE_API_URL}/scan'
TRENDING_URL = f'{BASE_API_URL}/trending' # Used for showing strength
HOT_MOVERS_URL = f'{BASE_API_URL}/hot-movers'

HEADERS = {'Authorization': API_KEY, 'Content-Type': 'application/json'}

# --- Database Functions ---

def get_active_subscribers():
    """
    Fetches active subscribers from the database.
    Supports both Heroku PostgreSQL and local SQLite.
    Returns a default recipient if issues occur.
    """
    default_recipient = os.getenv('EMAIL_RECIPIENT', 'default_test_email@example.com') # Provide a default
    try:
        # Check for Heroku PostgreSQL
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            try:
                import psycopg2
                if db_url.startswith("postgres://"):
                    db_url = db_url.replace("postgres://", "postgresql://", 1)
                
                conn = psycopg2.connect(db_url)
                cur = conn.cursor()
                cur.execute("SELECT email FROM subscriber WHERE is_active = True")
                subscribers = [row[0] for row in cur.fetchall()]
                cur.close()
                conn.close()
                
                if subscribers:
                    print(f"Found {len(subscribers)} active subscribers in PostgreSQL")
                    return subscribers
                else:
                    print("No active subscribers found in PostgreSQL database, using default.")
                    return [default_recipient]
            except ImportError:
                print("Error: psycopg2 module not found, install it (`pip install psycopg2-binary`)")
                return [default_recipient]
            except Exception as e:
                print(f"PostgreSQL database error: {str(e)}")
                return [default_recipient]
        else:
            # Local SQLite database
            try:
                conn = sqlite3.connect('subscribers.db') # Ensure this path is correct
                cur = conn.cursor()
                cur.execute("SELECT email FROM subscriber WHERE is_active = 1")
                subscribers = [row[0] for row in cur.fetchall()]
                cur.close()
                conn.close()
                
                if subscribers:
                    print(f"Found {len(subscribers)} active subscribers in SQLite")
                    return subscribers
                else:
                    print("No active subscribers found in SQLite database, using default.")
                    return [default_recipient]
            except Exception as e:
                print(f"SQLite error: {str(e)}")
                return [default_recipient]
    except Exception as e:
        print(f"Error getting subscribers: {str(e)}")
        return [default_recipient]

# --- API Fetching Functions ---

def run_squeeze_scan(timeframe='1D', bbw='0.13', exchange='kucoin'):
    """Run the Bollinger Band Squeeze Scan via the API"""
    payload = {'hours': timeframe, 'bbw': bbw, 'exchange': exchange}
    print(f"Running squeeze scan: timeframe={timeframe}, bbw={bbw}, exchange={exchange}")
    try:
        response = requests.post(SQUEEZE_SCAN_URL, json=payload, headers=HEADERS, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Squeeze scan API error: {e}")
        return {'status': 'error', 'message': str(e)}
    except json.JSONDecodeError:
        print(f"Squeeze scan API response is not valid JSON: {response.text}")
        return {'status': 'error', 'message': 'Invalid JSON response from API'}


def get_hot_movers(timeframe='15m', min_change='3.0', min_rating='2', max_rating='3', exchange='kucoin'):
    """Get Hot Movers data from the API"""
    params = {
        'timeframe': timeframe,
        'min_change': min_change,
        'min_rating': min_rating,
        'max_rating': max_rating,
        'exchange': exchange
    }
    print(f"Fetching hot movers: timeframe={timeframe}, exchange={exchange}")
    try:
        # Assuming GET request for hot movers
        response = requests.get(HOT_MOVERS_URL, params=params, headers=HEADERS, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Hot Movers API error: {e}")
        return {'status': 'error', 'message': str(e)}
    except json.JSONDecodeError:
        print(f"Hot Movers API response is not valid JSON: {response.text}")
        return {'status': 'error', 'message': 'Invalid JSON response from API'}

def get_showing_strength(timeframe='4h', rating='2', exchange='kucoin'):
    """Get assets showing strength (specific BB Rating + Gainers) from the API"""
    params = {
        'timeframe': timeframe,
        'filter_type': 'rating', # Assuming the trending endpoint handles this
        'rating': rating,
        'exchange': exchange
    }
    print(f"Fetching showing strength: timeframe={timeframe}, rating={rating}, exchange={exchange}")
    try:
         # Using the trending endpoint, assuming it returns sorted data when filtering by rating
        response = requests.get(TRENDING_URL, params=params, headers=HEADERS, timeout=60)
        response.raise_for_status()
        data = response.json()
        # Filter for positive change if not already done by API
        if data.get('status') == 'success':
            positive_gainers = [item for item in data.get('data', []) if item.get('change', 0) > 0]
             # Sort by change descending (API might already do this)
            data['data'] = sorted(positive_gainers, key=lambda x: x.get('change', 0), reverse=True)
        return data
    except requests.exceptions.RequestException as e:
        print(f"Showing Strength API error: {e}")
        return {'status': 'error', 'message': str(e)}
    except json.JSONDecodeError:
        print(f"Showing Strength API response is not valid JSON: {response.text}")
        return {'status': 'error', 'message': 'Invalid JSON response from API'}


def get_fear_greed_index():
    """Fetch Fear & Greed Index from alternative.me API"""
    print("Fetching Fear & Greed Index...")
    try:
        response = requests.get('https://api.alternative.me/fng/?limit=1', timeout=10) # Limit to 1 day
        response.raise_for_status()
        data = response.json()
        
        if 'data' in data and len(data['data']) > 0:
            latest = data['data'][0]
            timestamp_dt = datetime.fromtimestamp(int(latest['timestamp']))
            return {
                'value': latest['value'],
                'classification': latest['value_classification'],
                'timestamp': timestamp_dt.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'success': True
            }
        else:
             print(f"Fear & Greed API response format unexpected: {data}")
             return {'success': False, 'message': 'Unexpected API response format'}
    except requests.exceptions.RequestException as e:
        print(f"Fear & Greed Index API error: {e}")
        return {'success': False, 'message': str(e)}
    except (KeyError, IndexError, ValueError) as e:
         print(f"Error processing Fear & Greed data: {e}")
         return {'success': False, 'message': 'Error processing API data'}

# --- HTML Formatting Functions ---

def format_section_html(title, description, data, columns, link_column_index=0, timeframe=''):
    """Generic function to format a data section as HTML table."""
    if data is None or data.get('status') != 'success':
        error_msg = data.get('message', 'Failed to fetch data') if data else 'Failed to fetch data'
        print(f"Error generating HTML for '{title}': {error_msg}")
        return f"""
        <h3 style="color: #FFA500; border-bottom: 1px solid #555; padding-bottom: 5px;">{title}</h3>
        <p style="font-size: 14px; color: #ccc;"><i>Error: Could not retrieve data. {error_msg}</i></p>
        """

    items = data.get('data', [])
    exchange = data.get('exchange', 'kucoin').upper() # Use exchange from data if available

    if not items:
        return f"""
        <h3 style="color: #4CAF50; border-bottom: 1px solid #555; padding-bottom: 5px;">{title}</h3>
        <p style="font-size: 14px; color: #ccc;">{description}</p>
        <p style="font-size: 14px; color: #ccc;"><i>No results found for this section today.</i></p>
        """

    # Build Header Row
    header_html = "".join(f'<th style="padding: 10px; border: 1px solid #555; text-align: left; background-color: #2a3145; color: #eee;">{col}</th>' for col in columns)

    # Build Data Rows
    rows_html = ""
    for item in items:
        cells_html = ""
        for i, col_key in enumerate(columns):
            # Basic key mapping - handle variations like 'BB Rating', 'Change (%)'
            raw_key = col_key.lower().replace('(%)', '').replace('#', '').strip().replace(' ', '_') 
            value = item.get(raw_key, '')
            
            # Try symbol key if standard key fails
            if value == '' and raw_key == 'symbol':
                 value = item.get('key', '') # Fallback for older API responses maybe?
                 
            formatted_value = value # Default value

            # Apply specific formatting
            if col_key == 'Symbol' and link_column_index == i:
                symbol_raw = item.get('symbol', item.get('key', '')) # Get symbol, fallback to key
                if not symbol_raw: # Skip if no symbol found
                    formatted_value = 'N/A'
                else:
                    clean_symbol = symbol_raw.split(':')[-1] if ':' in symbol_raw else symbol_raw
                    exchange_prefix = symbol_raw.split(':')[0] if ':' in symbol_raw else exchange # Get exchange from symbol if possible
                    # Use timeframe from data if available, else fallback
                    interval = data.get('timeframe', timeframe).upper() if data.get('timeframe', timeframe) else ''
                    tv_link = f"https://www.tradingview.com/chart/?symbol={exchange_prefix}:{clean_symbol}"
                    if interval: # Add interval only if available
                        tv_link += f"&interval={interval}"
                    formatted_value = f'<a href="{tv_link}" target="_blank" style="color: #64b5f6; text-decoration: none;">{clean_symbol}</a>'
            
            elif col_key == 'Change (%)':
                 try:
                    change_val = float(value)
                    color = "#4CAF50" if change_val >= 0 else "#F44336" # Green for positive, Red for negative
                    formatted_value = f'<span style="color: {color};">{change_val:.2f}%</span>'
                 except (ValueError, TypeError):
                     formatted_value = f'<span style="color: #ccc;">{value}</span>' # Grey if not a number
            
            elif col_key == 'BB Rating':
                 try:
                     rating_val = int(value)
                     if rating_val > 0: color = "#4CAF50" # Green shades for positive rating
                     elif rating_val < 0: color = "#F44336" # Red shades for negative rating
                     else: color = "#ccc" # Grey for neutral
                     formatted_value = f'<span style="color: {color}; font-weight: bold;">{rating_val:+}</span>'
                 except (ValueError, TypeError):
                     formatted_value = f'<span style="color: #ccc;">{value}</span>'
            
            elif col_key == 'Signal':
                 color = "#4CAF50" if value == "BUY" else ("#F44336" if value == "SELL" else "#ccc")
                 weight = "bold" if value in ["BUY", "SELL"] else "normal"
                 formatted_value = f'<span style="color: {color}; font-weight: {weight};">{value}</span>'
            
            elif isinstance(value, float):
                 # Attempt to format floats nicely, handle potential errors
                 try:
                     if abs(value) < 0.0001 and value != 0:
                         formatted_value = f"{value:.6f}" # More precision for very small numbers
                     elif abs(value) > 1000:
                          formatted_value = f"{value:,.2f}" # Comma separation for large numbers
                     else:
                          formatted_value = f"{value:.4f}" # Default float formatting
                 except (ValueError, TypeError):
                     formatted_value = str(value)
            
            elif isinstance(value, int) and raw_key != 'bb_rating': 
                 # Format large integers like volume with commas
                 try:
                     formatted_value = f"{value:,}"
                 except (ValueError, TypeError):
                      formatted_value = str(value)
            
            else:
                 # Ensure the value is a string for the cell
                 formatted_value = str(value)

            # Determine text alignment (right align numbers, except rating)
            text_align = "left"
            is_numeric = isinstance(item.get(raw_key), (int, float))
            if is_numeric and raw_key != 'bb_rating':
                text_align = "right"
                
            cells_html += f'<td style="padding: 8px; border: 1px solid #555; text-align: {text_align};">{formatted_value}</td>'
        rows_html += f'<tr style="background-color: #1e293b;">{cells_html}</tr>'

    # Combine parts
    return f"""
    <h3 style="color: #4CAF50; border-bottom: 1px solid #555; padding-bottom: 5px;">{title}</h3>
    <p style="font-size: 14px; color: #ccc;">{description}</p>
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; color: #eee;">
        <thead><tr style="background-color: #2a3145;">{header_html}</tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """

def format_fear_greed_html(fear_greed_data):
    """Format Fear & Greed Index HTML (English)"""
    if not fear_greed_data or not fear_greed_data.get('success'):
        return "<p style='color: #ccc;'>Fear & Greed Index data currently unavailable.</p>"

    value = int(fear_greed_data['value'])
    classification = fear_greed_data['classification']
    timestamp = fear_greed_data['timestamp']

    # Determine color based on value
    color = "#ccc" # Default grey
    if value <= 25: color = f"rgb(210, {max(0, 25 + value * 4)}, {max(0, 25 + value * 2)})" # More red/orange for extreme fear
    elif value < 46: color = f"rgb(210, {100 + int((value-25)*3)}, 0)" # Orange/Yellow for fear
    elif value <= 54: color = f"rgb(180, 180, 180)" # Neutral grey
    elif value < 75: color = f"rgb({180-int((value-55)*4)}, 190, {100-int((value-55)*3)})" # Light Green for greed
    else: color = f"rgb({max(0, 100 - int((value-75)*3))}, 200, {max(0, 100 - int((value-75)*3))})" # Strong Green for extreme greed

    return f"""
    <div style="background-color: #1a2439; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center; border: 1px solid #334155;">
        <h3 style="color: #eee; margin-top: 0; margin-bottom: 15px; font-weight: 500;">Market Sentiment</h3>
        <div style="display: inline-block; width: 100px; height: 100px; border-radius: 50%; background-color: {color};
                    line-height: 100px; color: #111; font-size: 28px; font-weight: bold; margin-bottom: 10px;">
            {value}
        </div>
        <p style="font-size: 18px; font-weight: bold; margin: 0 0 5px 0; color: {color};">{classification}</p>
        <p style="color: #94a3b8; font-size: 12px; margin: 0;">Last updated: {timestamp}</p>
    </div>
    """

def generate_full_html_report(fear_greed_html, squeeze_1d_html, squeeze_4h_html, hot_movers_html, showing_strength_html):
    """Generates the full HTML email body by combining sections."""
    unsubscribe_url = "https://cryptosieve.com/subscription" # Use custom domain
    report_date = datetime.now().strftime("%Y-%m-%d")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>CryptoSieve Daily Digest</title>
        <style>
            body {{ background-color: #0f172a; color: #f8fafc; font-family: Arial, sans-serif; margin: 0; padding: 0; }}
            .container {{ padding: 20px; max-width: 700px; margin: auto; background-color: #1e293b; border-radius: 8px; }}
            .header {{ text-align: center; padding-bottom: 15px; border-bottom: 1px solid #334155; margin-bottom: 20px; }}
            .header h1 {{ color: #eee; margin: 0; font-size: 24px; font-weight: 500; }}
            .header p {{ color: #94a3b8; margin: 5px 0 0 0; font-size: 14px; }}
            .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #334155; font-size: 12px; color: #94a3b8; text-align: center; }}
            .footer a {{ color: #64b5f6; text-decoration: none; }}
            .footer a:hover {{ text-decoration: underline; }}
            h3 {{ color: #4CAF50; margin-top: 25px; margin-bottom: 10px; font-weight: 500; }}
            p {{ font-size: 14px; color: #ccc; line-height: 1.5; }}
            hr {{ border: none; border-top: 1px solid #334155; margin: 25px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; color: #eee; }}
            th, td {{ border: 1px solid #555; padding: 8px; text-align: left; font-size: 13px; }}
            th {{ background-color: #2a3145; color: #eee; font-weight: bold; }}
            tr {{ background-color: #1e293b; }} /* Ensure consistent row background */
            a {{ color: #64b5f6; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>CryptoSieve Daily Digest</h1>
                <p>{report_date}</p>
            </div>

            {fear_greed_html}

            <hr>

            {squeeze_1d_html}
            
            {squeeze_4h_html} 

            <hr>

            {hot_movers_html}

            <hr>

            {showing_strength_html}

            <hr>

            <div>
                <h3 style="color: #FFA500;">Notes & Explanations</h3>
                <p><strong>BBW (Bollinger Band Width):</strong> Measures the narrowness of the bands. Lower values indicate a squeeze, potentially preceding a significant price move.</p>
                <p><strong>BB Rating:</strong> Indicates price position relative to the Bollinger Bands (+3: Above Upper Band, +2: Upper Half, +1: Above Middle, -1: Below Middle, -2: Lower Half, -3: Below Lower Band).</p>
                 <p><strong>Signal:</strong> Basic signal based on BB Rating (+2: BUY, -2: SELL).</p>
            </div>

            <div class="footer">
                <p>This report was generated by CryptoSieve.</p>
                <p>You are receiving this because you subscribed to daily updates. Manage your subscription <a href="{unsubscribe_url}">here</a>.</p>
                <p>Disclaimer: This is not financial advice. Do your own research before making any investment decisions.</p>
                 <p>&copy; {datetime.now().year} CryptoSieve. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

# --- Email Sending Function ---

def send_email(subject, html_content, recipients):
    """Send an email with the scan results to multiple recipients"""
    if not all([EMAIL_HOST, EMAIL_USER, EMAIL_PASSWORD]):
        print("Email configuration incomplete. Check EMAIL_HOST, EMAIL_USER, EMAIL_PASSWORD in .env")
        return False

    if not recipients:
        print("No recipients list provided.")
        return False

    print(f"Attempting to send email to {len(recipients)} recipients...")
    
    try:
        # Use SSL for port 465, STARTTLS for 587
        if EMAIL_PORT == 465:
             server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, timeout=30)
        else: # Default to 587 with STARTTLS
            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=30)
            server.starttls()
        
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        print("Successfully logged into email server.")
        
        success_count = 0
        error_count = 0
        
        for recipient in recipients:
            try:
                msg = MIMEMultipart('alternative') # Use alternative for HTML/Plain text
                msg['From'] = f"CryptoSieve Reports <{EMAIL_USER}>" # Nicer From address
                msg['To'] = recipient
                msg['Subject'] = subject
                
                # Attach HTML part
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

    except smtplib.SMTPAuthenticationError:
        print("SMTP Authentication Error: Check EMAIL_USER and EMAIL_PASSWORD.")
        return False
    except Exception as e:
        print(f"Failed to connect to email server or send email: {e}")
        return False

# --- Main Execution ---

def main():
    """Main function to run scans, format report, and send email."""
    print("Starting daily report generation...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # --- Define Scans --- 
    # Customize these configurations as needed
    DEFAULT_EXCHANGE = 'binance' # Default exchange for scans
    
    # Squeeze Scan Configs
    squeeze_configs = [
        {'timeframe': '1D', 'bbw': '0.13', 'exchange': DEFAULT_EXCHANGE},
        {'timeframe': '4H', 'bbw': '0.05', 'exchange': DEFAULT_EXCHANGE}
    ]
    
    # Hot Movers Config
    hot_movers_config = {'timeframe': '15m', 'exchange': DEFAULT_EXCHANGE, 'min_change':'3.0', 'min_rating':'2', 'max_rating':'3'}
    
    # Showing Strength Config
    strength_config = {'timeframe': '4h', 'rating': '2', 'exchange': DEFAULT_EXCHANGE}
    
    # 1. Fetch Data
    print("\n--- Fetching Data ---")
    fear_greed_data = get_fear_greed_index()
    
    squeeze_scan_results = []
    for config in squeeze_configs:
         result = run_squeeze_scan(**config)
         # Add config back to result for easy access in formatting
         if result.get('status') == 'success':
             result['config'] = config
         squeeze_scan_results.append(result)
         
    hot_movers_result = get_hot_movers(**hot_movers_config)
    strength_result = get_showing_strength(**strength_config)

    # 2. Format HTML Sections
    print("\n--- Formatting HTML Sections ---")
    fear_greed_html = format_fear_greed_html(fear_greed_data)

    # Format Squeeze Scans
    squeeze_html_parts = []
    for result in squeeze_scan_results:
        config = result.get('config', {'timeframe': 'N/A', 'bbw': 'N/A', 'exchange': 'N/A'})
        tf = config['timeframe']
        bbw_limit = config['bbw']
        exchange_name = config['exchange'].upper()
        
        squeeze_html_parts.append(format_section_html(
            title=f"Bollinger Band Squeeze Opportunities ({tf} - BBW < {bbw_limit})",
            description=f"Assets on {exchange_name} showing a tight BBW, indicating potential for a significant price move.",
            data=result,
            columns=['Symbol', 'Price', 'BBW', 'Change (%)', 'RSI'], # Define columns
            timeframe=tf
        ))
    combined_squeeze_html = "".join(squeeze_html_parts)

    # Format Hot Movers
    hot_movers_tf = hot_movers_config['timeframe']
    hot_movers_exchange = hot_movers_config['exchange'].upper()
    hot_movers_html = format_section_html(
        title=f"🔥 Hot Movers ({hot_movers_tf})",
        description=f"Assets on {hot_movers_exchange} with significant price increase AND BB Rating +2 or +3 in the last {hot_movers_tf}.",
        data=hot_movers_result,
        columns=['Symbol', 'Price', 'Change (%)', 'BB Rating', 'Signal'], # Define columns
        timeframe=hot_movers_tf
    )

    # Format Showing Strength
    strength_tf = strength_config['timeframe']
    strength_exchange = strength_config['exchange'].upper()
    showing_strength_html = format_section_html(
        title=f"🚀 Showing Strength (BB Rating +2, {strength_tf})",
        description=f"Top gainers on {strength_exchange} closing in the upper BB zone (Rating +2) on the {strength_tf} chart.",
        data=strength_result,
        columns=['Symbol', 'Price', 'Change (%)', 'BB Rating', 'Signal'], # Define columns
        timeframe=strength_tf
    )

    # 3. Combine HTML into Full Report
    print("\n--- Generating Full Report ---")
    combined_html = generate_full_html_report(
         fear_greed_html,
         combined_squeeze_html, 
         hot_movers_html,
         showing_strength_html
     )

    # 4. Send Email
    print("\n--- Sending Email ---")
    subscribers = get_active_subscribers()
    if subscribers:
        subject = f"CryptoSieve Daily Digest - {current_date}"
        email_sent = send_email(subject, combined_html, subscribers)
        if email_sent:
             print("Daily report email sent successfully.")
        else:
             print("Failed to send daily report email.")
    else:
        print("No active subscribers found. Email not sent.")

    print("\nReport generation process finished.")

if __name__ == "__main__":
    # Ensure API key is set
    if not API_KEY:
        print("Error: API_KEY environment variable not set. Cannot run scans.")
        sys.exit(1) # Exit if no API key
        
    main() 