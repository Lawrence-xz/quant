import json
import asyncio
import websockets
from datetime import datetime, timezone
from binance.client import Client
# 用户配置
API_KEY = 'TCZq0UChOAyfmACk4pOiPBWNEHAp5JT3GjWkymHxW1allGOrFMMMTp9JtBDTMjRN'
API_SECRET = 'FrS1qCToiUxAWoAbCVlXFHN8R0bRMRQd1vZLIXO5Z17xrj8ynrDLDKzJBtGQe8DX'


# def send_notification(order):
#     # 发送通知的函数示例
#     print(f"发送通知 - 订单ID: {order['i']} 已完全成交！")
#     # 在这里实现发送邮件、短信、推送通知等逻辑
#     pass


class WebSocketService:
    def __init__(self, api_key, api_secret):
        self.listen_key = None
        self.running = False
        self.callbacks = {}
        self.api_key = api_key
        self.api_secret = api_secret

    async def _get_listen_key(self):
        """
        获取 ListenKey。
        """
        client = Client(self.api_key, self.api_secret)
        self.listen_key = client.futures_stream_get_listen_key()
        print(f"Listen Key: {self.listen_key}")
        return self.listen_key

    def register_callback(self, condition, callback):
        self.callbacks[condition] = callback

    def _trigger_callback(self, condition, *args, **kwargs):
        if condition in self.callbacks:
            self.callbacks[condition](*args, **kwargs)

    async def _handle_order_update(self, order_data):
        """
        处理订单更新事件。
        """
        order = order_data["o"]
        symbol = order["s"]  # 交易对
        order_id = order["c"]  # 订单 ID
        status = order["X"]  # 订单状态 (NEW, FILLED, CANCELED 等)
        side = order["S"]  # 方向 (BUY, SELL)
        order_type = order["o"]
        quantity = order["q"]  # 订单数量
        executed_quantity = order["z"]  # 已执行数量
        price = order["p"]  # 订单价格
        position = order["ps"]

        print(f"订单更新 - 交易对: {symbol}, 订单ID: {order_id}, 状态: {status}, 类型: {order_type}, 方向: {side}")
        print(f"数量: {quantity}, 已执行数量: {executed_quantity}, 价格: {price}, 持仓方向: {position}")

        if status == "FILLED" and order_type == "STOP_MARKET":
            self._trigger_callback("on_stop_market")

        if status == "FILLED" and order_type == "LIMIT":
            self._trigger_callback("on_filled", price, position, side)

        if status == "FILLED" and order_type == "MARKET":
            self._trigger_callback("on_close_position", position, side)






    async def _listen_to_user_data(self):
        """
        监听用户数据流（包括订单更新、账户更新等）。
        """
        uri = f"wss://fstream.binance.com/ws/{self.listen_key}"
        async with websockets.connect(uri) as websocket:
            print("WebSocket 连接已建立，开始监听用户数据...")
            while self.running:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    event_type = data.get("e")
                    if event_type == "ORDER_TRADE_UPDATE":
                        await self._handle_order_update(data)
                    elif event_type == "ACCOUNT_UPDATE":
                        print("账户更新")
                    else:
                        print(f"收到未知事件: {event_type}")
                except websockets.ConnectionClosed:
                    print("连接已关闭，尝试重连...")
                    break
                except Exception as e:
                    print(f"发生异常: {e}")

    async def _refresh_listen_key(self):
        client = Client(API_KEY, API_SECRET)
        while self.running:
            try:
                print("正在刷新 ListenKey...")
                self.listen_key = client.futures_stream_keepalive(self.listen_key)["listenKey"]
                print(f"ListenKey 刷新成功: {self.listen_key}")
            except Exception as e:
                print(f"刷新 ListenKey 时发生错误: {e}")
            await asyncio.sleep(1800)  # 每 30 分钟刷新一次

    async def _run_websocket(self):
        while self.running:
            try:
                if not self.listen_key:
                    self.listen_key = self._get_listen_key()  # 初始化 ListenKey

                print(self.listen_key)
                await self._listen_to_user_data()
            except Exception as e:
                print(f"WebSocket 发生错误: {e}")
                print("将在 5 秒后重试...")
                await asyncio.sleep(5)

    def start(self):
        self.running = True
        print("正在启动 WebSocket 服务...")
        # 获取初始 ListenKey

        asyncio.run(self._main())

    async def _main(self):
        """
        主程序入口，同时运行 ListenKey 刷新和 WebSocket 监听
        """
        await self._get_listen_key()
        refresh_task = asyncio.create_task(self._refresh_listen_key())  # 后台刷新 ListenKey
        websocket_task = asyncio.create_task(self._run_websocket())     # 启动 WebSocket 监听
        await asyncio.gather(refresh_task, websocket_task)

    def stop(self):
        """
        停止 WebSocket 服务
        """
        self.running = False
        print("WebSocket 服务已停止")


# 主程序入口
if __name__ == "__main__":
    try:
        ws_service = WebSocketService(api_key=API_KEY, api_secret=API_SECRET)
        ws_service.start()
    except KeyboardInterrupt:
        print("手动终止程序")
        ws_service.stop()