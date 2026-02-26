import asyncio
import threading
import time
import csv
import os
import pytz
import cantools
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import aiocoap.resource as resource
import aiocoap

# --- 基礎設定 ---
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
tw_tz = pytz.timezone('Asia/Taipei')
CSV_FILE = 'battery_data.csv'

# 載入 DBC 檔案 (必須確保 battery_system.dbc 存在於同目錄)
try:
    db = cantools.database.load_file('battery_system.dbc')
    print("成功載入 DBC 檔案！")
except Exception as e:
    print(f"無法載入 DBC 檔案，請檢查路徑與格式: {e}")
    exit(1)

# --- 全域狀態管理 ---
devices = {} # { "IP": {"status": "pending/online/verifying/stopped/error", "last_seen": timestamp} }
system_pause = False 

# 初始化 CSV (支援 DBC 的所有訊號)
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'ip', 'Volt_mV', 'Curr_mA', 'Status', 'Temp_C', 'UnixTime'])

# --- CoAP 資源：生存訊號廣播 (Heartbeat) ---
class HeartbeatResource(resource.ObservableResource):
    def __init__(self):
        super().__init__()
        self.payload = b"ALIVE"
        self.notify_loop()

    def notify_loop(self):
        self.updated_state()
        threading.Timer(30, self.notify_loop).start()

    async def render_get(self, request):
        return aiocoap.Message(payload=self.payload)

# --- CoAP 資源：連線授權 (Connect) ---
class ConnectResource(resource.Resource):
    async def render_put(self, request):
        client_ip = request.remote.hostinfo
        
        if client_ip not in devices or devices[client_ip]["status"] in ["stopped", "error"]:
            devices[client_ip] = {"status": "pending", "last_seen": time.time()}
            print(f"[請求] 設備 {client_ip} 申請連線，等待核准...")
            socketio.emit('auth_request', {'ip': client_ip})
        
        current_status = devices[client_ip]["status"].encode()
        return aiocoap.Message(code=aiocoap.Code.CONTENT, payload=current_status)

# --- CoAP 資源：正常斷線 (Disconnect) ---
class DisconnectResource(resource.Resource):
    async def render_put(self, request):
        client_ip = request.remote.hostinfo
        if client_ip in devices:
            devices[client_ip]["status"] = "stopped"
            print(f"[停止] 設備 {client_ip} 已正常斷開")
            socketio.emit('device_list_update', devices)
        return aiocoap.Message(code=aiocoap.Code.DELETED, payload=b"BYE")

# --- CoAP 資源：DBC 數據接收與解碼 (Battery) ---
class BatteryResource(resource.Resource):
    async def render_put(self, request):
        global system_pause
        client_ip = request.remote.hostinfo

        if system_pause:
            return aiocoap.Message(code=aiocoap.Code.SERVICE_UNAVAILABLE, payload=b"PAUSED")

        if client_ip not in devices or devices[client_ip]["status"] != "online":
            return aiocoap.Message(code=aiocoap.Code.UNAUTHORIZED, payload=b"DENIED")

        try:
            raw_data = request.payload 
            
            # 使用 cantools 根據 DBC 的 Message ID 100 進行解碼
            decoded = db.decode_message(100, raw_data)
            
            # 更新狀態
            devices[client_ip]["last_seen"] = time.time()
            now = datetime.now(tw_tz).strftime('%H:%M:%S')
            
            # 存入 CSV
            with open(CSV_FILE, 'a', newline='') as f:
                csv.writer(f).writerow([
                    now, client_ip, 
                    decoded['Voltage_01'], decoded['Current_01'], 
                    decoded['Status'], decoded['Temp'], decoded['Timestamp']
                ])

            # 推播完整數據給網頁
            socketio.emit('new_data', {
                'timestamp': now,
                'ip': client_ip,
                'data': decoded
            })

            return aiocoap.Message(code=aiocoap.Code.CHANGED, payload=b"ACK")
            
        except Exception as e:
            print(f"[錯誤] DBC 解碼失敗: {e}")
            return aiocoap.Message(code=aiocoap.Code.BAD_REQUEST, payload=b"DECODE_ERROR")

# --- Flask 路由：互動授權 ---
@app.route('/approve_connection')
def approve_connection():
    ip = request.args.get('ip')
    choice = request.args.get('choice') 
    if ip in devices:
        if choice == 'yes':
            devices[ip]["status"] = "online"
        else:
            del devices[ip]
        socketio.emit('device_list_update', devices)
    return "OK"

@app.route('/confirm_disconnect')
def confirm_disconnect():
    ip = request.args.get('ip')
    is_normal = request.args.get('normal') 
    global system_pause
    if ip in devices:
        if is_normal == 'yes':
            devices[ip]["status"] = "stopped"
        else:
            devices[ip]["status"] = "error"
            system_pause = True
            socketio.emit('system_alert', {"msg": f"設備 {ip} 異常斷線，系統停止"})
        socketio.emit('device_list_update', devices)
    return "OK"

@app.route('/reset')
def reset_system():
    global system_pause, devices
    system_pause = False
    devices.clear()
    return "系統重置成功"

@app.route('/get_history')
def get_history():
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r') as f:
            rows = list(csv.DictReader(f))
            return jsonify(rows[-50:])
    return jsonify([])

@app.route('/')
def index():
    return render_template('index.html')

# --- 背景監控 (Watchdog) ---
def watchdog():
    while True:
        now = time.time()
        for ip, info in list(devices.items()):
            if info["status"] == "online" and (now - info["last_seen"] > 15):
                info["status"] = "verifying"
                socketio.emit('check_disconnect', {'ip': ip})
        time.sleep(5)

# --- 啟動程序 ---
async def start_coap():
    root = resource.Site()
    root.add_resource(['heartbeat'], HeartbeatResource())
    root.add_resource(['connect'], ConnectResource())
    root.add_resource(['disconnect'], DisconnectResource())
    root.add_resource(['battery'], BatteryResource())
    
    await aiocoap.Context.create_server_context(root, bind=('0.0.0.0', 5683))
    print("CoAP Server 運行中 (Port 5683)...")
    await asyncio.get_running_loop().create_future()

if __name__ == '__main__':
    threading.Thread(target=watchdog, daemon=True).start()
    threading.Thread(target=lambda: asyncio.run(start_coap()), daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000)