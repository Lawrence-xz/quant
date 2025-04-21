import pandas as pd
from draw import draw_net_value, draw_win_lose_dash
import joblib
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field
from analyze import analyze_index_distribution
from MLmodel import load_models, truncate_time, pred
features = ['High', 'Low', 'Close', 'Volume', 'Number of trades', 'Taker buy base asset volume', 'RSI',
            'Bollinger_Mid', 'Bollinger_Upper', 'Bollinger_Lower', 'Rsv',
            'K', 'D', 'J', 'ADX', 'DI+', 'DI-', 'VWAP', 'VO', 'OBV', 'CMF']


@dataclass
class Order:
    time: str
    price: float
    dir: int


def prepare_data():
    data_url = "../datas/btc_coins_for_train.csv"
    data_url_15MIN = "../datas/btc_usdt_15MIN_coins_for_train.csv"
    df = pd.read_csv(data_url)
    df = df[290000:291000]
    df_15MIN = pd.read_csv(data_url_15MIN)
    df['Open time'] = pd.to_datetime(df['Open time'])
    df_15MIN['Open time'] = pd.to_datetime(df_15MIN['Open time'])
    df = df.reset_index(drop=True)
    df, df_15MIN = truncate_time(df, df_15MIN)
    df_15MIN = df_15MIN.reset_index(drop=True)
    return df, df_15MIN


df, df_15MIN = prepare_data()
last_time = datetime.strptime("2024-03-09 17:50:00",
                              "%Y-%m-%d %H:%M:%S")  # just an old time, nothing special for 2024.03.09

meta_order = Order("0", -1, 0)
order_queue = deque()
order_queue.append(meta_order)

time_diff_meta = 3
time_diff_meta_wrong_lose = 15
time_diff_meta_lack_lose = 18


model_15MIN = joblib.load("/pkls/BTCUSDT_15MIN_100margin_large_random_forest_model.pkl")


def check_meta():
    models = load_models("BTCUSDT")
    df['Close_10_min_later'] = df['Close'].shift(-10)
    check_win = 0
    check_lack_lose = 0
    check_lose = 0
    check_invalid = 0
    check_wrong_lose = 0
    win = []
    lack_lose = []
    lose = []
    wrong_lose = []
    invalid = []
    # for index, row in df.iterrows():
    #     X = pd.DataFrame([row[features]], columns=features)
    #     pre = pred(X)
    #     if pre == 1:
    #         if (row['Close_10_min_later'] - row['Close']) >= 2:
    #             check_win += 1
    #         elif (row['Close_10_min_later'] - row['Close']) >= 0:
    #             check_lack_lose += 1
    #         elif (row['Close_10_min_later'] - row['Close']) <= -2:
    #             check_wrong_lose += 1
    #         else:
    #             check_lose += 1
    #     if pre == -1:
    #         if (row['Close'] - row['Close_10_min_later']) >= 2:
    #             check_win += 1
    #         elif (row['Close'] - row['Close_10_min_later']) >= 0:
    #             check_lack_lose += 1
    #         elif (row['Close'] - row['Close_10_min_later']) <= -2:
    #             check_wrong_lose += 1
    #         else:
    #             check_lose += 1
    #     if pre == 0:
    #         check_invalid += 1
    i = 6
    j = 0
    lens = len(df)
    while i < lens:
        X_list = []
        for offset in range(6):  # 从 i-5 到 i 共6个时间点
            row_df = df.loc[i - offset:i - offset, features]
            X_list.append(row_df.reset_index(drop=True))
        if df.loc[i, 'Open time'] - df_15MIN.loc[j, 'Open time'] > timedelta(minutes=15):
            print("time changed")
            j += 1
        x_15 = df_15MIN.loc[j:j, features]
        pre15 = model_15MIN.predict(x_15)
        pre = pred(models, X_list)
        if pre15 < 2:
            print("this not pre15")
            pre = 0
        # 根据预测结果进行分类统计
        if pre == 1:
            if (df.loc[i, 'Close_10_min_later'] - df.loc[i, 'Close']) >= 100:
                check_win += 1
                win.append(i)
            elif (df.loc[i, 'Close_10_min_later'] - df.loc[i, 'Close']) >= 0:
                check_lack_lose += 1
                lack_lose.append(i)
                i += time_diff_meta_lack_lose
                continue
            elif (df.loc[i, 'Close_10_min_later'] - df.loc[i, 'Close']) <= -100:
                check_wrong_lose += 1
                wrong_lose.append(i)
                i += time_diff_meta_wrong_lose
                continue
            else:
                check_lose += 1
                lose.append(i)
                i += time_diff_meta
                continue
        if pre == -1:
            if (df.loc[i, 'Close'] - df.loc[i, 'Close_10_min_later']) >= 100:
                check_win += 1
                win.append(i)
            elif (df.loc[i, 'Close'] - df.loc[i, 'Close_10_min_later']) >= 0:
                check_lack_lose += 1
                lack_lose.append(i)
                i += time_diff_meta_lack_lose
                continue
            elif (df.loc[i, 'Close'] - df.loc[i, 'Close_10_min_later']) <= -100:
                check_wrong_lose += 1
                wrong_lose.append(i)
                i += time_diff_meta_wrong_lose
                continue
            else:
                check_lose += 1
                lose.append(i)
                i += time_diff_meta
                continue
        elif pre == 0:
            check_invalid += 1
            invalid.append(i)
        i += 1
    print(f"win: {check_win}, lose: {check_lose}, lack_lose: {check_lack_lose}, wrong_lose: {check_wrong_lose}, "
          f"invalid: {check_invalid}")
    print(f"win rate: {check_win / (check_win + check_lose + check_lack_lose + check_wrong_lose)}")
    total_lose = lose + lack_lose + wrong_lose
    # 分析索引分布
    analyze_index_distribution(win)
    analyze_index_distribution(lose)
    analyze_index_distribution(lack_lose)
    analyze_index_distribution(wrong_lose)
    analyze_index_distribution(invalid)
    analyze_index_distribution(total_lose)
    # 将所有列表组合在一起
    # 将所有列表存入 all_lists
    # all_lists = [win, lose, lack_lose, wrong_lose]
    all_lists = [win, lose, lack_lose, wrong_lose, invalid]
    # 颜色列表
    colors = ['red', 'blue', 'green', 'orange', 'purple']
    draw_win_lose_dash(all_lists, colors)


def mock_loop():
    money = 10000
    proportion = 0.09
    lose_stash = 0
    l_time = 0
    last_price = -1
    last_dir = 0
    order_limit = 8
    time_interval = 10
    delta_threshold = 50
    win_count = 0
    lose_count = 0
    invalids = 0
    deltas = []
    time_diff = 20
    is_punishing = 0
    i = 6
    lens = len(df)
    while i < lens:
        row = df.iloc[i]
        delta = 0
        now_time = datetime.strptime(row['Open time'], "%Y-%m-%d %H:%M:%S")
        X = pd.DataFrame([row[features]], columns=features)
        # 检查订单队列是否需要处理
        if l_time and order_queue:
            if now_time - l_time >= timedelta(minutes=time_interval):
                price_delta = row['Close'] - last_price
                change_pct = price_delta / last_price
                if last_dir == 1:
                    delta = money * proportion * (change_pct * 10 - 0.01)
                elif last_dir == -1:
                    delta = money * proportion * (-change_pct * 10 - 0.01)
                order_queue.popleft()
                print(f"buy time: {l_time}")
                if order_queue:
                    earliest_order = order_queue[0]
                    l_time, last_price, last_dir = earliest_order
                else:
                    last_price = -1
        # 遍历订单队列，检查是否触发条件
        j = 0
        while j < len(order_queue):
            if j >= len(order_queue):
                break
            order = order_queue[j]
            n_time, n_price, n_dir = order
            if n_dir == 1 and n_price - row['Low'] >= delta_threshold:
                price_delta = row['Low'] - last_price
                change_pct = price_delta / last_price
                delta = money * proportion * (change_pct * 10 - 0.001)
                print(f"buy time: {n_time}")
                del order_queue[j]
                if not order_queue:
                    last_price = -1
                    break
                if j == 0:
                    earliest_order = order_queue[0]
                    l_time, last_price, last_dir = earliest_order
            elif n_dir == -1 and row['High'] - last_price >= delta_threshold:
                price_delta = row['Close'] - last_price
                change_pct = price_delta / last_price
                delta = money * proportion * (-change_pct * 10 - 0.001)
                print(f"buy time: {n_time}")
                del order_queue[j]
                if not order_queue:
                    last_price = -1
                    break
                if j == 0:
                    earliest_order = order_queue[0]
                    l_time, last_price, last_dir = earliest_order
            else:
                j += 1

        # 更新资金余额和统计信息
        money += delta
        if delta > 0:
            win_count += 1
            lose_stash = 0
            order_limit += 1
            if time_diff > 20:
                time_diff -= 10
        elif delta < 0:
            lose_count += 1
            lose_stash += 1
            if lose_stash > 4:
                time_diff = 60
            print(f"lose_stash: {lose_stash}")
            print(row['Open time'])

        if delta != 0:
            print(f"资产余额: {money}, delta: {delta}")
        deltas.append(delta)
        # 惩罚状态管理
        punish_status = is_punishing
        if now_time - (l_time or now_time) < timedelta(minutes=time_diff):
            is_punishing = True
            deltas.append(delta)
            i += 1
            continue
        is_punishing = False
        if punish_status and not is_punishing:
            order_limit = 1
        # 如果没有有效订单，尝试添加新订单
        if last_price < 0:
            temp_dir = model10.predict(X)[0]
            if temp_dir == 0:
                invalids += 1
                i += 1
                continue
            last_dir = temp_dir
            last_price = row['Close']
            l_time = now_time
            order_queue.append((l_time, last_price, last_dir))
            i += 1
            continue
        # 如果订单数量已达到限制，跳过当前循环
        if len(order_queue) >= order_limit:
            i += 1
            continue

        # 添加新订单
        this_dir = model10.predict(X)[0]
        if this_dir == 0:
            invalids += 1
            i += 1
            continue
        this_price = row['Close']
        this_time = now_time
        order_queue.append((this_time, this_price, this_dir))
        # 移动到下一行
        i += 1
    print(win_count, lose_count, invalids)
    draw_net_value(deltas)


if __name__ == '__main__':
    check_meta()
