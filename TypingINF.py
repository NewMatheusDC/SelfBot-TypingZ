import websocket
import json
import time
import threading
import random
from urllib.request import Request, urlopen
# Your Token Here...
token = "YOUR_TOKEN"
user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
# Note: It can be single channel or multiple channels :D 
channel_ids = [
    "CHANNEL-ID",
    "CHANNEL-ID-2",
    "CHANNEL-ID-3",
    "CHANNEL-ID-4",
    "CHANNEL-ID-5",
    "CHANNEL-ID-6", 
]
# User Agent
headers = {
    "Authorization": token,
    "User-Agent": user_agent,
    "Content-Type": "application/json"
}

channel_names = {}
# Cooldown configuration :P
class CoolDownHandler:
    def __init__(self):
        self.last_call = 0
        self.min_wait = 1
        self.max_wait = 3
        self.failed_count = 0
        self.backoff_base = 0
        
    def need_wait(self):
        now = time.time()
        since_last = now - self.last_call
        
        base_wait = random.uniform(self.min_wait, self.max_wait)
        
        if self.failed_count > 0:
            backoff_wait = base_wait * (self.backoff_base ** self.failed_count)
            final_wait = min(backoff_wait, 60)
        else:
            final_wait = base_wait
            
        return since_last < final_wait, final_wait - since_last
        
    def mark_success(self):
        self.failed_count = max(0, self.failed_count - 1)
        self.last_call = time.time()
        
    def mark_failure(self):
        self.failed_count += 1
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
    except:
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
    except Exception as e:
        print(f"Failed to type in channel {channel_id}: {e}")
        cool_down.mark_failure()
        return False
    
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
    print("Connection closed, reconnecting in 5 seconds...")
    time.sleep(5)
    connect_to_gateway()

def handle_open(ws):
    print("Connected and running")

def continuous_typing():
    failed_in_row = 0
    max_failed = 3
    
    while True:
        successful = 0
        
        for channel_id in channel_ids:
            if start_typing(channel_id):
                successful += 1
                failed_in_row = 0
            else:
                failed_in_row += 1
                
            if failed_in_row >= max_failed:
                print("Multiple failures detected, waiting 30 seconds...")
                time.sleep(30)
                failed_in_row = 0
                
            time.sleep(random.uniform(1, 3))
        
        if successful == 0 and len(channel_ids) > 0:
            print("All attempts failed, extended pause activated")
            time.sleep(60)
        elif successful > 0:
            next_wait = random.uniform(20, 40)
            time.sleep(next_wait)

def connect_to_gateway():
    while True:
        try:
            print("Establishing connection...")
            websocket.enableTrace(False)
            ws = websocket.WebSocketApp("wss://gateway.discord.gg/?v=10&encoding=json",
                                      on_message=handle_message,
                                      on_error=handle_error,
                                      on_close=handle_close,
                                      header={"User-Agent": user_agent})
            ws.on_open = handle_open
            ws.run_forever()
        except Exception as e:
            print(f"Connection error: {e}. Retrying in 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    print(f"Tracking {len(channel_ids)} channels")

    connect_to_gateway()
