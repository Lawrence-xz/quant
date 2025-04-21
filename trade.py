from datetime import datetime, timedelta
from binance.client import Client
import coins
import asyncio
import joblib
from collections import deque
import time
import math
import supervise
import login
import threading

# 用户配置
API_KEY = 'TCZq0UChOAyfmACk4pOiPBWNEHAp5JT3GjWkymHxW1allGOrFMMMTp9JtBDTMjRN'
API_SECRET = 'FrS1qCToiUxAWoAbCVlXFHN8R0bRMRQd1vZLIXO5Z17xrj8ynrDLDKzJBtGQe8DX'

client = login.login()
# Settings
symbol = 'BTCUSDT'
interval = '1m'
limit = 28  # 最低信息数量
model = joblib.load('D:/Quant/pkls/10minrandom_forest_model.pkl')
features = ['High', 'Low', 'Close', 'Volume', 'RSI', 'Bollinger_Mid', 'Bollinger_Upper',
            'Bollinger_Lower', 'Rsv', 'K', 'D', 'J', 'ADX', 'DI+', 'DI-', 'VWAP', 'VO', 'OBV', 'CMF']
time_interval = 10
buy_count = 0
sell_count = 0
last_lose_time = datetime.strptime("2024-03-09 17:50:00", "%Y-%m-%d %H:%M:%S")
time_diff = 20
now_time = 0
previous_balance = 0
order_queue = deque()

# On running
wins = 0
loses = 0
invalids = 0
lose_stash = 0

# Temp data
last_time = 0
last_price = -1
last_dir = 0


# 合约买多（开多仓）
def place_futures_long(symbol, buy_price , quantity, leverage=None):
    global buy_count, client
    new_id = 'buy' + str(buy_count)
    try:
        if leverage:
            client.futures_change_leverage(symbol=symbol, leverage=leverage)
        order = client.futures_create_order(
            symbol=symbol,
            side='BUY',
            type='LIMIT',
            timeInForce='GTC',
            quantity=quantity,
            price=buy_price,
            positionSide='LONG',
            newClientOrderId=new_id,
        )
        buy_count += 1
        return order
    except Exception as e:
        print(f"Error placing futures long order: {e}")
        return None


# 设置 STOP_MARKET 买多 止损单
def place_stop_market_order(symbol, quantity, stop_price):
    new_id = 'anti_buy' + str(buy_count)
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side="SELL",  # 卖出
            type="STOP_MARKET",  # STOP_MARKET 类型
            quantity=quantity,  # 卖出数量
            stopPrice=stop_price,  # 触发价格
            positionSide="LONG",
            newClientOrderId=new_id,
        )
        return order
    except Exception as e:
        print(f"Error placing STOP_MARKET_LONG order: {e}")
        return None


# 平多仓
def close_futures_long(symbol, quantity):
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side='SELL',
            type='MARKET',
            quantity=quantity,
            positionSide='LONG',
        )
        return order
    except Exception as e:
        print(f"平多错误: {e}")
        return None


# 合约卖空（开空仓）
def place_futures_short(symbol, buy_price, quantity, leverage=None):
    global sell_count
    new_id = 'sell' + str(sell_count)
    try:
        if leverage:
            client.futures_change_leverage(symbol=symbol, leverage=leverage)
        order = client.futures_create_order(
            symbol=symbol,
            side='SELL',
            type='LIMIT',
            timeInForce='GTC',
            quantity=quantity,
            price=buy_price,
            positionSide='SHORT',
            newClientOrderId=new_id,
        )
        sell_count += 1
        return order
    except Exception as e:
        print(f"Error placing futures short order: {e}")
        return None


# 设置 STOP_MARKET 卖空 止损单
def place_stop_market__short_order(symbol, quantity, stop_price):
    new_id = 'anti_sell' + str(sell_count)
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side="BUY",  # 卖出
            type="STOP_MARKET",  # STOP_MARKET 类型
            quantity=quantity,  # 卖出数量
            stopPrice=stop_price,  # 触发价格
            positionSide="SHORT",
            newClientOrderId=new_id
        )
        return order
    except Exception as e:
        print(f"Error placing STOP_MARKET_SHORT order: {e}")
        return None


# 平空仓
def close_futures_short(symbol, quantity):
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side='BUY',
            type='MARKET',
            quantity=quantity,
            positionSide='SHORT',
        )
        return order
    except Exception as e:
        print(f"平空错误: {e}")
        return None


# 即时预测
def instant_prediction(symbol, interval, limit):
    df = coins.get_klines(symbol, interval, limit, client)
    df = df[['Open time', 'High', 'Low', 'Close', 'Volume']]
    df = coins.calculate_rsi(df)
    df = coins.calculate_bollinger_bands(df)
    df = coins.calculate_kdj(df)
    df = coins.calculate_DMI(df)
    df = coins.calculate_VWAP(df)
    df = df.iloc[[-1]]
    x = df[features]
    prediction = model.predict(x)[0]
    return prediction, df['Close'].values[0]


# 异步：等待到下一分钟的第 59 秒
async def wait_until_next_59_second():
    # 获取当前时间
    now = datetime.now()
    # 计算下一分钟的第 59 秒
    next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    target_time = next_minute.replace(second=59)
    # 计算距离目标时间的秒数
    seconds_to_wait = (target_time - now).total_seconds()
    if seconds_to_wait < 0:
        seconds_to_wait += 60  # 如果已经过了第 59 秒，则等待到下一分钟
    print(f"Waiting for {seconds_to_wait:.2f} seconds until {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
    await asyncio.sleep(seconds_to_wait)


# 等到下一分钟的第59秒
def wait_next_59_second():
    # 获取当前时间
    now = datetime.now()
    # 计算下一分钟的第 59 秒
    next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    target_time = next_minute.replace(second=59)
    # 计算距离目标时间的秒数
    seconds_to_wait = (target_time - now).total_seconds()
    if seconds_to_wait < 0:
        seconds_to_wait += 60  # 如果已经过了第 59 秒，则等待到下一分钟
    print(f"Waiting for {seconds_to_wait:.2f} seconds until {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
    time.sleep(seconds_to_wait)


# 查询所有未完成的止损挂单
def get_open_orders(symbol, order_type, position):
    try:
        open_orders = client.futures_get_open_orders(symbol=symbol)
        key_info_list = []
        # 筛选出指定类型的订单
        open_orders = [order for order in open_orders
                       if order["type"] == order_type and order["positionSide"] == position]
        for order in open_orders:
            key_info = {
                "symbol": order["symbol"],
                "clientOrderId": order["clientOrderId"],
                "type": order["type"],
                "side": order["side"],
                "positionSide": order["positionSide"],
                "time": order["time"]
            }
            key_info_list.insert(0, key_info)
        return key_info_list
    except Exception as e:
        print(f"Error fetching open orders: {e}")
        return None


# # 查询特定订单
# def get_order_by_client_id(symbol, client_order_id):
#     try:
#         # 根据 clientOrderId 查询订单
#         order = client.futures_get_order(
#             symbol=symbol,
#             origClientOrderId=client_order_id
#         )
#         key_info = {
#             "symbol": order["symbol"],
#             "clientOrderId": order["clientOrderId"],
#             "type": order["type"],
#             "side": order["side"],
#             "positionSide": order["positionSide"],
#             "time": order["time"]
#         }
#         print(f"Order found: {key_info}")
#         return order
#     except Exception as e:
#         print(f"Error fetching order: {e}")
#         return None

def add_lose_stash():
    global lose_stash, time_diff
    lose_stash += 1
    if lose_stash >= 3:
        time_diff += lose_stash * 10


def place_order(pred, price):
    if pred == 1:
        order = place_futures_long(symbol, price, 0.002, 15)
        if order:
            print("买多")
        else:
            print("下单失败")
    elif pred == -1:
        order = place_futures_short(symbol, price, 0.002, 15)
        if order:
            print("卖空")
        else:
            print("下单失败")


# 取消指定订单
def cancel_order(symbol, order_id=None, client_order_id=None):
    try:
        if order_id:
            # 使用 orderId 取消订单
            response = client.futures_cancel_order(symbol=symbol, orderId=order_id)
        elif client_order_id:
            # 使用 origClientOrderId 取消订单
            response = client.futures_cancel_order(symbol=symbol, origClientOrderId=client_order_id)
        else:
            print("Error: 必须提供 orderId 或 client_order_id")
            return None
        cancel_info = {
            "symbol": response["symbol"],
            "clientOrderId": response["clientOrderId"],
            "type": response["type"],
            "side": response["side"],
            "positionSide": response["positionSide"],
        }
        print(f"Order canceled successfully: {cancel_info}")
        return cancel_info
    except Exception as e:
        print(f"Error canceling order: {e}")
        return None


def default_loop(symbol, time_diff):
    global last_lose_time, last_price, last_dir, last_time, \
        previous_balance, interval, limit, time_interval, now_time, loses, wins, lose_stash, invalids
    while True:
        wait_next_59_second()
        now_time = datetime.now()
        # 10分钟强制平仓逻辑
        if now_time - last_time > timedelta(minutes=time_interval - 1):
            if last_dir == 1:
                close_futures_long(symbol, 0.002)
            if last_dir == -1:
                close_futures_short(symbol, 0.002)
            balance = login.show_balance(client)
            if previous_balance > balance:
                loses += 1
                add_lose_stash()
                last_lose_time = now_time
                print(f'Lose time :  {last_lose_time}')
            elif previous_balance < balance:
                wins += 1
            print(f"Balance : {balance}")
            order_queue.popleft()
            if order_queue:
                earliest_order = order_queue[0]
                last_time = earliest_order[0]
                last_price = earliest_order[1]
                last_dir = earliest_order[2]
            else:
                last_price = -1
                continue
        # 罚时机制
        if now_time - last_lose_time < timedelta(minutes=time_diff):
            continue
        pred, price = instant_prediction(symbol, interval, limit)
        price = shape_price(price)
        # 处理初始状态，没有订单
        if last_price < 0:
            if pred == 0:
                invalids += 1
                continue
            place_order(pred, price)
            last_dir = pred
            last_price = price
            last_time = now_time
            order_queue.append((last_time, last_price, last_dir))
            continue
        # 控制同时持仓的订单数量
        if len(order_queue) >= 8:
            continue
        # 下单行为
        if pred == 0:
            invalids += 1
            continue
        place_order(pred, price)
        this_dir = pred
        this_price = price
        this_time = now_time
        order_queue.append((this_time, this_price, this_dir))
        print(wins, loses, invalids)


def shape_price(number):
    return math.floor(number * 10) / 10


def run_ws_service(ws_service):
    try:
        asyncio.run(ws_service.start())
    except KeyboardInterrupt:
        print("手动终止程序")
        ws_service.stop()


def run_trade_loop():
    """
    启动交易循环。
    """
    try:
        default_loop()  # 启动交易器
    except KeyboardInterrupt:
        print("手动终止交易循环")


def on_stop_market():
    # 更新last_lose_time
    global now_time, last_lose_time, loses, lose_stash, order_queue, last_time, last_price, last_dir
    last_lose_time = now_time
    loses += 1
    add_lose_stash()
    order_queue.popleft()
    if order_queue:
        earliest_order = order_queue[0]
        last_time = earliest_order[0]
        last_price = earliest_order[1]
        last_dir = earliest_order[2]
    else:
        last_price = -1
    balance = login.show_balance(client)
    print(f'Forced Lose time :  {last_lose_time}')
    print(f"Balance : {balance}")


def on_filled(price, position, side):
    # 下止损单
    global symbol
    anti_order = 0
    if position == "LONG" and side == "BUY":
        anti_order = place_stop_market_order(symbol, 0.002, price - 50)
    elif position == "SHORT" and side == "SELL":
        anti_order = place_stop_market__short_order(symbol, 0.002, price + 50)
    if anti_order:
        print("限价止损成功")
    else:
        print("限价止损失败")


def on_close_position(position, side):
    stop_orders = []
    if position == "SHORT" and side == "BUY":
        stop_orders = get_open_orders(symbol, "STOP_MARKET", position)
    elif position == "LONG" and side == "SELL":
        stop_orders = get_open_orders(symbol, "STOP_MARKET", position)
    if stop_orders:
        latest_order = stop_orders[-1]
        cancel_order(symbol, client_order_id=latest_order['clientOrderId'])
    else:
        print("Error cancel stop market")


if __name__ == '__main__':
    pass
    # ws_service = supervise.WebSocketService(api_key=API_KEY, api_secret=API_SECRET)
    # ws_service.register_callback("on_stop_market", on_stop_market)
    # ws_service.register_callback("on_filled", on_filled)
    # ws_service.register_callback("on_close_position", on_close_position)
    # # 创建线程
    # ws_thread = threading.Thread(target=run_ws_service, args=(ws_service,), daemon=True)
    # trade_thread = threading.Thread(target=run_trade_loop, daemon=True)
    # # 启动线程
    # ws_thread.start()
    # trade_thread.start()
    # print("监控器和交易器已启动，按 Ctrl+C 终止程序...")
    # try:
    #     # 主线程等待子线程运行
    #     ws_thread.join()
    #     trade_thread.join()
    # except KeyboardInterrupt:
    #     print("手动终止程序")
    #     ws_service.stop()
    # previous_balance = show_balance()
    # asyncio.run(trading_loop())
