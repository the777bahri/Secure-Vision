import socket, time

TELLO_CMD_PORT = 8889
LOCAL_PORT     = 9000  # your receive socket

# 1) bind your socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', LOCAL_PORT))

def send(cmd, addr):
    sock.sendto(cmd.encode(), addr)
    print(">>", cmd)
    time.sleep(0.5)

def recv():
    data, _ = sock.recvfrom(1024)
    print("<<", data.decode())

# 2) enter SDK mode (still on default TELLO-xxxx AP)
send('command', ('192.168.10.1', TELLO_CMD_PORT))
recv()

# 3) tell the drone to join your Wi-Fi
MY_SSID = "YourHomeSSID"
MY_PWD  = "YourHomePassword"
send(f'ap {MY_SSID} {MY_PWD}', ('192.168.10.1', TELLO_CMD_PORT))
recv()

print("…waiting 10s for the drone to join your network…")
time.sleep(10)

# 4) now discover the drone’s new IP (via your router’s DHCP table, or simply scan for UDP port 8889)
#    let’s assume it came up as 192.168.1.42
DRONE_IP = '192.168.1.42'

# 5) send flight commands
send('takeoff', (DRONE_IP, TELLO_CMD_PORT))
recv()
time.sleep(5)
send('land', (DRONE_IP, TELLO_CMD_PORT))
recv()
