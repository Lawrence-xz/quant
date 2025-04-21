from login import login
import pandas as pd
import ta
import time


# 获取 BTC/USDT 的每分钟 K 线数据
def get_klines(symbol, interval, limit, client):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        'Open time',
        'Open', 'High', 'Low',
        'Close',
        'Volume',
        'Close time', 'Quote asset volume', 'Number of trades',
        'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
    ])

    # 转换数据类型
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
    df['Open'] = df['Open'].astype(float)
    df['High'] = df['High'].astype(float)
    df['Low'] = df['Low'].astype(float)
    df['Close'] = df['Close'].astype(float)
    df['Volume'] = df['Volume'].astype(float)
    df['Taker buy base asset volume'] = df['Taker buy base asset volume'].astype(float)
    return df


def calculate_rsi(df, period=6):
    df['RSI'] = ta.momentum.rsi(df['Close'], window=period)
    return df


def calculate_bollinger_bands(df, period=25, std_dev=2):
    df['Bollinger_Mid'] = df['Close'].rolling(window=period).mean()
    df['Bollinger_Upper'] = df['Bollinger_Mid'] + std_dev * df['Close'].rolling(window=period).std()
    df['Bollinger_Lower'] = df['Bollinger_Mid'] - std_dev * df['Close'].rolling(window=period).std()
    return df


def calculate_kdj(df, n=7, m1=3, m2=3):
    # 计算 RSV
    lowest_low = df['Low'].rolling(window=n).min()
    highest_high = df['High'].rolling(window=n).max()
    df['Rsv'] = (df['Close'] - lowest_low) / (highest_high - lowest_low) * 100
    # 初始化 K, D, J
    df['K'] = 0
    df['D'] = 0
    df['J'] = 0
    # 计算 K, D, J
    for i in range(len(df)):
        if i < n - 1:
            # 前 n-1 天无法计算 KDJ，设为 NaN
            df.loc[i, 'K'] = None
            df.loc[i, 'D'] = None
            df.loc[i, 'J'] = None
        elif i == n - 1:
            # 第 n 天初始化 K 和 D
            df.loc[i, 'K'] = 50  # K 初始值
            df.loc[i, 'D'] = 50  # D 初始值
            df.loc[i, 'J'] = 3 * df.loc[i, 'K'] - 2 * df.loc[i, 'D']
        else:
            # 计算 K, D, J
            df.loc[i, 'K'] = (2 / 3) * df.loc[i - 1, 'K'] + (1 / 3) * df.loc[i, 'Rsv']
            df.loc[i, 'D'] = (2 / 3) * df.loc[i - 1, 'D'] + (1 / 3) * df.loc[i, 'K']
            df.loc[i, 'J'] = 3 * df.loc[i, 'K'] - 2 * df.loc[i, 'D']

    return df


def calculate_DMI(df, period=25):
    # 计算 ADX 和 DI+、DI-
    adx_indicator = ta.trend.ADXIndicator(
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        window=14
    )
    df['ADX'] = adx_indicator.adx()
    df['DI+'] = adx_indicator.adx_pos()
    df['DI-'] = adx_indicator.adx_neg()
    return df


def calculate_VWAP(df):
    # 计算 VWAP  成交量加权平均价格
    vwap_indicator = ta.volume.VolumeWeightedAveragePrice(
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        volume=df['Volume']
    )
    df['VWAP'] = vwap_indicator.volume_weighted_average_price()

    # 计算 VO (短期窗口 3，长期窗口 5) 成交量震荡指标
    short_window = 3
    long_window = 5

    short_ma = df['Volume'].rolling(window=short_window).mean()
    long_ma = df['Volume'].rolling(window=long_window).mean()

    df['VO'] = (short_ma - long_ma) / long_ma * 100

    # 计算 OBV 能量潮指标
    obv_indicator = ta.volume.OnBalanceVolumeIndicator(
        close=df['Close'],
        volume=df['Volume']
    )
    df['OBV'] = obv_indicator.on_balance_volume()

    # 计算 CMF (以 3 天为周期) 成交量平衡指标 用于衡量资金流入流出
    cmf_indicator = ta.volume.ChaikinMoneyFlowIndicator(
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        volume=df['Volume'],
        window=3
    )
    df['CMF'] = cmf_indicator.chaikin_money_flow()

    return df


# 获取 BTC/USDT 多条数据
def get_recent_klines(symbol, interval, total_limit):
    all_klines = []
    limit_per_request = 1000  # 每次请求的最大限制
    end_time = None  # 初始化结束时间为 None

    while len(all_klines) < total_limit:
        try:
            # 如果是第一次请求，从最近的时间开始
            if not end_time:
                klines = client.futures_klines(symbol=symbol, interval=interval, limit=limit_per_request)
            else:
                # 后续请求时，指定结束时间为上一次的第一个时间点 - 1ms
                klines = client.get_klines(
                    symbol=symbol,
                    interval=interval,
                    endTime=int(all_klines[0][0]) - 1,  # 上一次第一个时间点减去 1ms
                    limit=limit_per_request
                )

            if not klines:  # 如果没有更多数据，退出循环
                break

            # 将当前批次的数据插入到总数据的开头（倒序拼接）
            all_klines = klines + all_klines

            # 更新结束时间
            end_time = int(all_klines[0][0])


            # 防止请求过快被限流
            time.sleep(0.1)

        except Exception as e:
            print(f"Error occurred: {e}")
            break

    # 转换为 DataFrame
    df = pd.DataFrame(all_klines, columns=[
        'Open time',
        'Open', 'High', 'Low', 'Close',
        'Volume',
        'Close time', 'Quote asset volume', 'Number of trades',
        'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
    ])

    # 转换数据类型
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
    df['Open'] = df['Open'].astype(float)
    df['High'] = df['High'].astype(float)
    df['Low'] = df['Low'].astype(float)
    df['Close'] = df['Close'].astype(float)
    df['Volume'] = df['Volume'].astype(float)

    # 按照时间排序并去重
    df.drop_duplicates(subset='Open time', inplace=True)
    df.sort_values(by='Open time', ascending=False, inplace=True)  # 倒序排列

    # 返回前 total_limit 条数据
    return df.iloc[:total_limit]


def fetch_data(symbol='BTCUSDT', interval='1m', total_limit=1000):
    df = get_recent_klines(symbol, interval, total_limit)
    df = df[['Open time', 'High', 'Low', 'Close', 'Volume', 'Number of trades', 'Taker buy base asset volume']]
    df = df.iloc[::-1].reset_index(drop=True)
    df = calculate_rsi(df)
    df = calculate_bollinger_bands(df)
    df = calculate_kdj(df)
    df = calculate_DMI(df)
    df = calculate_VWAP(df)
    df = df.dropna()
    df.to_csv(f'../datas/{symbol}_{interval}_{total_limit}.csv', index=False)
    print(f"Total rows: {len(df)}")
    print(df.columns)
    return df


if __name__ == '__main__':
    client = login()
    fetch_data('BTCUSDT', '1m', 100000)

