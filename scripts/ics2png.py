import requests, pytz, textwrap, math
from ics import Calendar
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont

# ------- Einstellungen -------
ICS = "https://outlook.office365.com/owa/calendar/543f71192bc94e368be74654f86827f4@espas.ch/f401e8b7dee04a53a30450f5f60ac9fa8638957689972678873/calendar.ics"
W, H = 800, 480                  # ePaper 7.5"
DAYS = 6                         # Anzahl Spalten/Tage
START_TODAY = True               # True: ab heute; False: ab morgen
TZ = pytz.timezone("Europe/Zurich")
MARGIN_X = 14                    # Aussenrand links/rechts
TOP = 16                         # oberer Rand
COL_GAP = 8                      # Abstand zwischen Spalten
HEADER_H = 28                    # Höhe für Tageskopf
MAX_EVENTS_PER_COL = 12          # harte Obergrenze pro Spalte (Falls sehr voll)

# Schriften (fallen auf Default zurück, falls nicht vorhanden)
try:
    FONT_HDR = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    FONT_TIME = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    FONT_TXT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
except:
    FONT_HDR = FONT_TIME = FONT_TXT = ImageFont.load_default()

# ------- Helpers -------
DAYS_DE = ["Mo","Di","Mi","Do","Fr","Sa","So"]

def day_key(dt):
    d = dt.astimezone(TZ)
    return d.date()

def fmt_day(date_obj):
    wd = DAYS_DE[date_obj.weekday()]
    return f"{wd} {date_obj.day:02}.{date_obj.month:02}."

def fmt_time(dt):
    if not dt: return ""
    d = dt.astimezone(TZ)
    return d.strftime("%H:%M")

def wrap_by_width(draw, text, font, max_w):
    # pragmatisch: textwrap + Breitenprüfung
    lines = []
    for raw in text.replace("\n"," ").split("  "):
        for piece in textwrap.wrap(raw, width=60):
            # schneide weiter runter bis es in die Breite passt
            while draw.textlength(piece, font=font) > max_w and len(piece) > 1:
                piece = piece[:-1]
            lines.append(piece)
    return [l for l in lines if l]

def collect_events(ics_text, start_day, days_count):
    cal = Calendar(ics_text)
    # Zeitfenster
    start_dt = datetime.combine(start_day, datetime.min.time(), tzinfo=TZ)
    end_dt = start_dt + timedelta(days=days_count)
    # Gruppieren nach Datum
    buckets = { (start_day + timedelta(days=i)): [] for i in range(days_count) }
    for e in cal.events:
        # Begin/Ende bestimmen
        begin = e.begin.datetime if e.begin else None
        end = e.end.datetime if e.end else None
        if not begin: continue
        # Filter grob aufs Fenster
        if (end or begin) < start_dt or begin >= end_dt:
            continue
        dkey = day_key(begin)
        # Nur Tage im Fenster aufnehmen
        if dkey in buckets:
            buckets[dkey].append(e)
    # Sortierung je Tag
    for k in buckets:
        buckets[k].sort(key=lambda x: x.begin if x.begin else datetime.max.replace(tzinfo=timezone.utc))
    return buckets

# ------- Render -------
def main():
    try:
        txt = requests.get(ICS, timeout=20).text
    except Exception as ex:
        # Fehlerbild
        img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
        msg = f"Fehler beim Laden der ICS: {ex}"
        for i, line in enumerate(textwrap.wrap(msg, width=46)):
            d.text((20, 40 + i*22), line, font=FONT_TXT, fill="black")
        img.save("docs/ics.png", optimize=True)
        return

    today_local = datetime.now(TZ).date()
    start_day = today_local if START_TODAY else today_local + timedelta(days=1)

    buckets = collect_events(txt, start_day, DAYS)

    # Spaltenbreite
    inner_w = W - 2*MARGIN_X
    col_w = math.floor((inner_w - (DAYS-1)*COL_GAP) / DAYS)
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    # Optional: feine vertikale Trennlinien
    for i in range(DAYS-1):
        x = MARGIN_X + (i+1)*col_w + i*COL_GAP + COL_GAP//2
        d.line([(x, TOP), (x, H - 8)], fill="black", width=1)

    # Jede Spalte zeichnen
    for ci in range(DAYS):
        day = start_day + timedelta(days=ci)
        x = MARGIN_X + ci*(col_w + COL_GAP)
        y = TOP

        # Tageskopf
        head = fmt_day(day)
        d.text((x, y), head, font=FONT_HDR, fill="black")
        y += HEADER_H

        events = buckets.get(day, [])
        if not events:
            d.text((x, y), "– keine Termine –", font=FONT_TXT, fill="black")
            continue

        # Events
        count = 0
        for e in events:
            if count >= MAX_EVENTS_PER_COL: break
            start = e.begin.datetime if e.begin else None
            end = e.end.datetime if e.end else None
