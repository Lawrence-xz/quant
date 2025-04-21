from binance.client import Client


def login():
    api_key = 'TCZq0UChOAyfmACk4pOiPBWNEHAp5JT3GjWkymHxW1allGOrFMMMTp9JtBDTMjRN'
    api_secret = 'FrS1qCToiUxAWoAbCVlXFHN8R0bRMRQd1vZLIXO5Z17xrj8ynrDLDKzJBtGQe8DX'
    # api_key_second = 'BIDKZSCg5CVlvTuCQvSn2CnoU2d1OdPmAP9NnzR3jk40RjLFxbmLhHxVklC0j6N2'
    # api_secret_second = 'D0ADRuHXsMFwURkU3rNuCqyTYJ4MprpOfYINpu1d4jHIcp95juUF1xxhmv9hg2dX'
    # api_key_test = '3b6cf02793065b4cf2ee51083ced6ab6a04d04ce8c7a0b4bad61fb09faff02bb'
    # api_secret_test = '29d3d35fd6dfad54664a4d704fd8f3ae22e0f052685afed09a6779c00d411ed7'
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
