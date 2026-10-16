#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Avetaar EFootball Player
========================
دليلك داخل eFootball (PES 2022 API) من:
  1) طرفية في الترمنال (ألوان، أزرار، تنسيق)
  2) بوت تلغرام (رسائل مفلترة، أزرار ملونة)

التثبيت بأمر واحد (Windows/Linux):
  pip install requests colorama

شغل الترمنال:
  python AvetaarEFoot.py

شغل البوت (ضع توكن بوتك في ملف .env بجوار السكربت أو عبر المتغيرات):
  python AvetaarEFoot.py --bot
"""
import argparse
import html
import json
import time
import os
import sys
from urllib.parse import quote_plus

try:
    import requests
except ImportError:
    sys.exit("العباءة مفقودة: pip install requests")

# colorama اختياري (إذا ما توفر، ألوان خام من ANSI في لينكس، وعادي في ويندوز)
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    def C(name: str) -> str:
        return getattr(Fore, name, "")
    def RST() -> str:
        return Style.RESET_ALL
except Exception:
    def C(name: str) -> str:
        return ""
    def RST() -> str:
        return ""

API_BASE = "https://api.efootballdb.com/api/2022/players"
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "origin": "https://www.efootballdb.com",
    "referer": "https://www.efootballdb.com/",
    "accept-language": "ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6,zh;q=0.5,ar-EG;q=0.4",
}

# ---------- معالجة الـ API ----------
def team_name_from(team_field) -> str:
    """يعيد اسم الفريق من حقل (national_team / club_team / current_club_id).
    يتعامل مع البنية المزدوجة: dict مباشر مع 'team' مضمن، أو 'team' في الجذر."""
    if not team_field:
        return "غير متوفر"
    # بنية 1: team_field['team'] مضمن (national_team, club_team)
    team = team_field.get("team")
    if team:
        return (team.get("english_name") or team.get("licensed_abb_name") or "غير متوفر").strip()
    # بنية 2: البيانات مباشرة في team_field (current_club_id — فيه english_name في الجذر)
    return (team_field.get("english_name") or team_field.get("licensed_abb_name") or "غير متوفر").strip()

def fetch_player(handle: str, timeout: int = 20):
    """يعيد dict للاعب أو None إذا ما فيه."""
    handle = (handle or "").strip().lower()
    if not handle:
        return None
    try:
        r = requests.get(f"{API_BASE}/{handle}", headers=API_HEADERS, timeout=timeout)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        d = r.json()
    except ValueError:
        return None
    if not isinstance(d, dict) or not d.get("data"):
        return None
    return d["data"][0]

def player_card(p: dict) -> dict:
    """يبني بطاقة نظيفة من رد الـ API (معالجة كل الحقول الفاصلة)."""
    return {
        "handle":  p.get("base_pes_id") or p.get("pes_id") or "",
        "name":    p.get("player_name", "غير متوفر"),
        "club":    team_name_from(p.get("current_club_id")),
        "nat":     team_name_from(p.get("national_team")),
        "nat_abbr": (p.get("national_team") or {}).get("team", {}).get("licensed_abb_name", ""),
        "age":     p.get("age"),
        "height":  p.get("height"),
        "weight":  p.get("weight"),
        "pos":     p.get("main_position_text") or "غير معروف",
        "style":   p.get("playing_style"),
        "foot":    ["يسرى", "يمنى", "متوازن"][p.get("strong_foot", 1)] if p.get("strong_foot") in (0, 1, 2) else None,
        "star":    p.get("star_player"),
        "value":   p.get("market_value"),
        "stats": {
            "السرعة":             p.get("speed"),
            "المراوغة":          p.get("dribbling"),
            "التحكم بالكرة":      p.get("ball_control"),
            "التمرير القصير":     p.get("low_pass"),
            "التسديد":           p.get("finishing"),
            "القوة البدنية":      p.get("physical_contact"),
            "التمركز الهجومي":   p.get("attacking_prowess"),
            "التحمل":            p.get("stamina"),
            "الرأسيات":           p.get("header"),
            "الضغط الدفاعي":      p.get("defensive_engagement"),
        },
    }

def fmt(value, unit=""):
    if value in (None, "", "غير متوفر"):
        return "غير متوفر"
    return f"{value}{unit}"

# ---------- عرض الطرفية ----------
LINE   = "═" * 54
THIN   = "─" * 54

def bar(title, color="CYAN"):
    label = title.center(54)
    print(f"{C(color)}║{label}║{RST()}")

def terminal_card(card: dict):
    print(f"{C('CYAN')}{LINE}{RST()}")
    print(f"{C('GREEN')}  ★ {card['name']} {RST()}")
    print(f"{C('YELLOW')}  🏟 النادي  : {card['club']}   🏳️ المنتخب : {card['nat']}{RST()}")
    extra = []
    if card["age"]:    extra.append(f"🎂 {card['age']}")
    if card["height"]: extra.append(f"📏 {card['height']} سم")
    if card["weight"]: extra.append(f"⚖️ {card['weight']} كجم")
    if card["foot"]:   extra.append(f"🦶 {card['foot']}")
    if card["star"]:   extra.append(f"⭐ نجم {card['star']}")
    print(f"{C('BLUE')}  {C('LIGHTMAGENTA_EX')}  المركز: {card['pos']}   " + "  ".join(extra) + RST() + "  " + RST())
    print(f"{C('CYAN')}{THIN}{RST()}")
    print(f"{C('GREEN')}  الإحصائيات الرئيسية{RST()}")
    for k, v in card["stats"].items():
        print(f"   {C('LIGHTGREEN_EX')}{k:<14} {RST()}{C('LIGHTWHITE_EX')}{'>' * (int(v) * 30 // 99 if isinstance(v, int) else 0)}{RST()}  {fmt(v)}")
    print(f"{C('CYAN')}{LINE}{RST()}")

def terminal_menu_loop():
    banner = "\n".join([
        f"{C('CYAN')}{LINE}{RST()}",
        f"{C('MAGENTA')}   ⚽  Avetaar EFootball Player  ⚽{RST()}",
        f"{C('CYAN')}{LINE}{RST()}",
    ])
    print(banner)
    while True:
        print(f"\n  {C('GREEN')}[1]{RST()} استعلام لاعب   {C('YELLOW')}[2]{RST()} خروج")
        choice = input("  الاختيار: ").strip()
        if choice in ("q", "2", "0"):
            print(f"\n  {C('CYAN')}إلى اللقاء! ⚽{RST()}\n")
            break
        if choice not in ("", "1"):
            print(f"  {C('RED')}خيار غير صحيح{RST()}")
            continue
        handle = input(f"  {C('YELLOW')}اسم اللاعب (بالإنجليزية، بدون مسافات — مثال mbappe): {RST()}")
        raw = fetch_player(handle)
        if raw:
            terminal_card(player_card(raw))
        else:
            print(f"  {C('RED')}لا يوجد لاعب بهذا الاسم — تأكد من كتابة الاسم بدون مسافات.{RST()}")
    sys.exit(0)

# ---------- البوت ----------
BTN_BLUE    = "#3297FD"
BTN_GREEN   = "#45D0A8"
BTN_RED     = "#E05252"
BTN_YELLOW  = "#F0B429"
BTN_PURPLE  = "#8B5CF6"

def load_bot_token() -> str:
    for p in (".", os.path.dirname(os.path.abspath(__file__))):
        env_file = os.path.join(p, ".env")
        if os.path.exists(env_file):
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("BOT_TOKEN="):
                        return line.split("=", 1)[1].strip().strip('"\'')
    return os.environ.get("BOT_TOKEN", "")

def tg_call(token: str, method: str, params: dict):
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", params=params, timeout=30)
    d = r.json()
    if not d.get("ok"):
        raise RuntimeError(d.get("description", str(r.status_code)))
    return d.get("result")

def esc(s) -> str:
    return html.escape(str(s), quote=False)

def stat_line(v, name, max_val=99):
    if not isinstance(v, int):
        return f"   {name:<10}  {'-' * max_val}"
    filled = min(max(v, 0), max_val)
    bar_s = "█" * filled + "░" * (max_val - filled)
    return f"   {name:<10}  {bar_s}  {v}"

def bot_player_message(card: dict) -> str:
    lines = [f" <b>⚽ {esc(card['name'])}</b>", ""]
    if card["club"] != "غير متوفر" or card["nat"] != "غير متوفر":
        lines.append(f"   🏟️  {esc(card['club'])}   🏳️  {esc(card['nat'])}")
    extras = []
    if card["age"]:    extras.append(f"🎂 {card['age']}")
    if card["height"]: extras.append(f"📏 {card['height']} سم")
    if card["weight"]: extras.append(f"⚖️ {card['weight']} كجم")
    if card["foot"]:   extras.append(f"🦶 {card['foot']}")
    if card["star"]:   extras.append(f"⭐ نجم {card['star']}")
    if extras:
        lines.append("   " + "  ".join(extras))
    lines.append(f"   🧩  المركز: <b>{esc(card['pos'])}</b>")
    lines.append("")
    lines.append(" <b>الإحصائيات الرئيسية</b>")
    for k, v in card["stats"].items():
        lines.append(stat_line(v, k, 25))
    lines.append("")
    lines.append(" <i>تصحيح: بيانات eFootball 2022 API</i>")
    return "\n".join(lines)

def buttons_for_player(card: dict):
    inline = [
        [
            {"text": "⚽ إعادة", "callback_data": "menu", "color": BTN_BLUE},
            {"text": "🔁 آخر استعلام", "callback_data": f"replay:{card['handle']}", "color": BTN_GREEN},
        ]
    ]
    return json.dumps(inline, ensure_ascii=False)

def bot_handle_callback(token, update):
    cb = update["callback_query"]
    chat_id = cb["message"]["chat"]["id"]
    user = cb["from"]
    data = cb["data"]
    tg_call(token, "answerCallbackQuery", {"callback_query_id": cb["id"]})
    if data == "menu":
        tg_call(token, "sendMessage", {"chat_id": chat_id, "text": "اختر:", "reply_markup": buttons_for_menu()})
    elif data.startswith("search:"):
        handle = data[7:]
        raw = fetch_player(handle)
        if raw:
            card = player_card(raw)
            tg_call(token, "sendMessage", {
                "chat_id": chat_id,
                "text": bot_player_message(card),
                "reply_markup": buttons_for_player(card),
            })
        else:
            tg_call(token, "sendMessage", {
                "chat_id": chat_id,
                "text": " ⛔ لا يوجد لاعب بهذا الاسم — تأكد من كتابة الاسم بدون مسافات (مثل mbappe).",
            })
    elif data.startswith("replay:"):
        handle = data[7:]
        raw = fetch_player(handle)
        if raw:
            card = player_card(raw)
            tg_call(token, "editMessageText", {
                "chat_id": chat_id,
                "message_id": cb["message"]["message_id"],
                "text": bot_player_message(card),
                "reply_markup": buttons_for_player(card),
            })
        else:
            tg_call(token, "sendMessage", {"chat_id": chat_id, "text": " ⛔ لا توجد بيانات لهذا اللاعب."})

def buttons_for_menu():
    inline = [
        [
            {"text": "🔍 استعلام لاعب", "callback_data": "search:", "color": BTN_BLUE},
        ],
        [
            {"text": "👟 mbappe", "callback_data": "search:mbappe", "color": BTN_GREEN},
            {"text": "🧊 messi", "callback_data": "search:messi", "color": BTN_GREEN},
            {"text": "⚽ kane", "callback_data": "search:kane", "color": BTN_GREEN},
        ],
        [
            {"text": "🧤 neuer", "callback_data": "search:neuer", "color": BTN_YELLOW},
            {"text": "🏃 saka", "callback_data": "search:saka", "color": BTN_YELLOW},
            {"text": "🏰 aliy", "callback_data": "search:aliy", "color": BTN_YELLOW},
        ],
    ]
    return json.dumps(inline, ensure_ascii=False)

def bot_run_long_poll():
    token = load_bot_token()
    if not token:
        sys.exit("لا يوجد بوت تكين. أنشئ بوتاً مع @BotFather وضع التوكن في ملف .env بجانب السكربت:\n  BOT_TOKEN=123456:ABC...")
    tg_call(token, "setMyCommands", {
        "commands": json.dumps([
            {"command": "start",  "description": "بدء الدليل"},
            {"command": "player", "description": "اسم اللاعب بالإنجليزية"},
            {"command": "help",   "description": "دليل الاستخدام"},
        ], ensure_ascii=False)
    })
    print(f"{C('GREEN')}🚀 البوت شغّال... (Ctrl+C للإيقاف){RST()}")
    last_update_id = 0
    while True:
        try:
            d = tg_call(token, "getUpdates", {"limit": 50, "offset": last_update_id + 1, "timeout": 30})
            for u in d:
                last_update_id = u["update_id"]
                msg = u.get("message")
                if msg:
                    text = (msg.get("text") or "").strip()
                    chat_id = msg["chat"]["id"]
                    tl = text.lower()
                    if tl in ("/start", "start", "ابدأ") or tl == "/help" or tl == "help" or tl == "دليل":
                        tg_call(token, "sendMessage", {
                            "chat_id": chat_id,
                            "text": " 👋 أهلاً! اختر ما تريد من الأزرار، أو اكتب اسم اللاعب بالإنجليزية مباشرةً.",
                            "reply_markup": buttons_for_menu(),
                        })
                    elif tl.startswith("/player"):
                        handle = text.split(None, 1)[-1].strip() if " " in text else ""
                        raw = fetch_player(handle)
                        if raw:
                            card = player_card(raw)
                            tg_call(token, "sendMessage", {
                                "chat_id": chat_id,
                                "text": bot_player_message(card),
                                "reply_markup": buttons_for_player(card),
                            })
                        else:
                            tg_call(token, "sendMessage", {"chat_id": chat_id, "text": " ⛔ لا يوجد لاعب بهذا الاسم."})
                    elif not text.startswith("/"):
                        raw = fetch_player(text)
                        if raw:
                            card = player_card(raw)
                            tg_call(token, "sendMessage", {
                                "chat_id": chat_id,
                                "text": bot_player_message(card),
                                "reply_markup": buttons_for_player(card),
                            })
                        else:
                            tg_call(token, "sendMessage", {
                                "chat_id": chat_id,
                                "text": " ⛔ لا يوجد لاعب بهذا الاسم — اكتب الاسم بدون مسافات (مثل mbappe).",
                                "reply_markup": buttons_for_menu(),
                            })
                cb = u.get("callback_query")
                if cb:
                    bot_handle_callback(token, u)
        except requests.RequestException as e:
            print(f"{C('YELLOW')}⚠️ اتصال مفقود ({e}) — إعادة بعد 5 ثوانٍ...{RST()}")
            time.sleep(5)

# ---------- نقطة الدخول ----------
def main():
    parser = argparse.ArgumentParser(description="Avetaar EFootball Player")
    parser.add_argument("--bot", action="store_true", help="شغل وضع البوت")
    args, unknown = parser.parse_known_args()
    if args.bot:
        bot_run_long_poll()
    else:
        terminal_menu_loop()

if __name__ == "__main__":
    main()
