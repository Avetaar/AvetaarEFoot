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

API_BASE = "https://api.efootballdb.com/api/2022"
API_PLAYERS = f"{API_BASE}/players"
API_TEAMS   = f"{API_BASE}/teams"
API_COMPS   = f"{API_BASE}/competitions"
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
    team = team_field.get("team")
    if team:
        return (team.get("english_name") or team.get("licensed_abb_name") or "غير متوفر").strip()
    return (team_field.get("english_name") or team_field.get("licensed_abb_name") or "غير متوفر").strip()

def pick_teams(raw: dict) -> tuple:
    """يعيد (اسم النادي، اسم المنتخب) مع معالجة تكرار: لو النادي=المنتخب (منتخب) → النادي 'غير متوفر'."""
    club = team_name_from(raw.get("current_club_id") or raw.get("club_team"))
    nat  = team_name_from(raw.get("national_team"))
    if club == nat and nat.lower() != "غير متوفر":
        club = "غير متوفر"
    return club, nat

def fetch_player(handle: str, timeout: int = 20):
    """يعيد dict للاعب أو None إذا ما فيه."""
    handle = (handle or "").strip().lower()
    if not handle:
        return None
    try:
        r = requests.get(f"{API_PLAYERS}/{handle}", headers=API_HEADERS, timeout=timeout)
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
    data = d["data"]
    # data is a list on success — take first entry; guard against string/dict
    if isinstance(data, list) and data:
        entry = data[0]
        if isinstance(entry, dict):
            return entry
    return None

def fetch_all_cards(handle: str, timeout: int = 20):
    """يعيد كل كارتات اللاعب (نسخ مختلفة) أو قائمة فارغة.
    كل عنصر: {'card_type','gp_price','coin_price','price','level','max_level','form','iconic','star','variation'}"""
    handle = (handle or "").strip().lower()
    if not handle:
        return []
    try:
        r = requests.get(f"{API_PLAYERS}/{handle}", headers=API_HEADERS, timeout=timeout)
    except requests.RequestException:
        return []
    if r.status_code != 200:
        return []
    try:
        d = r.json()
    except ValueError:
        return []
    data = d.get("data") if isinstance(d, dict) else None
    if not isinstance(data, list) or not data:
        return []
    CARD_TYPE_NAMES = {
        0: "أساسي", 3: "مطوّر", 4: "نادر", 5: "نسخة", 6: "تطوير",
    }
    cards = []
    for c in data:
        if not isinstance(c, dict):
            continue
        ct = c.get("card_type")
        price = c.get("gp_price") or c.get("price") or c.get("coin_price")
        cards.append({
            "card_type":   ct,
            "type_name":   CARD_TYPE_NAMES.get(ct, f"نوع {ct}"),
            "price":       price,
            "level":       c.get("level"),
            "max_level":   c.get("max_level"),
            "form":        c.get("form"),
            "iconic":      bool(c.get("iconic")),
            "star":        c.get("star_player"),
            "variation":   c.get("variation"),
            "speed":       c.get("speed"),
            "finishing":   c.get("finishing"),
            "dribbling":   c.get("dribbling"),
            "main_pos":    c.get("main_position_text"),
        })
    # ترتيب: الأساسية أولاً، بعد ذي أسعار، بعد بقية
    cards.sort(key=lambda x: (
        x["card_type"] != 0,
        -(x["price"] or 0),
        -(x["star"] or 0),
    ))
    return cards

def fetch_team(team_id, timeout: int = 20):
    """يعيد dict لفريق (بالـ pes_id أو الاسم الجزئي) أو None.
    يشمل: name, coach, squad (قائمة لاعبيه), competitions, tactics."""
    if team_id is None:
        return None
    q = str(team_id).strip()
    if not q:
        return None
    try:
        r = requests.get(f"{API_TEAMS}/{q}", headers=API_HEADERS, timeout=timeout)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        d = r.json()
    except ValueError:
        return None
    data = d.get("data") if isinstance(d, dict) else None
    # لو بحث بالاسم الجزئي يرجع list — نختار الأول
    if isinstance(data, list):
        data = data[0] if data else None
    if not isinstance(data, dict):
        return None
    coach = data.get("coach") or {}
    squad = []
    for a in (data.get("player_assignments") or []):
        p = a.get("player") or {}
        squad.append({
            "shirt":   a.get("shirt_number"),
            "name":    p.get("player_name", "؟"),
            "pos":     p.get("main_position_text", "؟"),
            "speed":   p.get("speed"),
            "star":    p.get("star_player"),
        })
    squads = []
    for s in squad:
        price_note = ""
        squads.append(s)
    comps = []
    for c in (data.get("competitions") or []):
        cname = (c.get("competition") or {}).get("competition_name") if isinstance(c.get("competition"), dict) else c.get("competition_name")
        comps.append(cname or "؟")
    return {
        "id":        data.get("pes_id"),
        "name":      data.get("english_name") or data.get("licensed_abb_name") or "؟",
        "abbr":      data.get("licensed_abb_name", ""),
        "coach":     coach.get("english_name") or coach.get("player_name") or "؟",
        "country":   (data.get("country") or {}).get("english_name", "؟"),
        "is_nat":    bool(data.get("is_national_team")),
        "squad":     squads,
        "comps":     comps,
    }

def fetch_competitions(timeout: int = 20):
    """يعيد قائمة المسابقات (75) من الـ API."""
    try:
        r = requests.get(API_COMPS, headers=API_HEADERS, timeout=timeout)
    except requests.RequestException:
        return []
    if r.status_code != 200:
        return []
    try:
        d = r.json()
    except ValueError:
        return []
    data = d.get("data") if isinstance(d, dict) else None
    if not isinstance(data, list):
        return []
    out = []
    for c in data:
        if not isinstance(c, dict):
            continue
        out.append({
            "name":   c.get("competition_name", "؟"),
            "group":  c.get("competition_group"),
            "id":     c.get("pes_id"),
        })
    # إزالة التكرار (نفس الاسم يظهر بعدة مرات)
    seen, uniq = set(), []
    for c in out:
        if c["name"] not in seen:
            seen.add(c["name"])
            uniq.append(c)
    return uniq

def player_card(p: dict) -> dict:
    """يبني بطاقة نظيفة من رد الـ API (معالجة كل الحقول الفاصلة + معالجة تكرار الفريق)."""
    club, nat = pick_teams(p)
    return {
        "handle":  p.get("base_pes_id") or p.get("pes_id") or "",
        "name":    p.get("player_name", "غير متوفر"),
        "club":    club,
        "nat":     nat,
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
    print(f"{C('YELLOW')}  ‣ 🏟️ {card['club']}   ‣ 🏳️ {card['nat']}{RST()}")
    extra = []
    if card["age"]:    extra.append(f"🎂 {card['age']}")
    if card["height"]: extra.append(f"📏 {card['height']} سم")
    if card["weight"]: extra.append(f"⚖️ {card['weight']} كجم")
    if card["foot"]:   extra.append(f"🦶 {card['foot']}")
    if card["star"]:   extra.append(f"⭐ نجم {card['star']}")
    if extra:
        print(f"{C('BLUE')}   ‣ {'  ·  '.join(extra)}{RST()}")
    print(f"{C('MAGENTA')}   ‣ 🧩 المركز: {card['pos']} {RST()}")
    print(f"{C('CYAN')}{THIN}{RST()}")
    print(f"{C('GREEN')}   الإحصائيات الرئيسية{RST()}")
    for k, v in card["stats"].items():
        if isinstance(v, int):
            filled = min(max(v, 0), 30)
            bar = "▮" * filled + "▯" * (30 - filled)
            print(f"   ‣ {k:<10} {v:<3}  {C('LIGHTWHITE_EX')}{bar}{RST()}")
        else:
            print(f"   ‣ {k:<10} غير متوفر")
    print(f"{C('CYAN')}{LINE}{RST()}")
    print(f"{C('LIGHTBLACK_EX')}   بيانات eFootball PES{RST()}")

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
# ---------- الألوان (استخدمت في نظام الأزرار، متاحة للاستخدام المباشر) ----------
BTN_BLUE    = "#3297FD"
BTN_GREEN   = "#45D0A8"
BTN_RED     = "#E05252"
BTN_YELLOW  = "#F0B429"
BTN_PURPLE  = "#8B5CF6"

# ---------- الرموز المميزة (من ريتوال إيموجيز في الذاكرة) ----------
try:
    import Avetaar_emojis as EMO  # PREMIUM_EMOJI_IDS + tg() + auto()
    HAS_EMOJI = True
except Exception:
    HAS_EMOJI = False

def tg(em: str, doc_id=None, size=None) -> str:
    """ينشر رمز مميز (premium) عند دعمه، وإلا يخلي الإيموجي الأساسي (fallback)."""
    if HAS_EMOJI and EMO:
        return EMO.tg(em, doc_id=doc_id, size=size)
    return em

def auto_emojis(text: str) -> str:
    """بدّل كل الإيموجيز في النص برموز مميزة (تلقائي)."""
    if HAS_EMOJI and EMO:
        return EMO.auto(text)
    return text

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
    """يرسل طلب تلغرام. يستخدم JSON body (وليس query string) حتى يتعامل مع reply_markup كـ object."""
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", json=params, timeout=30)
    d = r.json()
    if not d.get("ok"):
        raise RuntimeError(d.get("description", str(r.status_code)))
    return d.get("result")

def esc(s) -> str:
    return html.escape(str(s), quote=False)

def stat_bar(v, width=18):
    """شريط مختصر 18 خانة — يطلع شكله نظيف على الجوال (كل خانة = ~5.5 نقطة من 99)."""
    if not isinstance(v, int):
        return "—"
    filled = max(0, min(width, round(v * width / 99)))
    return "▓" * filled + "░" * (width - filled)

def bot_cards_message(handle: str, cards: list) -> str:
    """رسالة تلغرام لكارتات اللاعب (نسخ مختلفة + أسعار)."""
    L = [f"🎴 <b>كارتات {esc(handle)}</b>", ""]
    if not cards:
        L.append("ما فيه كارتات متاحة لهذا اللاعب.")
        return auto_emojis("\n".join(L))
    L.append(f"إجمالي الكارتات: <b>{len(cards)}</b>")
    L.append("")
    # عرض كل نوع كارت (مجمّع) — الأهم: الرئيسي + ذي أسعار
    shown = []
    for c in cards:
        line = f"🃏 <b>{esc(c['type_name'])}</b>  ⭐{c.get('star') or '؟'}"
        if c.get("price"):
            line += f"  💰 {c['price']:,} GP"
        if c.get("max_level"):
            line += f"  📈 max {c['max_level']}"
        if c.get("iconic"):
            line += "  👑 أسطوري"
        shown.append(line)
        if len(shown) >= 12:  # سطر تلغرام محدود — نوقف عند 12
            break
    L.extend(shown)
    L.append("")
    if len(cards) > 12:
        L.append(f"⚡ باقي {len(cards) - 12} كارت من نفس الأنواع.")
    L.append("⚽ eFootball PES")
    return auto_emojis("\n".join(L))

def bot_team_message(team: dict) -> str:
    """رسالة تلغرام لبطاقة فريق (تشكيلة + مدرب + منافسات)."""
    L = []
    flag = "🏳️" if team["is_nat"] else "🏟️"
    L.append(f"{flag} <b>{esc(team['name'])}</b>")
    if team["abbr"]:
        L.append(f"   <i>اسم مختصر: {esc(team['abbr'])}</i>")
    L.append("")
    if team.get("coach") and team["coach"] != "؟":
        L.append(f"🧑‍🏫 المدير: <b>{esc(team['coach'])}</b>")
    if team.get("country") and team["country"] != "؟":
        L.append(f"🌍 الدولة: {esc(team['country'])}")
    if team.get("comps"):
        L.append("🏆 المنافسات: " + "، ".join(esc(c) for c in team["comps"][:3]))
    L.append("")
    L.append(f"👥 <b>التشكيلة ({len(team['squad'])} لاعب)</b>")
    for s in team["squad"][:15]:
        star = f"⭐{s['star']}" if s.get("star") else ""
        L.append(f"  ‣ #{s['shirt']}  <b>{esc(s['name'])}</b>  ({esc(s['pos'])}) {star}".rstrip())
    if len(team["squad"]) > 15:
        L.append(f"  ⚡ ... و {len(team['squad']) - 15} لاعب إضافي.")
    L.append("")
    L.append("⚽ eFootball PES")
    return auto_emojis("\n".join(L))

def bot_comps_message(comps: list) -> str:
    """رسالة تلغرام لقائمة المسابقات."""
    L = [f"🏆 <b>المسابقات ({len(comps)})</b>", ""]
    # نعرض حتى 20 (حد طول الرسالة)
    for c in comps[:20]:
        L.append(f"  ‣ {esc(c['name'])}")
    if len(comps) > 20:
        L.append(f"  ⚡ ... و {len(comps) - 20} مسابقة أخرى.")
    L.append("")
    L.append("⚽ eFootball PES")
    return auto_emojis("\n".join(L))

def bot_compare_message(name_a: str, name_b: str, card_a: dict, card_b: dict) -> str:
    """رسالة تلغرام لمقارنة لاعبين جنب بعض."""
    L = [f"⚔️ <b>مقارنة: {esc(card_a['name'])} vs {esc(card_b['name'])}</b>", ""]
    L.append(f"{'':<2}  {esc(card_a['name']):<18} {esc(card_b['name']):<18}")
    L.append(" " + "─" * 38)
    rows = [
        ("🏟️", card_a["club"], card_b["club"]),
        ("🏳️", card_a["nat"],  card_b["nat"]),
        ("🎂", str(card_a["age"] or "؟"), str(card_b["age"] or "؟")),
        ("🧩", card_a["pos"],  card_b["pos"]),
    ]
    for emoji, va, vb in rows:
        L.append(f"{emoji}  {str(va):<18} {str(vb):<18}")
    L.append("")
    L.append("⚡ <b>الإحصائيات</b>")
    for emoji, k in [("🚀","السرعة"),("🌀","المراوغة"),("✋","التحكم بالكرة"),
                     ("🎯","التمرير القصير"),("⚽","التسديد"),("💪","القوة البدنية"),
                     ("🔥","التمركز الهجومي"),("🔋","التحمل"),("🗻","الرأسيات"),("🛡️","الضغط الدفاعي")]:
        va = card_a["stats"][k] or 0
        vb = card_b["stats"][k] or 0
        bar_a = stat_bar(va, 12)
        bar_b = stat_bar(vb, 12)
        L.append(f"{emoji} {k}: <b>{va}</b> {bar_a}  |  <b>{vb}</b> {bar_b}")
    L.append("")
    L.append("⚽ eFootball PES")
    return auto_emojis("\n".join(L))

def bot_player_message(card: dict) -> str:
    """رسالة تلغرام منظمة — كل سطر مستقل و قصير (بدون ‡/·، شريط مختصر، parse_mode HTML)."""
    L = []
    # السطر الأول: اسم اللاعب
    L.append(f"⚽ <b>{esc(card['name'])}</b>")
    L.append("")

    # سطر النادي + المنتخب (كل واحد في خانته، بدون تكرار)
    if card["club"] != "غير متوفر":
        L.append(f"🏟️ {esc(card['club'])}")
    if card["nat"] != "غير متوفر":
        L.append(f"🏳️ {esc(card['nat'])}")

    # سطر المعلومات الأساسية (كل سطر مستقل)
    if card["age"]:
        L.append(f"🎂 العمر: {card['age']}")
    if card["height"]:
        L.append(f"📏 الطول: {card['height']} سم")
    if card["weight"]:
        L.append(f"⚖️ الوزن: {card['weight']} كجم")
    if card["foot"]:
        L.append(f"🦶 القدم المفضلة: {card['foot']}")
    if card["star"]:
        L.append(f"⭐ نجم {card['star']}")
    L.append(f"🧩 المركز: <b>{esc(card['pos'])}</b>")
    L.append("")

    # الإحصائيات — كل سطر: emoji + الاسم + الرقم + شريط مختصر (18 خانة)
    L.append("⚡ <b>الإحصائيات</b>")
    for emoji, k, v in [
        ("🚀", "السرعة",         card["stats"]["السرعة"]),
        ("🌀", "المراوغة",       card["stats"]["المراوغة"]),
        ("✋", "التحكم",         card["stats"]["التحكم بالكرة"]),
        ("🎯", "التمرير",       card["stats"]["التمرير القصير"]),
        ("⚽", "التسديد",       card["stats"]["التسديد"]),
        ("💪", "القوة البدنية",  card["stats"]["القوة البدنية"]),
        ("🔥", "الهجوم",         card["stats"]["التمركز الهجومي"]),
        ("🔋", "التحمل",         card["stats"]["التحمل"]),
        ("🗻", "الرأسيات",        card["stats"]["الرأسيات"]),
        ("🛡️", "الدفاع",         card["stats"]["الضغط الدفاعي"]),
    ]:
        L.append(f"{emoji} {k}: <b>{v}</b>  {stat_bar(v)}")
    L.append("")
    L.append("⚽ eFootball PES")
    return auto_emojis("\n".join(L))

# ---------- نظام ألوان الأزرار ----------
# حقل "style" الرسمي (Bot API 9.4+) — قيمه 3 بس: primary=أزرق | success=أخضر | danger=أحمر
# + رمز لون في نص الزر (🟦🟩🟥) كاحتياط لو العميل ما يدعم style
BTN_STYLE = {
    "search":   ("primary", "🟦"),   # أزرق — البحث والتنقل
    "players":  ("success", "🟩"),   # أخضر — لاعبين
    "positive": ("success", "🟩"),   # أخضر — إجراءات إيجابية (إعادة، آخر استعلام)
    "negative": ("danger",  "🟥"),   # أحمر — إجراءات سالبة (إلغاء، خروج)
    "info":     ("primary", "🟦"),   # أزرق — معلومات/ميزات
}

# أيقونة الزر → معرّف الرمز المميز (لو الزر بداء بإيموجي، يظهر رمز premium بدل الإيموجي)
BTN_ICONS = {
    "⚽": "5974235702701853774",  # target ball
    "🎴": "5444854925903295394",  # card
    "👟": "5319250759110374827",  # cat/quick
    "🧊": "5316599316884766402",  # ice
    "🛡️": "5251203410396458957",  # shield
    "🏆": "5188344996356448758",  # trophy
    "❌": "5210952531676504517",  # cross
    "⚔️": "5319156402973849743",  # compare
    "🔁": "5316635510574169206",  # back
    "✍️": "5445128296276718145",  # write
}

# أيقونة الزر حسب نوعه (callback_data prefix) → معرّف الرمز المميز (sticker)
BTN_ICON_BY_CB = {
    "playerprompt": "5974235702701853774",  # target
    "cardsprompt":  "5444854925903295394",  # card
    "search:":      "5319250759110374827",  # quick player
    "teamprompt":   "5251203410396458957",  # shield
    "comps":        "5188344996356448758",  # trophy
    "exit":         "5210952531676504517",  # cross
    "menu":         "5316635510574169206",  # back
    "replay:":      "5316635510574169206",  # back
    "cards:":       "5444854925903295394",  # card
    "cmp:":         "5319156402973849743",  # compare
    "cmpdo:":       "5319156402973849743",  # compare
    "cmpwrite:":    "5445128296276718145",  # write
    "teamq:":       "5251203410396458957",  # shield
}

def _btn(text: str, callback_data: str, color_key: str) -> dict:
    """زر inline: حقل "style" الرسمي (أزرق/أخضر/أحمر) + icon (رمز مميز) حسب نوع الزر."""
    style, mark = BTN_STYLE.get(color_key, ("", ""))
    b = {"text": text, "callback_data": callback_data}
    if style:
        b["style"] = style
    # أيقونة مميزة حسب prefix من callback_data (تظهر كـ sticker بدل الإيموجي المكرر)
    icon_id = None
    for prefix, ic in BTN_ICON_BY_CB.items():
        if callback_data.startswith(prefix):
            icon_id = ic
            break
    if icon_id:
        b["icon_custom_emoji_id"] = icon_id
    return b

def buttons_for_player(card: dict):
    """يعيد inline-keyboard كـ object — الـ API يتوقعه بنية dict بـ 'inline_keyboard'."""
    # نضيف أزرار الميزات الجديدة: كارتات + مقارنة (تحتاج اللاعب الثاني من القايمة)
    return {
        "inline_keyboard": [
            [
                _btn("إعادة", "menu", "search"),
                _btn("آخر استعلام", f"replay:{card['handle']}", "positive"),
                _btn("الكارتات", f"cards:{card['handle']}", "info"),
            ],
            [
                _btn("مقارنة", f"cmp:{card['handle']}", "info"),
            ],
        ]
    }

def bot_handle_callback(token, update):
    cb = update["callback_query"]
    chat_id = cb["message"]["chat"]["id"]
    data = cb["data"]
    tg_call(token, "answerCallbackQuery", {"callback_query_id": cb["id"]})
    if data == "menu":
        tg_call(token, "sendMessage", {"chat_id": chat_id, "text": "اختر:", "reply_markup": buttons_for_menu()})
    elif data == "exit":
        tg_call(token, "sendMessage", {"chat_id": chat_id, "text": " 👋 إلى اللقاء! اضغط /start للعودة."})
    elif data.startswith("search:"):
        handle = data[7:]
        _send_player_result(token, chat_id, handle)
    elif data.startswith("replay:"):
        handle = data[7:]
        raw = fetch_player(handle)
        if raw:
            card = player_card(raw)
            tg_call(token, "editMessageText", {
                "chat_id": chat_id,
                "message_id": cb["message"]["message_id"],
                "text": bot_player_message(card),
                "parse_mode": "HTML",
                "reply_markup": buttons_for_player(card),
            })
        else:
            tg_call(token, "sendMessage", {"chat_id": chat_id, "text": " ⛔ لا توجد بيانات لهذا اللاعب."})
    elif data.startswith("teamq:"):
        # اختيار فريق من أزرار "أشهر الفرق"
        team_q = data[6:]
        _send_team_result(token, chat_id, team_q)
    elif data == "playerprompt":
        # زر "استعلام لاعب" — يطلب الاسم بالكتابة
        _pending_action[chat_id] = "player"
        tg_call(token, "sendMessage", {
            "chat_id": chat_id,
            "text": "اكتب اسم اللاعب بالإنجليزية (بدون مسافات):\nمثل: <code>mbappe</code> أو <code>messi</code>",
            "parse_mode": "HTML",
            "reply_markup": buttons_for_menu(),
        })
    elif data == "cardsprompt":
        # زر "كارتات لاعب" — يطلب الاسم بالكتابة
        _pending_action[chat_id] = "cards"
        tg_call(token, "sendMessage", {
            "chat_id": chat_id,
            "text": "اكتب اسم اللاعب لعرض كل كارتاته:\nمثل: <code>mbappe</code>",
            "parse_mode": "HTML",
            "reply_markup": buttons_for_menu(),
        })
    elif data == "teamprompt":
        # زر "تشكيلة فريق" — يعرض أشهر الفرق كأزرار (ما يحتاج كتابة)
        team = fetch_team("paris")  # عرض افتراضي + أزرار
        tg_call(token, "sendMessage", {
            "chat_id": chat_id,
            "text": "اختر فريقًا لعرض تشكيلته:",
            "reply_markup": buttons_for_teams(),
        })
    elif data == "comps":
        # زر "المسابقات" — يعرض القائمة مباشرة
        comps = fetch_competitions()
        if comps:
            tg_call(token, "sendMessage", {
                "chat_id": chat_id,
                "text": bot_comps_message(comps),
                "parse_mode": "HTML",
                "reply_markup": buttons_for_menu(),
            })
        else:
            tg_call(token, "sendMessage", {"chat_id": chat_id, "text": " ⛔ تعذّر جلب قائمة المسابقات."})
    elif data.startswith("cmp:"):
        # زر مقارنة من بطاقة اللاعب — يعرض أزرار اختيار اللاعب الثاني
        first_handle = data[4:]
        tg_call(token, "sendMessage", {
            "chat_id": chat_id,
            "text": f"مقارنة <b>{esc(first_handle)}</b> مع من؟ اختر:",
            "parse_mode": "HTML",
            "reply_markup": buttons_for_compare(first_handle),
        })
    elif data.startswith("cmpdo:"):
        # اختيار فعلي للاعب الثاني من أزرار المقارنة: cmpdo:first:second
        parts = data.split(":", 2)
        if len(parts) == 3:
            first, second = parts[1], parts[2]
            _send_compare_result(token, chat_id, first, second)

# تخزين مؤقت للإجراء المعلّق لكل محادثة (عند استخدام الأزرار اللي تتطلب كتابة)
_pending_action = {}

def buttons_for_compare(first_handle: str):
    """أزرار اختيار اللاعب الثاني للمقارنة + زر رجوع للقائمة."""
    QUICK = ["mbappe", "messi", "kane", "neuer", "saka", "aliy"]
    quick = [q for q in QUICK if q != first_handle]
    return {
        "inline_keyboard": [
            [
                _btn("⚔️ مقابل " + q, f"cmpdo:{first_handle}:{q}", "info")
                for q in quick[:3]
            ],
            [
                _btn("رجوع للقائمة", "menu", "search"),
                _btn("كتابة يدوية", f"cmpwrite:{first_handle}", "negative"),
            ],
        ]
    }

def buttons_for_menu():
    """يعيد inline-keyboard كـ object — كل شيء بأزرار (بدون أوامر).
    نظام الألوان: الأزرق للبحث/التنقل، الأخضر للاعبين، الأصفر للميزات، الأحمر للخروج."""
    return {
        "inline_keyboard": [
            [
                _btn("استعلام لاعب", "playerprompt", "search"),     # أزرق — استعلام لاعب
                _btn("كارتات لاعب", "cardsprompt", "info"),        # أصفر — كارتات
            ],
            [
                _btn("mbappe", "search:mbappe", "players"),        # أخضر — لاعب
                _btn("messi", "search:messi", "players"),
                _btn("kane", "search:kane", "players"),
            ],
            [
                _btn("تشكيلة فريق", "teamprompt", "info"),        # أصفر — فريق
                _btn("المسابقات", "comps", "info"),                # أصفر — مسابقات
            ],
            [
                _btn("خروج", "exit", "negative"),                  # أحمر — خروج
            ],
        ]
    }

def _handle_update(token, u):
    """معالجة تحديث واحد (رسالة أو callback) — البوت لا يتوقف على أي خطأ هنا."""
    msg = u.get("message")
    if msg:
        text = (msg.get("text") or "").strip()
        chat_id = msg["chat"]["id"]
        tl = text.lower()
        # كل التفاعل بأزرار — /start و /help يفتحان القائمة فقط
        if tl in ("/start", "start", "ابدأ", "/help", "help", "دليل", "/"):
            tg_call(token, "sendMessage", {
                "chat_id": chat_id,
                "text": " 👋 أهلا! اضغط زرًا من القائمة للتفاعل (كل شيء بأزرار):",
                "reply_markup": buttons_for_menu(),
            })
        elif not text.startswith("/"):
            # نص عادي — نتحقق من الإجراء المعلّق (من زر playerprompt أو cardsprompt)
            if chat_id in _pending_action:
                action = _pending_action.pop(chat_id)
                if action == "player":
                    _send_player_result(token, chat_id, text)
                elif action == "cards":
                    _send_cards_result(token, chat_id, text)
            else:
                # ما فيه إجراء معلّق — نتعامل مع النص كاسم لاعب (أبسط استخدام)
                _send_player_result(token, chat_id, text)
    cb = u.get("callback_query")
    if cb:
        bot_handle_callback(token, u)

def _send_player_result(token, chat_id, handle):
    """يستعلم لاعب ويرسل النتيجة (بطاقة + أزرار) أو رسالة خطأ."""
    raw = fetch_player(handle)
    if raw:
        card = player_card(raw)
        tg_call(token, "sendMessage", {
            "chat_id": chat_id,
            "text": bot_player_message(card),
            "parse_mode": "HTML",
            "reply_markup": buttons_for_player(card),
        })
    else:
        tg_call(token, "sendMessage", {
            "chat_id": chat_id,
            "text": " ⛔ لا يوجد لاعب بهذا الاسم — اكتب الاسم بدون مسافات (مثل mbappe).",
            "reply_markup": buttons_for_menu(),
        })

def _send_cards_result(token, chat_id, handle):
    """يعرض كل كارتات اللاعب."""
    cards = fetch_all_cards(handle)
    tg_call(token, "sendMessage", {
        "chat_id": chat_id,
        "text": bot_cards_message(handle, cards),
        "parse_mode": "HTML",
        "reply_markup": buttons_for_menu(),
    })

def _send_team_result(token, chat_id, handle):
    """يعرض بطاقة فريق (تشكيلة + مدرب + منافسات)."""
    team = fetch_team(handle)
    if team:
        tg_call(token, "sendMessage", {
            "chat_id": chat_id,
            "text": bot_team_message(team),
            "parse_mode": "HTML",
            "reply_markup": buttons_for_menu(),
        })
    else:
        # لو الاسم الجزئي ما نجح، نعرض أشهر الفرق كأزرار
        tg_call(token, "sendMessage", {
            "chat_id": chat_id,
            "text": f" ⛔ ما وريث فريق باسم <b>{esc(handle)}</b>. جرّب اسمًا إنجليزيًا جزئيًا، أو اختر من القائمة:",
            "parse_mode": "HTML",
            "reply_markup": buttons_for_teams(),
        })

def buttons_for_teams():
    """أزرار أشهر الفرق (بالأسماء الجزئية اللي تشتغل)."""
    TEAMS = ["paris", "liverpool", "england", "france", "spain", "germany", "italy", "brazil"]
    return {
        "inline_keyboard": [
            [
                _btn(t, f"teamq:{t}", "info") for t in TEAMS[:4]
            ],
            [
                _btn(t, f"teamq:{t}", "info") for t in TEAMS[4:]
            ],
            [
                _btn("رجوع للقائمة", "menu", "search"),
            ],
        ]
    }

def _send_compare_result(token, chat_id, handle_a, handle_b):
    """مقارنة لاعبين جنب بعض."""
    raw_a = fetch_player(handle_a)
    raw_b = fetch_player(handle_b)
    if not raw_a or not raw_b:
        missing = []
        if not raw_a: missing.append(handle_a)
        if not raw_b: missing.append(handle_b)
        tg_call(token, "sendMessage", {
            "chat_id": chat_id,
            "text": f" ⛔ ما وريث لاعب باسم: {', '.join(esc(x) for x in missing)}. جرّب اسمًا بدون مسافات.",
            "reply_markup": buttons_for_menu(),
        })
        return
    card_a = player_card(raw_a)
    card_b = player_card(raw_b)
    tg_call(token, "sendMessage", {
        "chat_id": chat_id,
        "text": bot_compare_message(handle_a, handle_b, card_a, card_b),
        "parse_mode": "HTML",
        "reply_markup": buttons_for_menu(),
    })

def _single_instance_lock():
    """قفل ضمان نسخة وحدة — يمنع 'Conflict: terminated by other getUpdates request'.
    يعتمد على os.kill(pid, 0) (يشيك وجود العملية على ويندوز ولينكس) — ما يحتاج tasklist/wmic."""
    import signal
    lock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bot_lock")
    if os.path.exists(lock_path):
        with open(lock_path) as f:
            old_pid = f.read().strip()
        try:
            os.kill(int(old_pid), 0)  # شغال؟
            return False  # نسخة قديمة ما زالت شغالة — لا تنشأ جديدة
        except (ProcessLookupError, ValueError, OSError):
            pass  # النسخة القديمة متوفاة أو PID غير صالح — امسح القفل العالق
        os.remove(lock_path)
    with open(lock_path, "w") as f:
        f.write(str(os.getpid()))
    return True

def bot_run_long_poll():
    token = load_bot_token()
    if not token:
        sys.exit("لا يوجد بوت تكين. أنشئ بوتا مع @BotFather وضع التوكن في ملف .env بجانب السكربت:\n  BOT_TOKEN=123456:ABC...")
    if not _single_instance_lock():
        sys.exit(f"{C('YELLOW')}⚠️ نسخة بوت أخرى شغالة حالياً — أغلها أولاً (Ctrl+C) ثم شغّل نسخة وحدة.{RST()}")
    # كل التفاعل بأزرار (بدون أوامر) — ما يحتاج setMyCommands
    print(f"{C('GREEN')}🚀 البوت شغّال... (Ctrl+C للإيقاف){RST()}")
    # استخدم timeout=10 (وليس 30) — لو الاتصال بـ api.telegram.org ضعيف،
    # getUpdates راجع كل 10 ثوانٍ وراح يكمل بدون انقطاع طويل.
    last_update_id = 0
    error_count = 0
    while True:
        try:
            d = tg_call(token, "getUpdates", {
                "limit": 100,
                "offset": last_update_id + 1,
                "timeout": 10,
            })
            error_count = 0  # اتصال ناجح — صفّر العدّاد
            for u in d:
                last_update_id = u["update_id"]
                try:
                    _handle_update(token, u)
                except Exception as e:
                    print(f"{C('RED')}⛔ خطأ في معالجة التحديث: {e} — تم تخطي.{RST()}")
        except requests.RequestException as e:
            error_count += 1
            wait = min(5 * error_count, 30)  # تصاعدي: 5، 10، 15... حتى 30 ثانية
            print(f"{C('YELLOW')}⚠️ اتصال مفقود ({e}) — إعادة بعد {wait} ثوانٍ...{RST()}")
            time.sleep(wait)
        except RuntimeError as e:
            error_count += 1
            wait = min(5 * error_count, 30)
            print(f"{C('YELLOW')}⚠️ خطأ تلغرام: {e} — إعادة بعد {wait} ثوانٍ...{RST()}")
            time.sleep(wait)

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
    try:
        main()
    finally:
        # إزالة قفل النسخة الوحيدة عند الخروج
        lock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bot_lock")
        if os.path.exists(lock_path):
            os.remove(lock_path)
