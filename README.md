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
Before the project can be run with Docker, a Docker image must be created. You can use the following constraint for this:
```bash
  docker build -t cryptoscreener .
```
Run docker on localhost:5000
 ```bash
  docker run -d -p 5000:5000 cryptoscreener
```
Go to to http://localhost:5000
