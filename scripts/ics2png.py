import requests, pytz, textwrap, math
from ics import Calendar
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont

# ---- Einstellungen ----
ICS = "https://outlook.office365.com/owa/calendar/543f71192bc94e368be74654f86827f4@espas.ch/f401e8b7dee04a53a30450f5f60ac9fa8638957689972678873/calendar.ics"
W, H = 800, 480            # 7.5" ePaper
DAYS = 5                   # 5 Spalten
START_TODAY = True         # ab heute
TZ = pytz.timezone("Europe/Zurich")

# Layout (enger)
MARGIN_X = 12
TOP = 10
COL_GAP = 6
HEADER_H = 24
MAX_EVENTS_PER_COL = 18
LH = 16                    # Zeilenhoehe Text

# Schriften (kleiner)
try:
    FONT_HDR  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
    FONT_TIME = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    FONT_TXT  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
except:
    FONT_HDR = FONT_TIME = FONT_TXT = ImageFont.load_default()

DAYS_DE = ["Mo","Di","Mi","Do","Fr","Sa","So"]

def day_key(dt): return dt.astimezone(TZ).date()
def fmt_day(date_obj): return f"{DAYS_DE[date_obj.weekday()]} {date_obj.day:02}.{date_obj.month:02}."
def fmt_time(dt): return dt.astimezone(TZ).strftime("%H:%M") if dt else ""

def wrap_by_width(draw, text, font, max_w):
    text = (text or "").replace("\n"," ")
    out = []
    for piece in textwrap.wrap(text, width=80):  # grob vorschneiden
        while draw.textlength(piece, font=font) > max_w and len(piece) > 1:
            piece = piece[:-1]
        if piece: out.append(piece)
    return out

def collect_events(ics_text, start_day, days_count):
    cal = Calendar(ics_text)
    start_dt = datetime.combine(start_day, datetime.min.time(), tzinfo=TZ)
    end_dt = start_dt + timedelta(days=days_count)
    buckets = { (start_day + timedelta(days=i)): [] for i in range(days_count) }
    for e in cal.events:
        begin = e.begin.datetime if e.begin else None
        end = e.end.datetime if e.end else None
        if not begin: continue
        if (end or begin) < start_dt or begin >= end_dt: continue
        dkey = day_key(begin)
        if dkey in buckets: buckets[dkey].append(e)
    for k in buckets:
        buckets[k].sort(key=lambda x: x.begin if x.begin else datetime.max.replace(tzinfo=timezone.utc))
    return buckets

def main():
    # ICS holen
    try:
        txt = requests.get(ICS, timeout=20).text
    except Exception as ex:
        img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
        for i, line in enumerate(textwrap.wrap(f"Fehler beim Laden: {ex}", width=48)):
            d.text((20, 40 + i*LH), line, font=FONT_TXT, fill="black")
        img.save("docs/ics.png", optimize=True); return

    today_local = datetime.now(TZ).date()
    start_day = today_local if START_TODAY else today_local + timedelta(days=1)
    buckets = collect_events(txt, start_day, DAYS)

    inner_w = W - 2*MARGIN_X
    col_w = math.floor((inner_w - (DAYS-1)*COL_GAP) / DAYS)

    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    # optionale Trennlinien
    for i in range(DAYS-1):
        x = MARGIN_X + (i+1)*col_w + i*COL_GAP + COL_GAP//2
        d.line([(x, TOP), (x, H - 6)], fill="black", width=1)

    # Spalten rendern
    for ci in range(DAYS):
        day = start_day + timedelta(days=ci)
        x = MARGIN_X + ci*(col_w + COL_GAP)
        y = TOP

        # Kopf ohne globalen Titel
        d.text((x, y), fmt_day(day), font=FONT_HDR, fill="black")
        y += HEADER_H

        events = buckets.get(day, [])
        if not events:
            d.text((x, y), "– keine Termine –", font=FONT_TXT, fill="black")
            continue

        count = 0
        for e in events:
            if count >= MAX_EVENTS_PER_COL or y > H - LH - 6: break
            start = e.begin.datetime if e.begin else None
            end = e.end.datetime if e.end else None

            time_line = fmt_time(start) + ("–"+fmt_time(end) if end else "")
            d.text((x, y), time_line, font=FONT_TIME, fill="black"); y += LH

            title = (e.name or "Ohne Titel").strip()
            loc = f" · {e.location.strip()}" if e.location else ""
            block = title + loc
            lines = wrap_by_width(d, block, FONT_TXT, col_w - 2)
            for line in lines:
                if y > H - LH - 4: break
                d.text((x, y), line, font=FONT_TXT, fill="black"); y += LH
            y += 4
            count += 1

    img.save("docs/ics.png", optimize=True)

if __name__ == "__main__":
    main()
