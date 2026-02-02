import logging
import asyncio
import aiocoap.resource as resource
import aiocoap

# 設定日誌
logging.basicConfig(level=logging.INFO)

class BatteryResource(resource.Resource):
    """
    這個資源負責接收來自 ESP32 的模擬電池數據
    """
    def __init__(self):
        super().__init__()
        self.battery_value = "No data yet"

    # 使用 POST 方法接收數據
    async def render_put(self, request):
        # 取得從 ESP32 傳來的 Payload (bytes 格式)
        payload = request.payload.decode('utf-8')
        
        # 在 Terminal 顯示接收到的資訊
        print(f"收到數據: {payload}")
        logging.info(f"Received battery data from {request.remote.hostinfo}: {payload}")

        # 這裡可以加入處理邏輯，例如存入資料庫或分析
        self.battery_value = payload

        # 回傳給 ESP32 的確認訊息
        response_payload = f"Received: {payload}".encode('utf-8')
        return aiocoap.Message(code=aiocoap.Code.CHANGED, payload=response_payload)

    # 保留 GET 方法，方便你在網頁或工具上查看目前的數據
    async def render_get(self, request):
        payload = f"Current Battery Status: {self.battery_value}".encode('utf-8')
        return aiocoap.Message(payload=payload)

async def main():
    # 建立資源樹
    root = resource.Site()
    
    # 修改路徑為 coap://<RPi_IP>/battery
    root.add_resource(['battery'], BatteryResource())

    # 啟動伺服器環境
    # 注意：aiocoap 在新版本建議使用此方式建立 context
    bind_address = "0.0.0.0" # 監聽所有介面
    await aiocoap.Context.create_server_context(root, bind=(bind_address, 5683))
    
    print(f"CoAP Server 已啟動於 {bind_address}:5683")
    print("等待 ESP32 發送電池數據至 /battery ...")
    
    # 保持程式運行
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
