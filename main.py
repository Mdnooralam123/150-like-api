from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
import requests
import json
import like_pb2
import uid_generator_pb2
import visit_count_pb2
from google.protobuf.message import DecodeError
from datetime import datetime, timedelta
import pytz
import urllib3
import asyncio
import aiohttp
from typing import Optional

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="DEVILS WILL RISE API", version="2.0")

# ✅ Config
VALID_API_KEYS = {"KHAN"}
ADMIN_KEY = "KG_ADMIN_2026"
OWNER_NAME = "@Kgbrotherm"

# 🔢 State (in-memory for Vercel)
daily_limit = 30
used_count = 0
KEY_TOTAL_REQUESTS = 10
KEY_REMAINING_REQUESTS = 10
KEY_EXPIRY_DAYS = 365
BATCH_SIZE = 100
RESET_HOUR = 4
RESET_MINUTE = 0

# 🔥 Helper Functions
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
        print(f"Error loading tokens: {e}")
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
        print(f"Encryption error: {e}")
        return None

def create_protobuf_message(user_id, region):
    try:
        message = like_pb2.like()
        message.uid = int(user_id)
        message.region = region
        return message.SerializeToString()
    except Exception as e:
        print(f"Protobuf error: {e}")
        return None

async def send_request_async(encrypted_uid, token, url, session):
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
        async with session.post(url, data=edata, headers=headers, ssl=False) as response:
            return response.status
    except Exception as e:
        print(f"Request error: {e}")
        return None

async def send_multiple_requests_async(uid, region, url):
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
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(BATCH_SIZE):
                token = tokens[i % len(tokens)]["token"]
                tasks.append(send_request_async(encrypted_uid, token, url, session))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for r in results:
                if isinstance(r, int) and r == 200:
                    successful += 1
                elif r is not None:
                    failed += 1
        
        return successful, failed
    except Exception as e:
        print(f"Batch error: {e}")
        return 0, 0

def create_protobuf(uid):
    try:
        message = uid_generator_pb2.uid_generator()
        message.krishna_ = int(uid)
        message.teamXdarks = 1
        return message.SerializeToString()
    except Exception as e:
        print(f"UID protobuf error: {e}")
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
        print(f"Decode error: {e}")
        return None
    except Exception as e:
        print(f"Request error: {e}")
        return None

# 🔥 API Endpoints
@app.get("/")
async def home():
    return {
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
    }

@app.get("/like")
async def like(
    key: str = Query(..., description="API Key"),
    uid: str = Query(..., description="Free Fire UID"),
    region: str = Query(..., description="Region: IND, BR, US, SAC, NA, BD")
):
    global used_count, KEY_REMAINING_REQUESTS, KEY_TOTAL_REQUESTS

    # Reset check
    if should_reset_daily():
        used_count = 0
        KEY_REMAINING_REQUESTS = KEY_TOTAL_REQUESTS

    # API Key check
    if key not in VALID_API_KEYS:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid or missing API key", "status": 3, "owner": OWNER_NAME}
        )

    if KEY_REMAINING_REQUESTS <= 0:
        return JSONResponse(
            status_code=403,
            content={
                "error": "Key remaining requests exhausted! Reset at 4 AM IST",
                "KeyRemainingRequests": f"0/{KEY_TOTAL_REQUESTS}",
                "KeyExpiresAt": get_auto_expiry_date(KEY_EXPIRY_DAYS),
                "status": 3,
                "owner": OWNER_NAME
            }
        )

    # Load tokens
    tokens = load_tokens(region.upper())
    if not tokens:
        raise HTTPException(status_code=500, detail="Failed to load tokens.")
    
    token = tokens[0]['token']
    encrypted_uid = enc(uid)
    if encrypted_uid is None:
        raise HTTPException(status_code=500, detail="Encryption of UID failed.")
    
    # Before profile check
    before = make_request(encrypted_uid, region.upper(), token)
    if before is None:
        raise HTTPException(status_code=500, detail="Failed to get initial info.")
    
    before_like = before.AccountInfo.Likes

    # Determine URL
    if region.upper() == "IND":
        url = "https://client.ind.freefiremobile.com/LikeProfile"
    elif region.upper() in {"BR", "US", "SAC", "NA"}:
        url = "https://client.us.freefiremobile.com/LikeProfile"
    else:
        url = "https://clientbp.ggpolarbear.com/LikeProfile"

    # Send likes
    successful, failed = await send_multiple_requests_async(uid, region.upper(), url)

    # After profile check
    after = make_request(encrypted_uid, region.upper(), token)
    if after is None:
        raise HTTPException(status_code=500, detail="Failed to get final info.")
    
    after_like = after.AccountInfo.Likes
    like_given = after_like - before_like
    status = 1 if like_given > 0 else 2

    if status == 1:
        used_count += 1
        KEY_REMAINING_REQUESTS -= 1

    remaining = max(daily_limit - used_count, 0)
    auto_expiry = get_auto_expiry_date(KEY_EXPIRY_DAYS)

    return {
        "BatchSuccessCount": successful,
        "BatchFailedCount": failed,
        "BatchTotalAttempted": BATCH_SIZE,
        "LikesGivenByAPI": like_given,
        "LikesafterCommand": after_like,
        "LikesbeforeCommand": before_like,
        "PlayerNickname": after.AccountInfo.PlayerNickname,
        "Level": after.AccountInfo.Levels,
        "Region": after.AccountInfo.PlayerRegion,
        "UID": after.AccountInfo.UID,
        "status": status,
        "daily_limit": daily_limit,
        "used": used_count,
        "remaining": remaining,
        "KeyExpiresAt": auto_expiry,
        "KeyRemainingRequests": f"{KEY_REMAINING_REQUESTS}/{KEY_TOTAL_REQUESTS}",
        "reset_info": "4:00 AM IST (Auto reset)",
        "owner": OWNER_NAME
    }

@app.get("/remain")
async def remain_info():
    global used_count, KEY_REMAINING_REQUESTS, KEY_TOTAL_REQUESTS
    
    if should_reset_daily():
        used_count = 0
        KEY_REMAINING_REQUESTS = KEY_TOTAL_REQUESTS
    
    remaining = max(daily_limit - used_count, 0)
    auto_expiry = get_auto_expiry_date(KEY_EXPIRY_DAYS)
    
    return {
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

@app.get("/reset")
async def reset_all(admin_key: str = Query(...)):
    global used_count, KEY_REMAINING_REQUESTS, KEY_TOTAL_REQUESTS
    
    if admin_key != ADMIN_KEY:
        return JSONResponse(status_code=401, content={"error": "Invalid admin key", "owner": OWNER_NAME})
    
    used_count = 0
    KEY_REMAINING_REQUESTS = KEY_TOTAL_REQUESTS
    
    return {
        "message": "✅ All counters reset successfully!",
        "used_count": used_count,
        "KeyRemainingRequests": f"{KEY_REMAINING_REQUESTS}/{KEY_TOTAL_REQUESTS}",
        "reset_time": get_ist_time().strftime("%Y-%m-%d %H:%M:%S IST"),
        "owner": OWNER_NAME
    }

@app.get("/token_info")
async def token_info():
    servers = ["IND", "BD", "BR", "US", "SAC", "NA"]
    info = {"owner": OWNER_NAME}
    
    for server in servers:
        regular_tokens = load_tokens(server)
        info[server] = {
            "regular_tokens": len(regular_tokens) if regular_tokens else 0,
            "visit_tokens": "Not used anymore (same as regular tokens)"
        }
    
    return info

@app.get("/token_status")
async def token_status(region: str = Query(...)):
    tokens = load_tokens(region.upper())
    if tokens is None:
        return JSONResponse(status_code=404, content={"region": region, "total_tokens": 0, "status": "error", "owner": OWNER_NAME})
    
    return {
        "region": region.upper(),
        "total_tokens": len(tokens),
        "active_tokens": len(tokens),
        "status": "healthy",
        "owner": OWNER_NAME
    }

@app.get("/set_key")
async def set_key(
    admin_key: str = Query(...),
    expiry_days: Optional[int] = None,
    total_requests: Optional[int] = None,
    remaining: Optional[int] = None,
    batch_size: Optional[int] = None,
    new_admin_key: Optional[str] = None,
    new_owner: Optional[str] = None,
    new_daily_limit: Optional[int] = None,
    reset_used: bool = False
):
    global KEY_EXPIRY_DAYS, KEY_TOTAL_REQUESTS, KEY_REMAINING_REQUESTS, used_count, BATCH_SIZE, ADMIN_KEY, OWNER_NAME, daily_limit
    
    if admin_key != ADMIN_KEY:
        return JSONResponse(status_code=401, content={"error": "Invalid admin key", "owner": OWNER_NAME})
    
    if expiry_days:
        KEY_EXPIRY_DAYS = expiry_days
    if total_requests:
        KEY_TOTAL_REQUESTS = total_requests
        KEY_REMAINING_REQUESTS = total_requests
    if remaining:
        KEY_REMAINING_REQUESTS = remaining
    if batch_size:
        BATCH_SIZE = batch_size
    if new_admin_key:
        ADMIN_KEY = new_admin_key
    if new_owner:
        OWNER_NAME = new_owner
    if new_daily_limit:
        daily_limit = new_daily_limit
    if reset_used:
        used_count = 0
    
    return {
        "message": "✅ All settings updated successfully!",
        "owner": OWNER_NAME,
        "admin_key": ADMIN_KEY,
        "KeyExpiresAt": get_auto_expiry_date(KEY_EXPIRY_DAYS),
        "KeyExpiryDays": KEY_EXPIRY_DAYS,
        "KeyRemainingRequests": f"{KEY_REMAINING_REQUESTS}/{KEY_TOTAL_REQUESTS}",
        "BatchSize": BATCH_SIZE,
        "daily_limit": daily_limit,
        "used_count": used_count
    }

# For Vercel
handler = app