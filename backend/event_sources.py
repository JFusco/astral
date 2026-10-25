"""Fixed public event sources. Published context is distinct from complete coverage."""
from calendar import month_name, monthrange
from datetime import datetime, timedelta
from html.parser import HTMLParser
import hashlib
import json
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from .risk import timestamp

NYFED = "https://www.newyorkfed.org/research/calendars/nationalecon_cal.html"
MAINTENANCE = "https://status.alpaca.markets/api/v2/scheduled-maintenances/"
BIPS = "https://raw.githubusercontent.com/bitcoin/bips/master/README.mediawiki"
LIFECYCLE = "https://bitcoincore.org/en/lifecycle/"
ETHEREUM = "https://ethereum.org/roadmap/"
KINDS = {"nyfed", "maintenance-upcoming", "maintenance-active", "bips", "bitcoin-lifecycle", "ethereum-roadmap"}


class Cells(HTMLParser):
    """Retain cells in a selected table, including links and their following text."""
    def __init__(self, select):
        super().__init__(); self.select=select; self.depth=0; self.rows=[]; self.row=[]; self.cell=None
        self.heading=False; self.heading_text=[]; self.headings=[]; self.document=[]

    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag in {"script", "style"}:return
        if tag=="table":
            if self.depth:self.depth+=1
            elif self.select(attrs):self.depth=1
        if tag=="td" and "ts-data-table-head" in attrs.get("class","").split():self.heading=True;self.heading_text=[]
        if not self.depth:return
        if tag=="tr":self.row=[]
        if tag in {"td","th"}:self.cell={"text":[],"links":[]};self.link=None
        if self.cell is not None:
            if tag=="a":
                self.link={"url":attrs.get("href",""),"text":[],"after":[]};self.cell["links"].append(self.link)
            if tag=="br":self.cell["text"].append(" ")

    def handle_data(self, data):
        if self.heading:self.heading_text.append(data)
        if self.cell is not None:
            self.cell["text"].append(data)
            if self.cell["links"]:
                target=self.cell["links"][-1]
                target["text" if self.link is target else "after"].append(data)

    def handle_endtag(self, tag):
        if self.heading and tag=="td":self.headings.append(" ".join("".join(self.heading_text).split()));self.heading=False
        if not self.depth:return
        if tag=="a":self.link=None
        if tag in {"td","th"} and self.cell is not None:self.row.append(self.cell);self.cell=None
        if tag=="tr" and self.row:self.rows.append(self.row);self.row=[]
        if tag=="table":self.depth-=1


def event(key, headline, url, start, end, precision, scope, **extra):
    return {"key":key,"headline":headline,"url":url,"created_at":None,"updated_at":None,
            "event_start":start.isoformat(),"event_end_exclusive":end.isoformat(),
            "precision":precision,"calendar_scope":scope,**extra}


def nyfed(body):
    text=body.decode("utf-8")
    if "all Eastern Time" not in text:raise ValueError("NY Fed timezone contract changed")
    p=Cells(lambda a:"research-table-1col" in a.get("class","").split());p.feed(text)
    titles=[re.fullmatch(r"([A-Za-z]+) (\d{4})",v) for v in p.headings]
    titles=[m for m in titles if m]
    if len(titles)!=1:raise ValueError("NY Fed month missing/ambiguous")
    month=list(month_name).index(titles[0][1]);year=int(titles[0][2]);tz=ZoneInfo("America/New_York")
    first=datetime(year,month,1,tzinfo=tz);end=first+timedelta(days=monthrange(year,month)[1]);events=[];days=[]
    for row in p.rows:
        for cell in row:
            value=" ".join("".join(cell["text"]).split());match=re.match(r"^(\d{2})(?:\s|$)",value)
            if not match:continue
            day=int(match[1]);date=datetime(year,month,day,tzinfo=tz);days.append(day)
            if date.weekday()>4:raise ValueError("Unexpected NY Fed calendar day")
            for link in cell["links"]:
                u=urlsplit(link["url"])
                # Only BLS-origin releases, as republished by NY Fed. Never fetch BLS links.
                if u.hostname!="www.bls.gov":continue
                title=" ".join("".join(link["text"]).split())
                clock=re.search(r"\((\d{2}):(\d{2})\)","".join(link["after"]))
                if not clock or not title:raise ValueError("Missing NY Fed release time")
                start=date.replace(hour=int(clock[1]),minute=int(clock[2]))
                events.append(event(str(day)+":"+u.path,"NY Fed / BLS: "+title,NYFED,start,start+timedelta(minutes=1),
                                    "New York Fed published Eastern release time","Key BLS releases republished by NY Fed only",
                                    originating_url=link["url"]))
    expected=[d for d in range(1,monthrange(year,month)[1]+1) if datetime(year,month,d).weekday()<5]
    if days!=expected or not events:raise ValueError("Incomplete/changed NY Fed month")
    return events,{"coverage_from":first.isoformat(),"coverage_until":end.isoformat(),"complete_category":False,
                   "scope":"NY Fed key BLS releases only; not all BLS series or a BLS-authored calendar"}


def maintenance(body, active):
    data=json.loads(body)
    if data["page"]["id"]!="bf49n9xp9x2w" or data["page"]["url"]!="https://status.alpaca.markets":
        raise ValueError("Unexpected status publisher")
    items=data["scheduled_maintenances"]
    if not isinstance(items,list) or len(items)>100:raise ValueError("Invalid maintenance list")
    result=[];seen=set();allowed={"in_progress","verifying"} if active else {"scheduled"}
    for row in items:
        key=row["id"]
        if not isinstance(key,str) or not key or key in seen or row["status"] not in allowed:raise ValueError("Invalid maintenance state")
        seen.add(key);start,end=timestamp(row["scheduled_for"]),timestamp(row["scheduled_until"])
        if end<=start or end-start>timedelta(days=31):raise ValueError("Invalid maintenance interval")
        result.append(event(key,str(row["name"])[:500],"https://status.alpaca.markets",start,end,
                            "Publisher UTC/offset interval","Alpaca published maintenance",
                            maintenance_status=row["status"]))
    return result


def protocol(body, kind):
    """Watch authoritative documents without interpreting proposals as activations."""
    text=body.decode("utf-8");rows=[]
    if kind=="bips":
        if "does not indicate" not in text or "wikitable sortable" not in text:raise ValueError("BIP index contract changed")
        chunks=re.split(r"\n\|-.*\n",text)
        for chunk in chunks[1:]:
            cells=[v or "" for v in re.findall(r"^\|(?: (.*))?$",chunk,re.M)]
            number=re.match(r"\[\[bip-\d+\.(?:mediawiki|md)\|(\d+)\]\]",cells[0]) if cells else None
            if number:
                if len(cells)!=6:raise ValueError("Changed BIP row structure")
                rows.append({"number":int(number[1]),"layer":cells[1],"title":cells[2],"status":cells[5]})
        if len(rows)<100:raise ValueError("Incomplete BIP index")
        summary=f"Bitcoin BIP index: {len(rows)} proposals; document status is not network activation"
        url=BIPS
    elif kind=="bitcoin-lifecycle":
        p=Cells(lambda a:True);p.feed(text)
        for row in p.rows:
            cells=[" ".join("".join(c["text"]).split()) for c in row]
            if len(cells)==3 and re.fullmatch(r"(?:\d+\.)?\d+\.x",cells[0]):rows.append({"version":cells[0],"release":cells[1],"end_of_life":cells[2]})
        if len(rows)<10:raise ValueError("Bitcoin lifecycle table changed")
        summary="Bitcoin Core software lifecycle: "+rows[0]["version"]+" / "+rows[0]["release"]+"; software release is not consensus activation";url=LIFECYCLE
    else:
        # Inspect rendered headings/paragraphs only, never scripts or hydration data.
        class Roadmap(HTMLParser):
            def __init__(self):super().__init__();self.kind=None;self.text=[];self.name=None;self.rows=[];self.skip=0
            def handle_starttag(self,tag,attrs):
                if tag in {"script","style"}:self.skip+=1
                if not self.skip and tag in {"h2","p"}:self.kind=tag;self.text=[]
            def handle_data(self,value):
                if self.kind and not self.skip:self.text.append(value)
            def handle_endtag(self,tag):
                if tag in {"script","style"}:self.skip=max(0,self.skip-1)
                if tag==self.kind:
                    value=" ".join("".join(self.text).split());self.kind=None
                    if tag=="h2":self.name=value
                    elif self.name and re.fullmatch(r"(?:Q[1-4] )?20\d{2}|[A-Z][a-z]+ \d{1,2}, 20\d{2}",value):
                        self.rows.append({"upgrade":self.name,"source_schedule":value});self.name=None
        p=Roadmap();p.feed(text);rows=p.rows
        if len(rows)<5:raise ValueError("Ethereum roadmap structure changed")
        summary="Ethereum roadmap: "+"; ".join(r["upgrade"]+" / "+r["source_schedule"] for r in rows[-2:])+"; intentions are not exact activation times";url=ETHEREUM
    return [{"key":"current-protocol-snapshot","headline":summary[:500],"url":url,"created_at":None,"updated_at":None,
             "protocol_rows":rows,"coverage_complete":False,"calendar_scope":"Protocol watch; complete scheduled activation coverage unknown"}]


def parse_events(kind, body):
    if kind=="nyfed":return nyfed(body)[0]
    if kind.startswith("maintenance-"):return maintenance(body,kind=="maintenance-active")
    return protocol(body,kind)


def catalog(source, body, items, checked):
    """Full source snapshot, separate from the capped UI headline sample."""
    value={"source_id":source.id,"source_url":source.url,"checked_at":checked,
           "retained_body_sha256":hashlib.sha256(body).hexdigest(),
           "events":[{k:v for k,v in i.items() if k in {"event_start","event_end_exclusive","headline","precision","maintenance_status","originating_url"}} for i in items if i.get("event_start")]}
    if source.kind=="nyfed":value.update(nyfed(body)[1])
    elif source.kind.startswith("maintenance-"):
        value.update(coverage_from=checked,coverage_until=(timestamp(checked)+timedelta(hours=48)).isoformat(),
                     complete_category=True,scope="Currently published Alpaca maintenance only; new/unannounced outages not guaranteed absent")
    elif source.kind in {"bips","bitcoin-lifecycle","ethereum-roadmap"}:
        value.update(complete_category=False,scope="Protocol document watch, not a complete activation calendar",snapshots=items)
    return value
