import asyncio
import socket
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

#  基礎設定 
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
tw_tz = pytz.timezone('Asia/Taipei')
CSV_FILE = 'battery_data.csv'

# 載入 DBC 檔案
try:
    db = cantools.database.load_file('battery_system.dbc')
    print("成功載入 DBC 檔案！")
except Exception as e:
    print(f"無法載入 DBC 檔案，請檢查路徑與格式: {e}")
    exit(1)

#  全域狀態管理 
devices = {} # { "IP": {"status": "pending/online/verifying/stopped/error", "last_seen": timestamp} }
system_pause = False 

# 初始化 CSV (支援 DBC 的所有訊號)
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'ip', 'Volt_mV', 'Curr_mA', 'Status', 'Temp_C', 'UnixTime'])

#  CoAP 資源：生存訊號廣播 (Heartbeat) 
class HeartbeatResource(resource.ObservableResource):
    def __init__(self):
        super().__init__()
        self.payload = b"ALIVE"
        self.notify_loop()

    def notify_loop(self):
        self.updated_state()
        threading.Timer(10, self.notify_loop).start()

    async def render_get(self, request):
        return aiocoap.Message(payload=self.payload)

#  CoAP 資源：連線授權 (Connect) 
class ConnectResource(resource.Resource):
    async def render_put(self, request):
        client_ip = request.remote.hostinfo
        
        if client_ip not in devices or devices[client_ip]["status"] in ["stopped", "error"]:
            devices[client_ip] = {"status": "pending", "last_seen": time.time()}
            print(f"[請求] 設備 {client_ip} 申請連線，等待核准...")
            socketio.emit('auth_request', {'ip': client_ip})
        
        current_status = devices[client_ip]["status"].encode()
        return aiocoap.Message(code=aiocoap.Code.CONTENT, payload=current_status)

#  CoAP 資源：正常斷線 (Disconnect) 
class DisconnectResource(resource.Resource):
    async def render_put(self, request):
        client_ip = request.remote.hostinfo
        if client_ip in devices:
            devices[client_ip]["status"] = "stopped"
            print(f"[停止] 設備 {client_ip} 已正常斷開")
            socketio.emit('device_list_update', devices)
        return aiocoap.Message(code=aiocoap.Code.DELETED, payload=b"BYE")

#  CoAP 資源：DBC 數據接收與解碼 (Battery) 
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

class ThinkPowerCharger:
    def __init__(self, ip, port=5025):
        self.ip = ip
        self.port = port

    def query(self, cmd):
        response = None
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect((self.ip, self.port))
                full_cmd = cmd + "\n"
                s.sendall(full_cmd.encode('ascii'))
                time.sleep(0.2) 
                response = s.recv(1024).decode('ascii').strip()
        except Exception as e:
            print(f"[充放電機] 指令 [{cmd}] 執行失敗: {e}")
            response = "ERROR"
        return response

# 初始化充放電機 (請確認 IP 正確)
charger = ThinkPowerCharger(ip="172.22.13.214", port=5025)

#  Flask 路由：互動授權 
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

@socketio.on('connect')
def handle_web_connect():
    # 針對剛連進來的網頁，立刻發送目前的設備清單與狀態
    socketio.emit('device_list_update', devices, to=request.sid)
    print(f"[網頁端] 已連線，已同步目前設備清單。")

@app.route('/toggle_charge')
def toggle_charge():
    ip = request.args.get('ip')
    state = request.args.get('state') # 會收到字串 "1" 或 "0"
    
    if ip in devices and devices[ip]["status"] == "online":
        print(f"[控制] 準備發送狀態 {state} 至設備 {ip}")
        
        # 建立一個背景執行緒來發送 CoAP 請求 (避免阻塞 Flask)
        def send_coap_request():
            async def _send():
                try:
                    context = await aiocoap.Context.create_client_context()
                    payload = state.encode('utf-8')
                    # 傳送到 ESP32 的 /led 資源
                    msg = aiocoap.Message(code=aiocoap.Code.PUT, uri=f"coap://{ip}:5683/led", payload=payload)
                    await context.request(msg).response
                    print(f"[控制] 成功發送至 {ip}")
                except Exception as e:
                    print(f"[錯誤] 發送 CoAP 指令給 {ip} 失敗: {e}")
            
            # 使用獨立的 Event Loop 執行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_send())
            loop.close()
            
        threading.Thread(target=send_coap_request).start()
        return jsonify({"status": "success"}), 200
        
    return jsonify({"status": "error", "msg": "設備未連線或不存在"}), 404

# 安全斷開/重新連線
@app.route('/set_device_state')
def set_device_state():
    ip = request.args.get('ip')
    state = request.args.get('state') # 接收 "stop" 或 "start"
    
    if ip in devices:
        print(f"[系統] 準備將設備 {ip} 狀態設為: {state}")
        
        # 建立背景執行緒發送 CoAP 控制指令
        def send_control_cmd():
            async def _send():
                try:
                    context = await aiocoap.Context.create_client_context()
                    payload = state.encode('utf-8')
                    # 傳送到 ESP32 control resource
                    msg = aiocoap.Message(code=aiocoap.Code.PUT, uri=f"coap://{ip}:5683/control", payload=payload)
                    await context.request(msg).response
                    print(f"[系統] {ip} 控制指令發送成功")
                except Exception as e:
                    print(f"[錯誤] 發送控制指令給 {ip} 失敗: {e}")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_send())
            loop.close()
            
        threading.Thread(target=send_control_cmd).start()
        
        # 更新網頁端的設備狀態
        if state == "stop":
            devices[ip]["status"] = "stopped"
        else:
            # 喚醒後直接設為 online，或設為 pending 讓使用者重新授權 (這裡選擇直接 online)
            devices[ip]["status"] = "online" 
            devices[ip]["last_seen"] = time.time() # 刷新最後存活時間避免立刻觸發超時
            
        socketio.emit('device_list_update', devices)
        return jsonify({"status": "success"}), 200
        
    return jsonify({"status": "error", "msg": "設備不存在"}), 404

@app.route('/charger')
def charger_page():
    """負責載入充放電機的專屬控制面板網頁"""
    return render_template('charger.html')

mah_tracker = {
    "last_hardware_mah": 0.0,
    "total_charge_mah": 0.0,
    "total_discharge_mah": 0.0
}

@app.route('/api/charger/data')
def get_charger_data():
    """提供前端 Ajax 抓取即時數據的 API"""
    global mah_tracker
    response_str = charger.query("MEASure:ALL?")
    data_parts = [p.strip() for p in response_str.split(',')]
    
    # 防錯機制 2：確保陣列長度足夠，避免 IndexError 導致系統崩潰
    if len(data_parts) >= 14:
            raw_mode = data_parts[11].strip().upper()
            
            # --- MAH 分流計算邏輯 ---
            try:
                current_hardware_mah = float(data_parts[6])
            except ValueError:
                current_hardware_mah = 0.0 # 防呆：萬一機台傳回來的不是數字
                
            delta_mah = current_hardware_mah - mah_tracker["last_hardware_mah"]
            
            # 如果機台數值歸零 (換腳本時)，差額就是當下的數值
            if delta_mah < 0:
                delta_mah = current_hardware_mah
                
            # 將差額存入對應的帳戶
            if raw_mode in ["CCC", "CVC", "CPC"]:
                mah_tracker["total_charge_mah"] += delta_mah
            elif raw_mode in ["CCD", "CVD", "CPD"]:
                mah_tracker["total_discharge_mah"] += delta_mah
                
            mah_tracker["last_hardware_mah"] = current_hardware_mah
            
            # --- 狀態文字翻譯邏輯 ---
            action_text = raw_mode
            if raw_mode in ["CCC", "CVC", "CPC"]:
                action_text = f"充電 ({raw_mode})"
            elif raw_mode in ["CCD", "CVD", "CPD"]:
                action_text = f"放電 ({raw_mode})"
            elif raw_mode == "REST":
                action_text = "休息 (REST)"
            else:
                action_text = raw_mode

            # 成功解析，回傳完整數據 (請確認這裡的 return 是在 if 區塊內)
            return jsonify({
                "status": "online",
                "volt": f"{float(data_parts[2]):.3f}",      
                "curr": f"{float(data_parts[3]):.3f}",      
                "power": f"{float(data_parts[4]):.3f}", 
                "charge_mah": round(mah_tracker["total_charge_mah"], 3),
                "discharge_mah": round(mah_tracker["total_discharge_mah"], 3),
                "step": data_parts[8],      
                "mode": action_text       
            }), 200
    else:
        # 如果長度不到 14，代表資料格式不對或儀器還在開機
        return jsonify({
            "status": "offline", 
            "volt": "--", 
            "curr": "--",
            "power": "--",
            "mah": "--",
            "step": "--",
            "mode": "--"
        }), 503




@app.route('/api/charger/cmd')
def send_charger_cmd():
    """提供前端發送任意控制指令的 API"""
    cmd = request.args.get('cmd')
    if not cmd:
        return jsonify({"error": "No command provided"}), 400 
    res = charger.query(cmd)
    return jsonify({"response": res})


# ESP32生存監控
def watchdog():
    while True:
        now = time.time()
        for ip, info in list(devices.items()):
            if info["status"] == "online" and (now - info["last_seen"] > 15):
                info["status"] = "verifying"
                socketio.emit('check_disconnect', {'ip': ip})
        time.sleep(5)

#  啟動程序 
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