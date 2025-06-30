from binance.client import Client


def login():
    api_key = 'Make it yours'
    api_secret = 'Make it yours'
    # 创建客户端
    # client = Client(api_key_test, api_secret_test, testnet=True)
    client = Client(api_key, api_secret)
    try:
        if client.get_account():
            # print("login success")
            # 现货钱包
            account_info = client.get_account()
            balances = account_info['balances']
            # 过滤出数量大于 0 的资产，并计算总余额
            non_zero_assets = []
            for asset in balances:
                free = float(asset['free'])
                locked = float(asset['locked'])
                if free > 0 or locked > 0:
                    total = free + locked
                    non_zero_assets.append({
                        'asset': asset['asset'],
                        'total': total
                    })
            print("\nYour assets:")
            for asset in non_zero_assets:
                print(f"{asset['asset']}: {asset['total']}")
        if client.futures_account():
            # 合约钱包
            futures_account = client.futures_account()
            assets = futures_account['assets']
            # 过滤出数量大于 0 的资产
            non_zero_future_assets = [asset for asset in assets if float(asset['walletBalance']) > 0]
            print("\nYour future assets:")
            for asset in non_zero_future_assets:
                print(f"{asset['asset']}: {asset['walletBalance']}")
        return client
    except Exception as e:
        print("login fail!")
        print(f"Error: {e}")
        return None


def show_balance(client):
    balance = client.futures_account()
    assets = balance['assets']
    usdt = next((asset for asset in assets if asset['asset'] == 'USDT'), None)
    usdt_balance = float(usdt['walletBalance'])
    print(usdt_balance)
    return usdt_balance


if __name__ == '__main__':
    login()
