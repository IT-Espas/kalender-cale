import requests, textwrap, pytz
from ics import Calendar
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont

ICS = "https://outlook.office365.com/owa/calendar/543f71192bc94e368be74654f86827f4@espas.ch/f401e8b7dee04a53a30450f5f60ac9fa8638957689972678873/calendar.ics"
OUT = "docs/ics.png"
W, H = 800, 480
LIMIT = 10
TZ = pytz.timezone("Europe/Zurich")

try:
    FB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    FN = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
except:
    FB = FN = ImageFont.load_default()

def wrap(t, w=46): return textwrap.wrap((t or "").replace("\n"," "), w)
def fmt(dt): return dt.astimezone(TZ).strftime("%a %d.%m.%Y %H:%M")

def draw_error(msg):
    img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
    d.text((20, 20), "Kalender", font=FB, fill="black")
    for i, line in enumerate(wrap("Fehler: "+msg, 48), start=0):
        d.text((20, 80+i*26), line, font=FN, fill="black")
    img.save(OUT, optimize=True)

def main():
    try:
        txt = requests.get(ICS, timeout=20).text
        cal = Calendar(txt)
        now = datetime.now(timezone.utc)
        events = sorted([e for e in cal.events if (e.end or e.begin) and (e.end or e.begin) >= now],
                        key=lambda e: e.begin)[:LIMIT]

        img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img); y = 16
        d.text((20, y), "Kalender", font=FB, fill="black"); y += 46

        if not events:
            d.text((20, y), "Keine kommenden Termine", font=FN, fill="black")
        else:
            for e in events:
                start = e.begin.datetime if e.begin else None
                when = fmt(start) if start else ""
                title = (e.name or "Ohne Titel").strip()
                loc = (" · " + e.location.strip()) if e.location else ""
                for line in [when] + wrap(title + loc, 46):
                    d.text((20, y), line, font=FN, fill="black"); y += 26
                y += 6
                if y > H - 30: break

        img.save(OUT, optimize=True)
    except Exception as ex:
        draw_error(str(ex))

if __name__ == "__main__":
    main()
