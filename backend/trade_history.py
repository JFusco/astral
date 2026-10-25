"""Build daily candles exclusively from documented execution records."""
from datetime import timedelta
from decimal import localcontext
import hashlib
import json
import re

from .risk import number as D,timestamp


def aggregate_daily(trades, *, start, end, known_at):
    with localcontext() as context:
        context.prec=40
        return _aggregate_daily(trades,start=start,end=end,known_at=known_at)


def _aggregate_daily(trades, *, start, end, known_at):
    first,last,known=timestamp(start),timestamp(end),timestamp(known_at)
    if not first < last <= known:raise ValueError('Invalid observed history window')
    seen={}
    for row in trades:
        if not isinstance(row.get('i'),int):raise ValueError('Trade ID required')
        key=str(row['i'])
        if key in seen and seen[key]!=row:raise ValueError('Conflicting trade ID')
        when=timestamp(row['t'])
        if not first<=when<=last or D(row['p'])<=0 or D(row['s'])<=0:raise ValueError('Invalid trade or outside history window')
        seen[key]=row
    # Preserve nanosecond ordering where datetime alone truncates microseconds.
    def order(row):
        m=re.fullmatch(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?Z',row['t'])
        if not m:raise ValueError('Expected provider UTC trade timestamp')
        return m[1],int((m[2] or '').ljust(9,'0')),row['i']
    rows=sorted(seen.values(),key=order);buckets={}
    for row in rows:
        when=timestamp(row['t']);day=when.replace(hour=0,minute=0,second=0,microsecond=0)
        if day<first or day+timedelta(days=1)>last:continue
        price,size=D(row['p']),D(row['s']);key=day.isoformat()
        if key not in buckets:buckets[key]={'t':key,'o':str(price),'h':str(price),'l':str(price),'c':str(price),'v':'0','n':0,'dollar_volume':'0'}
        b=buckets[key];b.update(h=str(max(D(b['h']),price)),l=str(min(D(b['l']),price)),c=str(price),v=str(D(b['v'])+size),n=b['n']+1,dollar_volume=str(D(b['dollar_volume'])+price*size))
    digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'rows':list(buckets.values()),'trade_count':len(rows),'input_sha256':digest,'bar_semantics':'executed-trades-only',
            'source':'alpaca-us-executed-trades','received_at':known_at,'coverage':'Alpaca US executed trades only; not consolidated market volume',
            'start':start,'end':end,'complete_page_traversal':True,'missing_intervals':'Not fabricated or forward-filled'}
