import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.ensemble import RandomForestClassifier, BaggingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
from multiprocessing import Process, Manager
import logging


features = ['High', 'Low', 'Close', 'Volume', 'Number of trades', 'Taker buy base asset volume', 'RSI',
            'Bollinger_Mid', 'Bollinger_Upper', 'Bollinger_Lower', 'Rsv',
            'K', 'D', 'J', 'ADX', 'DI+', 'DI-', 'VWAP', 'VO', 'OBV', 'CMF']

file_suffix = "random_forest_model.pkl"

# 配置日志记录
def setup_logger(log_file):
    logger = logging.getLogger("ModelLogger")
    logger.setLevel(logging.INFO)

    # 确保logger没有重复的handlers
    if not logger.handlers:
        # 创建文件处理器，并设置为追加模式
        file_handler = logging.FileHandler(log_file, mode='a')  # 使用'a'表示追加模式
        file_handler.setLevel(logging.INFO)

        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        # 将处理器添加到日志器
        logger.addHandler(file_handler)
    return logger


def bagging_pred(X_train, y_train, X_test, y_test):
    bag = BaggingClassifier(DecisionTreeClassifier(), n_estimators=500, oob_score=True, max_samples=0.2,
                            bootstrap=True, n_jobs=-1)
    bag.fit(X_train, y_train)
    bag_pred = bag.predict(X_test)
    bag_accuracy = accuracy_score(y_test, bag_pred)
    print(f"bagging模型准确度: {bag_accuracy * 100:.2f}%")
    print(bag.oob_decision_function_[:3])
    return bag


def pasting_pred(X_train, y_train, X_test, y_test):
    pas = BaggingClassifier(DecisionTreeClassifier(), n_estimators=500, max_samples=0.002,
                            bootstrap=False, n_jobs=-1)
    pas.fit(X_train, y_train)
    pas_pred = pas.predict(X_test)
    pas_accuracy = accuracy_score(y_test, pas_pred)
    print(f"pasting模型准确度: {pas_accuracy * 100:.2f}%")
    return pas


def random_forest_head(data, time_interval, margin):
    df = data
    df['Close_later'] = df['Close'].shift(-time_interval)
    df.dropna()
    # 定义多个条件
    conditions = [
        (df['Close_later'] - df['Close']) >= margin,  # 10分钟后价格比当前高100点
        (df['Close_later'] - df['Close']) <= -margin  # 10分钟后价格比当前低100点
    ]
    # 定义每个条件对应的值
    choices = [1, -1]
    # 使用 np.select 根据条件选择值，默认值为 0
    df['Price_later'] = np.select(conditions, choices, default=0)
    df.drop(columns=['Close_later'], inplace=True)
    return df
# return df


def random_forest_15min_head(data, margin):
    # 15分种的k线用于识别波动幅度，如果幅度不够则认为该时段不适合交易
    df = data
    df["Later_high"] = df['High'].shift(-1)
    df["Later_low"] = df['Low'].shift(-1)
    df.dropna()
    conditions = [
        (df['Later_high'] - df['Close']) >= margin,  # Later_high - Close 大于等于 margin，即认为有上涨行情
        (df['Later_low'] - df['Close']) <= -margin  # Later_low - Close 小于等于 -margin，即认为有下跌行情
    ]
    choices = [1, -1]
    df['Price_later'] = np.select(conditions, choices, default=0)
    # 检查是否同时满足两个条件（即值为 2 的情况，此时最高点为上涨行情，最低点为下跌行情）
    df['Price_later'] = np.where(
        (df['Later_high'] - df['Close'] >= margin) &
        (df['Later_low'] - df['Close'] <= -margin),
        2,  # 同时满足两种情况时赋值为 2
        df['Price_later']  # 否则保留之前的值
    )
    return df
# return df


def random_forest(symbol, head_data, time_interval, margin):
    # 使用合适的特征列作为输入数据
    df = head_data
    X = df[features]
    y = df['Price_later']
    # 留最后1w条做测试
    split_index = len(df)-10000
    # X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    X_train = X[:split_index]
    y_train = y[:split_index]
    X_test = X[split_index:]
    y_test = y[split_index:]
    # # # 使用TimeSeriesSplit
    # tscv = TimeSeriesSplit(n_splits=144)  # 你可以根据需要调整n_splits的数量
    logger.info("Start training")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    logger.info("Training Finished")
    # # 进行交叉验证并计算平均准确率
    # scores = cross_val_score(model, X, y, cv=tscv, scoring='accuracy')
    # print(f"cross_val_score: {scores}")
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"{time_interval}min, margin: {margin}")
    logger.info(f"模型准确度: {accuracy * 100:.2f}%")
    logger.info("\n分类报告:")
    logger.info(classification_report(y_test, y_pred))
    cm = confusion_matrix(y_test, y_pred)
    logger.info("混淆矩阵：\n%s", cm)
    # 保存模型
    joblib.dump(model, f'../pkls/{symbol}_{time_interval}min_{file_suffix}')


def single_process(symbol, data, data_15min):
    if not len(data):
        data = pd.read_csv(f"../datas/{symbol}_1m_100000.csv")  # 默认训练数据是10w; default training data length is 100,000
    if not len(data_15min):
        data_15min = pd.read_csv(f"../datas/{symbol}_15m_100000.csv")
    margin = data['Close'].max()/1000  # trading fee is 1/1000 of price
    head_data = random_forest_head(data, 10, margin)
    random_forest(symbol, head_data, 10, margin)
    head_data_15min = random_forest_15min_head(data_15min, margin)
    random_forest(symbol, head_data_15min, 1, margin)


def load_models(symbol):
    time_intervals = [10, 11, 12, 13, 14, 15]
    model_files = []
    for interval in time_intervals:
        file_name = f"../pkls/{symbol}_{interval}min_{file_suffix}"
        model_files.append(file_name)
    models = []
    for path in model_files:
        try:
            model = joblib.load(path)
            models.append(model)
        except Exception as e:
            print(f"加载模型 {path} 时出错: {e}")
    return models


def truncate_time(df, df_15MIN):
    start1, end1 = df['Open time'].min(), df['Open time'].max()
    start2, end2 = df_15MIN['Open time'].min(), df_15MIN['Open time'].max()
    overlap_start = max(start1, start2)
    df1_aligned = df[df['Open time'] >= overlap_start]
    df2_aligned = df_15MIN[df_15MIN['Open time'] >= overlap_start]
    return df1_aligned, df2_aligned


def pred(models, X_list, threshold=0.65):
    if len(models) != len(X_list):
        raise ValueError("模型数量和输入数据数量不匹配！")
    # 计算所有模型的预测值的平均值
    total_pred = 0
    for i, model in enumerate(models):
        try:
            pred_value = model.predict(X_list[i])[0]  # 获取单个预测值
            total_pred += pred_value
        except Exception as e:
            print(f"模型 {i} 预测时出错: {e}")
    total_pred /= len(models)

    if total_pred > threshold:
        return 1
    elif total_pred < threshold:
        return -1
    else:
        return 0



if __name__ == '__main__':
    # 初始化日志器
    log_file = "../scripts/random_forest_training.log"
    logger = setup_logger(log_file)

    df = pd.read_csv("../datas/BTCUSDT_1m_100000.csv")
    df_15min = pd.read_csv("../datas/btc_usdt_15MIN_coins_for_train.csv")
    print(df)
    print(df_15min)
    # single_process('BTCUSDT', "", "")   #also can be used like this
    single_process('BTCUSDT', df, df_15min)

    # processes = []
    # 使用 Manager 创建共享数据
    # with Manager() as manager:
    #     # 循环创建进程
    #     for time in range(10, 15):
    #         process = Process(target=random_forest, args=(time, 100, "BTCUSDC"))
    #         processes.append(process)
    #         process.start()
    #     # 等待所有进程完成
    #     for process in processes:
    #         process.join()
    # random_forest_15min(100, "BTCUSDT")
