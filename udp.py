import socket

# 設定監聽的 IP 與 Port (0.0.0.0 表示監聽所有介面)
UDP_IP = "0.0.0.0"
UDP_PORT = 5005

# 建立 Socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"正在監聽 Port {UDP_PORT}...")

while True:
    data, addr = sock.recvfrom(1024) # 緩衝區大小為 1024 位元組
    print(f"來自 {addr} 的訊息: {data.decode('utf-8')}")
