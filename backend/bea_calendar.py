"""Scoped BEA schedule; a date is retained without inventing an unspecified timezone."""
from calendar import month_name
from datetime import datetime, timedelta
from html.parser import HTMLParser
import hashlib
import re
from zoneinfo import ZoneInfo

URL = "https://www.bea.gov/news/schedule"


class Schedule(HTMLParser):
    def __init__(self):
        super().__init__(); self.active=False; self.cell=None; self.text=[]; self.rows=[]; self.row=[]; self.year=None

    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=="table" and attrs.get("id")=="release-schedule-table":self.active=True
        if not self.active:return
        if tag=="tr":self.row=[]
        if tag in {"td","th"}:self.cell=tag; self.text=[]
        if self.cell and tag in {"small","div"}:self.text.append(" ")

    def handle_data(self, data):
        if self.active and self.cell:self.text.append(data)

    def handle_endtag(self, tag):
        if not self.active:return
        if tag==self.cell:
            text=" ".join("".join(self.text).split());self.cell=None
            if tag=="th" and re.fullmatch(r"Year \d{4}",text):self.year=int(text[-4:])
            if tag=="td":self.row.append(text)
        if tag=="tr" and self.row:self.rows.append((self.year,self.row))
        if tag=="table":self.active=False


def parse_bea(body):
    parser=Schedule();parser.feed(body.decode("utf-8"));result=[]
    months={name:i for i,name in enumerate(month_name) if name}
    for year,cells in parser.rows:
        if year is None or len(cells)!=3:raise ValueError("Changed BEA schedule structure")
        match=re.fullmatch(r"([A-Za-z]+) (\d{1,2}) (\d{1,2}):(\d{2}) (AM|PM)",cells[0])
        if not match or match[1] not in months or not cells[2]:raise ValueError("Unsupported BEA date")
        # The schedule page omits a timezone. Use the whole U.S. Eastern date
        # as a conservative exclusion interval; retain the printed clock text.
        day=datetime(year,months[match[1]],int(match[2]),tzinfo=ZoneInfo("America/New_York"))
        key=hashlib.sha256((cells[0]+cells[2]+str(year)).encode()).hexdigest()
        result.append({"key":key,"headline":"BEA: "+cells[2],"url":URL,"created_at":None,"updated_at":None,
                       "event_start":day.isoformat(),"event_end_exclusive":(day+timedelta(days=1)).isoformat(),
                       "source_clock_text":cells[0],"precision":"Conservative Eastern date interval; page clock timezone unspecified",
                       "calendar_scope":"BEA published release schedule only"})
    if not result:raise ValueError("BEA schedule is empty or unavailable")
    return result
