from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
import requests
import json
import like_pb2
import uid_generator_pb2
import visit_count_pb2
from google.protobuf.message import DecodeError
from collections import OrderedDict
from datetime import datetime, timedelta
import pytz
import urllib3
import threading

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ✅ Valid API keys
VALID_API_KEYS = {
    "KHAN"
}

# 👑 ADMIN CONFIG
ADMIN_KEY = "KG_ADMIN_2026"
OWNER_NAME = "@Kgbrotherm"

# 🔢 Like limit tracking
daily_limit = 30
used_count = 0

# 🔥 KEY SYSTEM
KEY_TOTAL_REQUESTS = 10
KEY_REMAINING_REQUESTS = 10
KEY_EXPIRY_DAYS = 365
RESET_HOUR = 4
RESET_MINUTE = 0

# 📊 Batch tracking
BATCH_SIZE = 100

def get_auto_expiry_date(days=365):
    now = datetime.now(pytz.UTC)
    expiry = now + timedelta(days=days)
    return expiry.strftime("%Y-%m-%dT%H:%M:%SZ")

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

def should_reset_daily():
    now_ist = get_ist_time()
    if now_ist.hour >= RESET_HOUR and now_ist.minute >= RESET_MINUTE:
        return True
    return False

def load_tokens(region):
    try:
        if region == "IND":
            with open("token_ind.json", "r") as f:
                tokens = json.load(f)
        elif region in {"BR", "US", "SAC", "NA"}:
            with open("token_br.json", "r") as f:
                tokens = json.load(f)
        else:
            with open("token_bd.json", "r") as f:
                tokens = json.load(f)
        return tokens
    except Exception as e:
        app.logger.error(f"Error loading tokens for region {region}: {e}")
        return None

def encrypt_message(plaintext):
    try:
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_message = pad(plaintext, AES.block_size)
        encrypted_message = cipher.encrypt(padded_message)
        return binascii.hexlify(encrypted_message).decode('utf-8')
    except Exception as e:
        app.logger.error(f"Error encrypting message: {e}")
        return None

def create_protobuf_message(user_id, region):
    try:
        message = like_pb2.like()
        message.uid = int(user_id)
        message.region = region
        return message.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error creating protobuf message: {e}")
        return None

def send_request_sync(encrypted_uid, token, url):
    try:
        edata = bytes.fromhex(encrypted_uid)
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Expect": "100-continue",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54"
        }
        response = requests.post(url, data=edata, headers=headers, verify=False, timeout=10)
        return response.status_code
    except Exception as e:
        app.logger.error(f"Exception in send_request_sync: {e}")
        return None

def send_multiple_requests_sync(uid, region, url):
    try:
        protobuf_message = create_protobuf_message(uid, region)
        if protobuf_message is None:
            return 0, 0
        encrypted_uid = encrypt_message(protobuf_message)
        if encrypted_uid is None:
            return 0, 0
        tokens = load_tokens(region)
        if tokens is None:
            return 0, 0
        
        successful = 0
        failed = 0
        
        def send_with_thread(token, results, index):
            status = send_request_sync(encrypted_uid, token, url)
            results[index] = status
        
        threads = []
        results = [None] * BATCH_SIZE
        
        for i in range(BATCH_SIZE):
            token = tokens[i % len(tokens)]["token"]
            thread = threading.Thread(target=send_with_thread, args=(token, results, i))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        for r in results:
            if r == 200:
                successful += 1
            elif r is not None:
                failed += 1
        
        return successful, failed
    except Exception as e:
        app.logger.error(f"Exception in send_multiple_requests_sync: {e}")
        return 0, 0

def create_protobuf(uid):
    try:
        message = uid_generator_pb2.uid_generator()
        message.krishna_ = int(uid)
        message.teamXdarks = 1
        return message.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error creating uid protobuf: {e}")
        return None

def enc(uid):
    protobuf_data = create_protobuf(uid)
    if protobuf_data is None:
        return None
    return encrypt_message(protobuf_data)

def make_request(encrypt, region, token):
    try:
        if region == "IND":
            url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        elif region in {"BR", "US", "SAC", "NA"}:
            url = "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
        else:
            url = "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow"
        edata = bytes.fromhex(encrypt)
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Expect": "100-continue",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54"
        }
        response = requests.post(url, data=edata, headers=headers, verify=False, timeout=30)
        binary = response.content
        decoded = visit_count_pb2.Info()
        decoded.ParseFromString(binary)
        return decoded
    except DecodeError as e:
        app.logger.error(f"DecodeError: {e}")
        return None
    except Exception as e:
        app.logger.error(f"Error in make_request: {e}")
        return None

@app.route('/like', methods=['GET'])
def handle_requests():
    global used_count, KEY_REMAINING_REQUESTS, KEY_TOTAL_REQUESTS

    try:
        if should_reset_daily():
            used_count = 0
            KEY_REMAINING_REQUESTS = KEY_TOTAL_REQUESTS

        api_key = request.args.get("key")
        if api_key not in VALID_API_KEYS:
            result = OrderedDict([
                ("error", "Invalid or missing API key"),
                ("status", 3),
                ("owner", OWNER_NAME)
            ])
            return jsonify(result), 401

        uid = request.args.get("uid")
        region = request.args.get("region", "").upper()
        if not uid or not region:
            return jsonify({"error": "UID and region are required", "owner": OWNER_NAME}), 400

        if KEY_REMAINING_REQUESTS <= 0:
            result = OrderedDict([
                ("error", "Key remaining requests exhausted! Reset at 4 AM IST"),
                ("KeyRemainingRequests", f"0/{KEY_TOTAL_REQUESTS}"),
                ("KeyExpiresAt", get_auto_expiry_date(KEY_EXPIRY_DAYS)),
                ("status", 3),
                ("owner", OWNER_NAME)
            ])
            return jsonify(result), 403

        tokens = load_tokens(region)
        if not tokens:
            return jsonify({"error": "Failed to load tokens.", "owner": OWNER_NAME}), 500
        
        token = tokens[0]['token']
        encrypted_uid = enc(uid)
        if encrypted_uid is None:
            return jsonify({"error": "Encryption of UID failed.", "owner": OWNER_NAME}), 500
        
        before = make_request(encrypted_uid, region, token)
        if before is None:
            return jsonify({"error": "Failed to get initial info.", "owner": OWNER_NAME}), 500
        
        before_like = before.AccountInfo.Likes

        if region == "IND":
            url = "https://client.ind.freefiremobile.com/LikeProfile"
        elif region in {"BR", "US", "SAC", "NA"}:
            url = "https://client.us.freefiremobile.com/LikeProfile"
        else:
            url = "https://clientbp.ggpolarbear.com/LikeProfile"

        successful, failed = send_multiple_requests_sync(uid, region, url)

        after = make_request(encrypted_uid, region, token)
        if after is None:
            return jsonify({"error": "Failed to get final info.", "owner": OWNER_NAME}), 500
        
        after_like = after.AccountInfo.Likes
        like_given = after_like - before_like
        status = 1 if like_given > 0 else 2

        if status == 1:
            used_count += 1
            KEY_REMAINING_REQUESTS -= 1

        remaining = max(daily_limit - used_count, 0)
        auto_expiry = get_auto_expiry_date(KEY_EXPIRY_DAYS)

        result = OrderedDict([
            ("BatchSuccessCount", successful),
            ("BatchFailedCount", failed),
            ("BatchTotalAttempted", BATCH_SIZE),
            ("LikesGivenByAPI", like_given),
            ("LikesafterCommand", after_like),
            ("LikesbeforeCommand", before_like),
            ("PlayerNickname", after.AccountInfo.PlayerNickname),
            ("Level", after.AccountInfo.Levels),
            ("Region", after.AccountInfo.PlayerRegion),
            ("UID", after.AccountInfo.UID),
            ("status", status),
            ("daily_limit", daily_limit),
            ("used", used_count),
            ("remaining", remaining),
            ("KeyExpiresAt", auto_expiry),
            ("KeyRemainingRequests", f"{KEY_REMAINING_REQUESTS}/{KEY_TOTAL_REQUESTS}"),
            ("reset_info", "4:00 AM IST (Auto reset)"),
            ("owner", OWNER_NAME)
        ])

        return jsonify(result)

    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({"error": str(e), "owner": OWNER_NAME}), 500

@app.route('/remain', methods=['GET'])
def remain_info():
    global used_count, KEY_REMAINING_REQUESTS, KEY_TOTAL_REQUESTS
    
    try:
        if should_reset_daily():
            used_count = 0
            KEY_REMAINING_REQUESTS = KEY_TOTAL_REQUESTS
        
        remaining = max(daily_limit - used_count, 0)
        auto_expiry = get_auto_expiry_date(KEY_EXPIRY_DAYS)
        
        data = {
            "daily_limit": daily_limit,
            "remaining": remaining,
            "used": used_count,
            "reset_info": "4:00 AM IST (Auto reset)",
            "KeyExpiresAt": auto_expiry,
            "KeyRemainingRequests": f"{KEY_REMAINING_REQUESTS}/{KEY_TOTAL_REQUESTS}",
            "total_requests_allowed": KEY_TOTAL_REQUESTS,
            "batch_size": BATCH_SIZE,
            "owner": OWNER_NAME
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e), "owner": OWNER_NAME}), 500

@app.route('/reset', methods=['GET'])
def reset_all():
    global used_count, KEY_REMAINING_REQUESTS, KEY_TOTAL_REQUESTS
    
    try:
        admin_key = request.args.get("admin_key")
        if admin_key != ADMIN_KEY:
            return jsonify({"error": "Invalid admin key", "owner": OWNER_NAME}), 401
        
        used_count = 0
        KEY_REMAINING_REQUESTS = KEY_TOTAL_REQUESTS
        
        return jsonify({
            "message": "✅ All counters reset successfully!",
            "used_count": used_count,
            "KeyRemainingRequests": f"{KEY_REMAINING_REQUESTS}/{KEY_TOTAL_REQUESTS}",
            "reset_time": get_ist_time().strftime("%Y-%m-%d %H:%M:%S IST"),
            "owner": OWNER_NAME
        })
    except Exception as e:
        return jsonify({"error": str(e), "owner": OWNER_NAME}), 500

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "message": "🔥 DEVILS WILL RISE — Subscriber Edition",
        "owner": OWNER_NAME,
        "version": "2.0",
        "batch_size": BATCH_SIZE,
        "endpoints": {
            "like": "/like?key=KHAN&uid=UID&region=REGION",
            "remain": "/remain",
            "reset": "/reset?admin_key=KG_ADMIN_2026",
            "token_info": "/token_info",
            "token_status": "/token_status?region=IND",
            "set_key": "/set_key?admin_key=KG_ADMIN_2026&parameter=value"
        }
    })

@app.route('/token_info', methods=['GET'])
def token_info():
    try:
        servers = ["IND", "BD", "BR", "US", "SAC", "NA"]
        info = {"owner": OWNER_NAME}
        
        for server in servers:
            regular_tokens = load_tokens(server)
            info[server] = {
                "regular_tokens": len(regular_tokens) if regular_tokens else 0,
                "visit_tokens": "Not used anymore (same as regular tokens)"
            }
        
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e), "owner": OWNER_NAME}), 500

@app.route('/token_status', methods=['GET'])
def token_status():
    try:
        region = request.args.get("region", "").upper()
        if not region:
            return jsonify({"error": "Region parameter required", "owner": OWNER_NAME}), 400
        
        tokens = load_tokens(region)
        if tokens is None:
            return jsonify({"region": region, "total_tokens": 0, "status": "error", "owner": OWNER_NAME}), 404
        
        return jsonify({
            "region": region,
            "total_tokens": len(tokens),
            "active_tokens": len(tokens),
            "status": "healthy",
            "owner": OWNER_NAME
        })
    except Exception as e:
        return jsonify({"error": str(e), "owner": OWNER_NAME}), 500

@app.route('/set_key', methods=['GET'])
def set_key():
    global KEY_EXPIRY_DAYS, KEY_TOTAL_REQUESTS, KEY_REMAINING_REQUESTS, used_count, BATCH_SIZE, ADMIN_KEY, OWNER_NAME, daily_limit
    
    try:
        admin_key = request.args.get("admin_key")
        if admin_key != ADMIN_KEY:
            return jsonify({"error": "Invalid admin key", "owner": OWNER_NAME}), 401
        
        new_expiry_days = request.args.get("expiry_days")
        new_total = request.args.get("total_requests")
        new_remaining = request.args.get("remaining")
        new_batch_size = request.args.get("batch_size")
        new_admin_key = request.args.get("new_admin_key")
        new_owner = request.args.get("new_owner")
        new_daily_limit = request.args.get("daily_limit")
        reset_used = request.args.get("reset_used", "false").lower() == "true"
        
        if new_expiry_days:
            KEY_EXPIRY_DAYS = int(new_expiry_days)
        if new_total:
            KEY_TOTAL_REQUESTS = int(new_total)
            KEY_REMAINING_REQUESTS = int(new_total)
        if new_remaining:
            KEY_REMAINING_REQUESTS = int(new_remaining)
        if new_batch_size:
            BATCH_SIZE = int(new_batch_size)
        if new_admin_key:
            ADMIN_KEY = new_admin_key
        if new_owner:
            OWNER_NAME = new_owner
        if new_daily_limit:
            daily_limit = int(new_daily_limit)
        if reset_used:
            used_count = 0
        
        return jsonify({
            "message": "✅ All settings updated successfully!",
            "owner": OWNER_NAME,
            "admin_key": ADMIN_KEY,
            "KeyExpiresAt": get_auto_expiry_date(KEY_EXPIRY_DAYS),
            "KeyExpiryDays": KEY_EXPIRY_DAYS,
            "KeyRemainingRequests": f"{KEY_REMAINING_REQUESTS}/{KEY_TOTAL_REQUESTS}",
            "BatchSize": BATCH_SIZE,
            "daily_limit": daily_limit,
            "used_count": used_count
        })
    except Exception as e:
        return jsonify({"error": str(e), "owner": OWNER_NAME}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)