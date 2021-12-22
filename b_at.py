import ccxt 
import time
import datetime
import pandas as pd
import math
import telepot   # telepot 모듈 import 

slow_k=0
slow_d=0
slow_k_30m=0
slow_d_30m=0
macd_osc=0
macd_30m=0
trailing_target=0
trailing_start=0

# 파일로부터 apiKey, Secret 읽기 
with open("binance_api_key.txt") as f:
    lines = f.readlines()
    api_key = lines[0].strip() 
    secret = lines[1].strip() 
    token = lines[2].strip() 
    mc = lines[3].strip() 

bot = telepot.Bot(token) # bot.sendMessage(mc, "test") # 할말 적어서 메시지 보내기 

# binance 객체 생성
binance = ccxt.binance(config={'apiKey': api_key, 'secret': secret, 'enableRateLimit': True, 'options': {'defaultType': 'future'}})
symbol = "BTC/USDT"

# 잔고 조회
balance = binance.fetch_balance(params={"type": "future"})
#print(balance['USDT'])
#balance = binance.fetch_balance()
usdt = balance['total']['USDT']
btc = balance['total']['BTC']

op_mode = False 
position = {"type": None,"amount": 0} 

# 현재가 조회
ticker = binance.fetch_ticker(symbol)




def cal_amount(usdt_balance, cur_price):
    portion = 2 
    usdt_trade = usdt_balance * portion
    #amount = math.floor((usdt_trade * 10000)/cur_price) / 10000
    amount = math.floor((usdt_trade * 1000000)/cur_price) / 1000000
    return amount 


def enter_position(exchange, symbol, cur_price, amount, position):
    global slow_k, slow_d, slow_k_30m, slow_d_30m, bot, macd_30m, trailing_target, macd_osc
    #if macd_30m[-2] < macd_30m[-1] and slow_k_30m[-2] < slow_k_30m[-1] :
    if slow_k[-2] < 50 and slow_k[-2] <= slow_d[-2] and slow_k[-1] > slow_d[-1] and macd_osc[-2] < macd_osc[-1] :
        position['type'] = 'long'
        position['amount'] = amount
        exchange.create_market_buy_order(symbol=symbol, amount=amount)
        trailing_target = cur_price
        bot.sendMessage(mc, "long 진입")
        #time.sleep(1)
    #elif macd_30m[-2] > macd_30m[-1] and slow_k_30m[-2] > slow_k_30m[-1] :
    elif slow_k[-2] > 50 and slow_k[-2] >= slow_d[-2] and slow_k[-1] < slow_d[-1] and macd_osc[-2] > macd_osc[-1] :
        position['type'] = 'short'
        position['amount'] = amount
        exchange.create_market_sell_order(symbol=symbol, amount=amount)
        trailing_target = cur_price
        bot.sendMessage(mc, "short 진입")
        #time.sleep(1)


def exit_position(exchange, symbol, cur_price, ent_price, position, trailing_exit):
    global slow_k, slow_d, slow_k_30m, slow_d_30m, bot
    amount = position['amount']
    if position['type'] == 'long':
        if (slow_k[-2] >= 50 and slow_k[-2] >= slow_d[-2] and slow_k[-1] < slow_d[-1]) or (cur_price > ent_price*1.2) or (cur_price < ent_price*0.9) or (trailing_exit==1) :
            exchange.create_market_sell_order(symbol=symbol, amount=amount)
            position['type'] = None 
            bot.sendMessage(mc, "long 청산")
            #time.sleep(1)
    elif position['type'] == 'short':
        if (slow_k[-2] <= 50 and slow_k[-2] <= slow_d[-2] and slow_k[-1] > slow_d[-1]) or (cur_price > ent_price*1.1) or (cur_price < ent_price*0.8) or (trailing_exit==1) :
            exchange.create_market_buy_order(symbol=symbol, amount=amount)
            position['type'] = None 
            bot.sendMessage(mc, "short 청산")
            #time.sleep(1)

bot.sendMessage(mc, "START")
print("START")
while True: 
    try:
        now = datetime.datetime.now()

        # 과거 조회
        btc_ohlcv = binance.fetch_ohlcv(symbol="BTC/USDT", timeframe='5m', since=None, limit=50)
        df = pd.DataFrame(btc_ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        df.set_index('datetime', inplace=True)
        close = df['close']
        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        ma120 = close.rolling(120).mean()
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1-exp2
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_osc = macd - macd_signal
        Period = 30
        SlowK_period = 3
        SlowD_period = 3
        fast_k = (close - df['low'].rolling(Period).min()) / (df['high'].rolling(Period).max() - df['low'].rolling(Period).min())*100
        slow_k = fast_k.rolling(window=SlowK_period).mean()
        slow_d = slow_k.rolling(window=SlowD_period).mean()

        btc_ohlcv_30m = binance.fetch_ohlcv(symbol="BTC/USDT", timeframe='30m', since=None, limit=50)
        df_30m = pd.DataFrame(btc_ohlcv_30m, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
        df_30m['datetime'] = pd.to_datetime(df_30m['datetime'], unit='ms')
        df_30m.set_index('datetime', inplace=True)
        close_30m = df_30m['close']
        exp1_30m = close_30m.ewm(span=12, adjust=False).mean()
        exp2_30m = close_30m.ewm(span=26, adjust=False).mean()
        macd_30m = exp1_30m-exp2_30m
        macd_signal_30m = macd_30m.ewm(span=9, adjust=False).mean()
        macd_osc_30m = macd_30m - macd_signal_30m
        fast_k_30m = (close_30m - df_30m['low'].rolling(Period).min()) / (df_30m['high'].rolling(Period).max() - df_30m['low'].rolling(Period).min())*100
        slow_k_30m = fast_k_30m.rolling(window=SlowK_period).mean()
        slow_d_30m = slow_k_30m.rolling(window=SlowD_period).mean()

        balance = binance.fetch_balance()
        usdt = balance['total']['USDT']
        btc = balance['total']['BTC']
        positions = balance['info']['positions']
        for c in positions:
            if c["symbol"] == "BTCUSDT":
                btc_position = c
        ent_price = float(btc_position['entryPrice'])
      
        ticker = binance.fetch_ticker(symbol)
        cur_price = float(ticker['last'])
        amount = cal_amount(usdt, cur_price)

        

        #print(amount)

        if position['type'] is None:
            enter_position(binance, symbol, cur_price, amount, position)
            trailing_start =0
            trailing_target=0
            trailing_exit=0
        else:
            if position['type'] == 'long':
                if cur_price >= ent_price*1.06 :
                    trailing_start =1 
                if trailing_start == 1 :
                    if cur_price > trailing_target :
                        trailing_target = cur_price
                    if cur_price <= trailing_target*0.99 :
                        trailing_exit = 1
                    else :
                        trailing_exit = 0
            if position['type'] == 'short':
                if cur_price <= ent_price*0.94 :
                    trailing_start =1 
                if trailing_start == 1 :
                    if cur_price < trailing_target :
                        trailing_target = cur_price
                    if cur_price >= trailing_target*1.01 :
                        trailing_exit = 1
                    else :
                        trailing_exit = 0
            exit_position(binance, symbol, cur_price, ent_price, position, trailing_exit)

       
        time.sleep(1)
    except Exception as e:
        print(str(e))
        bot.sendMessage(mc, str(e))
        time.sleep(1)
