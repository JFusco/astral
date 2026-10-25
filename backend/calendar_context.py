"""Official FOMC meeting dates, scoped context only; no complete macro calendar."""
from calendar import month_name, month_abbr
from datetime import datetime, timedelta
from html.parser import HTMLParser
import re
from zoneinfo import ZoneInfo

FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"


class Meetings(HTMLParser):
    def __init__(self):
        super().__init__();self.year=None;self.month=None;self.capture=None;self.text=[];self.depth=0;self.rows=[]

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class", "").split()
        if self.capture:
            if tag == self.capture[1]: self.depth += 1
        elif tag == "h4":
            self.capture=("heading",tag);self.text=[];self.depth=1
        elif tag == "div" and any(c in classes for c in ("fomc-meeting__month", "fomc-meeting__date")):
            self.capture=("month" if "fomc-meeting__month" in classes else "day",tag);self.text=[];self.depth=1

    def handle_data(self, data):
        if self.capture:self.text.append(data)

    def handle_endtag(self, tag):
        if not self.capture or tag != self.capture[1]:return
        self.depth -= 1
        if self.depth:return
        kind=self.capture[0];value=" ".join("".join(self.text).split());self.capture=None
        if kind == "heading":
            match=re.fullmatch(r"(\d{4}) FOMC Meetings",value)
            self.year=int(match[1]) if match else None;self.month=None
        elif kind == "month":self.month=value
        elif self.year and self.month:self.rows.append((self.year,self.month,value))


def parse_fomc(body):
    parser=Meetings();parser.feed(body.decode("utf-8"));events=[]
    months={name:i for names in (month_name,month_abbr) for i,name in enumerate(names) if name}
    for year,month,days in parser.rows:
        # Fail visibly if the publisher changes its date syntax. Never silently
        # omit an unsupported cross-month date or invent an announcement time.
        match=re.fullmatch(r"(\d{1,2})(?:-(\d{1,2}))?\*?(?: \(notation vote\))?",days)
        names=month.split("/")
        if not match or any(name not in months for name in names) or len(names)>2:
            raise ValueError("Unsupported official FOMC date syntax")
        start=datetime(year,months[names[0]],int(match[1]),tzinfo=ZoneInfo("America/New_York"))
        end=datetime(year,months[names[-1]],int(match[2] or match[1]),tzinfo=ZoneInfo("America/New_York"))+timedelta(days=1)
        if not start < end or (end-start).days>4:raise ValueError("Invalid FOMC interval")
        events.append({"key": start.date().isoformat(), "headline": "FOMC meeting: "+month+" "+days+", "+str(year),
                       "url": FOMC_URL, "created_at": None, "updated_at": None,
                       "event_start": start.isoformat(), "event_end_exclusive": end.isoformat(),
                       "precision": "official meeting dates; time unspecified", "calendar_scope": "Scheduled FOMC meetings only"})
    if len(events)<8:raise ValueError("Incomplete or changed FOMC calendar page")
    return events
