# Bolinger Band Screener 
   ## [crypto-scanner-app.herokuapp.com](https://crypto-scanner-app.herokuapp.com/)  
[![GitHub stars](https://img.shields.io/github/stars/atilaahmettaner/CryptoScanner)](https://github.com/atilaahmettaner/CryptoScanner/stargazers)

[![HitCount](https://hits.dwyl.com/atilaahmettaner/bollinger-band-screener.svg?style=flat&show=unique)](http://hits.dwyl.com/atilaahmettaner/bollinger-band-screener)
 The Bollinger Band indicator is a technical analysis tool used to identify potential price breakouts or breakdowns. By entering the correct value in the tool, you can find coins with tight prices that are about to rise.
     
     
# Usage
The value to be entered in the Bollinger Band indicator varies depending on the time frame. For example:

- For daily scans, enter a value of 0.12 for BBW to get tight coins.
- For 4-hour scans, the optimum value will be 0.04.
- For hourly scans, enter a value of 0.02.
- For 15 minutes, enter bbw value of 0.08.
  
   
   
![Main Page](https://github.com/atilaahmettaner/bollinger-band-screener/assets/67838093/68a2a133-0ab8-40ae-8145-4fd876b8bd1a)

![Listing Page](https://github.com/atilaahmettaner/bollinger-band-screener/assets/67838093/7bc975f8-cbfc-485c-a4ec-7fac8269d114)

## Run Locally

Clone the project

```bash
  git clone https://github.com/atilaahmettaner/bollinger-band-screener.git
```

Go to the project directory

```bash
  cd bollinger-band-screener
```

## Run Docker

With Makefile

Run:

```bash
  make run
```
Rerun:

```bash
  make rerun
```
Another Way

Before the project can be run with Docker, a Docker image must be created. You can use the following constraint for this:
```bash
  docker build -t cryptoscreener .
```
Run docker on localhost:5000
 ```bash
  docker run -d -p 5000:5000 cryptoscreener
```

Go to to http://localhost:5000

## Mobile Application API Documentation

The application provides several API endpoints that can be consumed by mobile applications. All API endpoints require authentication using an API key provided in the Authorization header.

### Authentication

All API requests require an API key:

```
Authorization: YOUR_API_KEY
```

### Available Endpoints

#### 1. Scan for Coins

**Endpoint:** `/api/scan`  
**Method:** POST  
**Description:** Scans for coins based on Bollinger Band parameters.

**Request Parameters:**
```json
{
  "hours": "4h",  // Timeframe (5m, 15m, 1h, 4h, 1D)
  "bbw": "0.04",  // Bollinger Band Width threshold
  "exchange": "kucoin"  // Exchange (kucoin, binance, etc.)
}
```

**Response:**
```json
{
  "status": "success",
  "timeframe": "4h",
  "exchange": "kucoin",
  "data": [
    {
      "symbol": "KUCOIN:BTCUSDT",
      "price": 43215.5,
      "bbw": 0.0321,
      "change": 2.5,
      "rsi": 58.2,
      "volume": 1234567
    },
    // More coins...
  ]
}
```

#### 2. Get Trending Coins

**Endpoint:** `/api/trending`  
**Method:** GET  
**Description:** Gets trending coins or coins with specific BB ratings.

**Request Parameters:**
- `timeframe` (query param, default: "5m")
- `exchange` (query param, default: "kucoin")
- `filter_type` (query param, optional: "rating")
- `rating` (query param, optional: rating value to filter by)

**Response:**
```json
{
  "status": "success",
  "timeframe": "5m",
  "exchange": "kucoin",
  "filter_type": "rating",
  "rating_filter": "2",
  "data": [
    {
      "symbol": "KUCOIN:ETHUSDT",
      "price": 2315.75,
      "change": 1.8,
      "bbw": 0.0254,
      "rating": 2,
      "signal": "BUY",
      "volume": 987654
    },
    // More coins...
  ]
}
```

#### 3. Get Available Symbols

**Endpoint:** `/api/symbols`  
**Method:** GET  
**Description:** Gets all available symbols for a specific exchange.

**Request Parameters:**
- `exchange` (query param, default: "kucoin")

**Response:**
```json
{
  "status": "success",
  "exchange": "kucoin",
  "symbols": [
    "KUCOIN:BTCUSDT",
    "KUCOIN:ETHUSDT",
    // More symbols...
  ]
}
```

#### 4. Get Coin Details

**Endpoint:** `/api/coin-details`  
**Method:** GET  
**Description:** Gets detailed analysis for a specific coin.

**Request Parameters:**
- `symbol` (query param, required)
- `exchange` (query param, default: "kucoin")
- `timeframe` (query param, default: "4h")

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "KUCOIN:BTCUSDT",
    "timeframe": "4h",
    "price": 43215.5,
    "open": 42865.25,
    "high": 43500.0,
    "low": 42800.0,
    "volume": 1234567,
    "change": 0.82,
    "bb_rating": 2,
    "signal": "BUY",
    "bbwidth": 0.0321,
    "bb_upper": 43500.0,
    "bb_middle": 43100.0,
    "bb_lower": 42700.0,
    "rsi": 58.2,
    "ema_50": 42950.0,
    "ema_200": 41200.0,
    "macd": 105.5,
    "macd_signal": 98.2,
    "adx": 28.5,
    "oscillators": {},
    "moving_averages": {}
  }
}
```
#### 6. Hot Movers

**Endpoint:** `/api/hot-movers`  
**Method:** GET  
**Description:** Finds coins that have both high price change and specific BB Rating range in a given timeframe.

**Request Parameters:**
- `timeframe` (query param, default: "5m"): Desired timeframe (5m, 15m, 1h, 4h, 1D)
- `min_change` (query param, default: "3.0"): Minimum percentage change (e.g. 3.0 = 3% and above)
- `min_rating` (query param, default: "2"): Minimum BB Rating value (1, 2, 3 etc.)
- `max_rating` (query param, default: "3"): Maximum BB Rating value (to filter specific rating range)
- `exchange` (query param, default: "kucoin"): Exchange

**Example Usage:**
- To filter coins with BB Rating of 2 only: `/api/hot-movers?min_rating=2&max_rating=2`
- To filter coins with BB Rating of 1 or 2: `/api/hot-movers?min_rating=1&max_rating=2`

**Response:**
```json
{
  "status": "success",
  "timeframe": "5m",
  "exchange": "kucoin",
  "min_change": 3.0,
  "min_rating": 2,
  "max_rating": 2,
  "count": 3,
  "data": [
    {
      "symbol": "KUCOIN:BRWLUSDT",
      "price": 0.001,
      "change": 3.966,
      "bbw": 0.1018,
      "rating": 2,
      "signal": "BUY",
      "volume": 24300,
      "alert_message": "BRWLUSDT 5m zaman diliminde %4.0 yükseldi ve BB Rating 2!"
    },
  
  ]
}
```

### Error Responses

All endpoints will return an error response in the following format:

```json
{
  "status": "error",
  "message": "Error message description"
}
```

Common HTTP status codes:
- 400: Bad Request (missing parameters)
- 401: Unauthorized (invalid or missing API key)
- 404: Not Found (requested resource not found)
- 500: Internal Server Error

## Email Subscription System

The application includes an email subscription system that allows users to receive daily Bollinger Band scan results directly to their inbox.

### Features:

- **Subscribe**: Users can subscribe with their email address from the main page.
- **Automated Emails**: Subscribers receive daily scan results with detailed information about coins that meet the Bollinger Band criteria.
- **Multiple Timeframes**: The emails include scan results for multiple timeframes (4H and 1D).
- **Fear & Greed Index**: Each email includes the current Fear & Greed Index value with visual representation.
- **Unsubscribe**: Users can easily unsubscribe through a link provided in each email.

### How It Works:

1. Users enter their email address in the subscription form on the main page.
2. The system validates the email and adds it to the subscriber database.
3. The cron job runs daily to perform scans and send emails to all active subscribers.
4. Each subscriber receives a personalized email with the latest scan results.

### Subscription Management:

Users can manage their subscription at: `https://crypto-scanner-app.herokuapp.com/subscription`

This page allows users to unsubscribe if they no longer wish to receive scanning emails.
