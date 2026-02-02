import asyncio
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO
import aiocoap.resource as resource
import aiocoap
from flask import jsonify
import csv
import os
from datetime import datetime

# --- Flask & Socket.IO 設定 ---
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_history')
def get_history():
    history = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r') as f:
            reader = csv.DictReader(f)
            # 只取最後 50 筆，避免網頁載入太久
            rows = list(reader)
            history = rows[-50:] 
    return jsonify(history)

# 定義 CSV 檔案路徑
CSV_FILE = 'battery_data.csv'

# 初始化 CSV 檔案（如果不存在就建立並寫入標頭）
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'value']) # 寫入標頭
        
# --- CoAP 資源處理 ---
class BatteryResource(resource.Resource):
    async def render_put(self, request):
        payload = request.payload.decode('utf-8').replace('V', '')
        val = float(payload)
        now = datetime.now().strftime('%H:%M:%S')

        # 1. 持久化：存入 CSV 檔案
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([now, val])

        # 2. 即時推播給網頁
        socketio.emit('new_data', {'timestamp': now, 'value': val})
        
        return aiocoap.Message(code=aiocoap.Code.CHANGED, payload=b"OK")
        # except Exception as e:
        #     return aiocoap.Message(code=aiocoap.Code.BAD_REQUEST, payload=str(e).encode())

# --- 啟動 CoAP 伺服器的非同步函式 ---
async def start_coap():
    root = resource.Site()
    root.add_resource(['battery'], BatteryResource())
    await aiocoap.Context.create_server_context(root, bind=('0.0.0.0', 5683))
    print("CoAP Server 運行中...")
    await asyncio.get_running_loop().create_future()

def run_coap_loop():
    asyncio.run(start_coap())

if __name__ == '__main__':
    # 在背景執行 CoAP 伺服器
    coap_thread = threading.Thread(target=run_coap_loop, daemon=True)
    coap_thread.start()

    # 啟動 Flask 網頁伺服器 (預設 Port 5000)
    print("網頁伺服器請訪問 http://<你的Pi_IP>:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
