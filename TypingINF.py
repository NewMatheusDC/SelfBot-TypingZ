import websocket
import json
import time
import threading 
import random
from urllib.request import Request, urlopen
# Your Token
token = "YOUR_TOKEN"
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
# Single Channel or Multipe ^^
channel_ids = [
    "CHANNEL-ID", 
]

headers = {
    "Authorization": token,
    "User-Agent": user_agent,
    "Content-Type": "application/json"
}

channel_names = {}

class CoolDownHandler:
    def __init__(self):
        self.last_call = 0
        self.min_wait = 0.7
        self.max_wait = 1
        
    def need_wait(self):
        now = time.time()
        since_last = now - self.last_call
        final_wait = random.uniform(self.min_wait, self.max_wait)
        return since_last < final_wait, final_wait - since_last
        
    def mark_success(self):
        self.last_call = time.time()

cool_down = CoolDownHandler()

def get_channel_name(channel_id):
    if channel_id in channel_names:
        return channel_names[channel_id]
    
    url = f"https://discord.com/api/v10/channels/{channel_id}"
    req = Request(url, headers=headers, method="GET")
    
    try:
        response = urlopen(req)
        data = json.loads(response.read())
        name = data.get('name', 'unknown')
        channel_names[channel_id] = name
        return name
    except Exception as e:
        return "unknown"

def start_typing(channel_id):
    need_wait, wait_time = cool_down.need_wait()
    
    if need_wait:
        time.sleep(wait_time)
    
    url = f"https://discord.com/api/v10/channels/{channel_id}/typing"
    req = Request(url, headers=headers, method="POST")
    
    try:
        response = urlopen(req)
        if response.getcode() == 204:
            channel_name = get_channel_name(channel_id)
            print(f"Typing in #{channel_name} (ID:{channel_id})")
            cool_down.mark_success()
            return True
        else:
            print(f"HTTP {response.getcode()} for channel {channel_id}")
    except Exception as e:
        if hasattr(e, 'code'):
            if e.code == 429:
                time.sleep(2)
            else:
                print(f"HTTP {e.code} for channel {channel_id}")
        else:
            print(f"Failed to type in channel {channel_id}: {e}")
    
    return False

def keep_alive(ws, interval):
    while True:
        time.sleep(interval / 1000)
        try:
            ws.send(json.dumps({"op": 1, "d": None}))
        except:
            break

def handle_message(ws, message):
    data = json.loads(message)
    
    if data["op"] == 10:
        interval = data["d"]["heartbeat_interval"]
        alive_thread = threading.Thread(target=keep_alive, args=(ws, interval))
        alive_thread.daemon = True
        alive_thread.start()
        
        auth_data = {
            "op": 2,
            "d": {
                "token": token,
                "properties": {
                    "$os": "linux",
                    "$browser": "chrome",
                    "$device": "desktop"
                },
                "intents": 0
            }
        }
        ws.send(json.dumps(auth_data))
        
        typing_loop_thread = threading.Thread(target=continuous_typing)
        typing_loop_thread.daemon = True
        typing_loop_thread.start()

def handle_error(ws, error):
    print(f"Connection issue: {error}")

def handle_close(ws, close_status_code, close_msg):
    print("Connection closed, reconnecting in 3 seconds...")
    time.sleep(3)
    connect_to_gateway()

def handle_open(ws):
    print("Connected and running")

def continuous_typing():
    while True:
        for channel_id in channel_ids:
            start_typing(channel_id)
            time.sleep(0.5)

def connect_to_gateway():
    while True:
        try:
            print("Establishing connection...")
            websocket.enableTrace(False)
            ws = websocket.WebSocketApp("wss://gateway.discord.gg/?v=10&encoding=json",
                                      on_message=handle_message,
                                      on_error=handle_error,
                                      on_close=handle_close,
                                      header=["User-Agent: " + user_agent])
            ws.on_open = handle_open
            ws.run_forever()
        except Exception as e:
            print(f"Connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    print(f"Tracking {len(channel_ids)} channels")
    connect_to_gateway()
