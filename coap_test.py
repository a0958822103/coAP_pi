import logging
import asyncio
import aiocoap.resource as resource
import aiocoap

# 設定日誌，讓我們能在 Terminal 看到連線紀錄
logging.basicConfig(level=logging.INFO)
logging.getLogger("coap-server").setLevel(logging.INFO)

class TimeResource(resource.ObservableResource):
    """
    這是一個簡單的資源，當 Client 請求時會回傳「Hello from Raspberry Pi!」
    """
    async def render_get(self, request):
        payload = b"Hello from Raspberry Pi! CoAP is working!"
        return aiocoap.Message(payload=payload)

def main():
    # 建立資源樹 (Resource Tree)
    root = resource.Site()
    
    # 這裡定義了資源的路徑： coap://<RPi_IP>/test
    root.add_resource(['test'], TimeResource())

    # 啟動伺服器
    asyncio.Task(aiocoap.Context.create_server_context(root))
    print("CoAP Server 已啟動，等待 ESP32 連線...")
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    main()
