"""Read-only plan contract checks. Not a media renderer or a semantic quality judge."""
import argparse, hashlib, json, math, re
from pathlib import Path

SKILL = 'gameplay-video-editor'
class ContractError(ValueError): pass
def need(condition, message):
    if not condition: raise ContractError(message)
def text(value, label):
    need(isinstance(value,str) and bool(value.strip()), label+' must be nonempty text')
    return value
def num(value, label, positive=False):
    need(isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value),label+' must be a finite number')
    need(value>0 if positive else value>=0,label+' is out of range')
    return value
def rows(value,label):
    need(isinstance(value,list) and bool(value),label+' must be a nonempty list')
    need(all(isinstance(v,dict) for v in value),label+' entries must be objects')
    return value
def ids(value,label):
    result={}
    for row in rows(value,label):
        key=text(row.get('id'),label+' id');need(key not in result,'duplicate '+label+' id: '+key);result[key]=row
    return result
def span(row,limit,start='start',end='end'):
    a=num(row.get(start),start);b=num(row.get(end),end)
    need(a<b and b<=limit+0.001,'invalid/out-of-range interval '+start+'/'+end)
    return a,b
def cover(items,total):
    intervals=sorted(span(row,total) for row in rows(items,'timeline'))
    cursor=0.0
    for a,b in intervals:
        need(a<=cursor+0.001,'timeline has an uncovered gap at '+str(cursor))
        cursor=max(cursor,b)
    need(cursor>=total-0.001,'timeline does not cover output end')
def cover_window(items,start,end):
    intervals=[]
    for row in items:
        a=max(start,row['start']);b=min(end,row['end'])
        if b>a:intervals.append({'start':a-start,'end':b-start})
    cover(intervals,end-start)
def source_clip(row,source_duration):
    a,b=span(row,source_duration,'source_in','source_out')
    speed=num(row.get('speed',1),'speed',True)
    expected=(b-a)/speed
    need(abs((row['end']-row['start'])-expected)<=0.05,'clip output duration does not match source interval/speed')
    return a,b

def check_role(d,base,check_files):
    text(d.get('source_id'),'source_id');source_duration=num(d.get('source_duration'),'source_duration',True)
    duration=num(d.get('output_duration'),'output_duration',True)
    need(d.get('stage') in ['candidates','edit_ready'],'declare candidates/edit_ready stage')
    events=ids(d.get('events'),'event');clips=rows(d.get('clips'),'clips');cover(clips,duration)
    for e in events.values():
        span(e,source_duration,'source_in','source_out')
        need(e.get('type') in ['gameplay','reaction'],'distinguish game event and reaction')
        evidence=rows(e.get('evidence'),'event evidence')
        for signal in evidence:text(signal.get('description'),'event evidence description')
        if e.get('verified') is True and e['type']=='gameplay':
            need(any(s.get('kind') in ['hud','visual','game_log'] for s in evidence),'audio excitement alone cannot verify a gameplay outcome')
    used=[];event_coverage={}
    for clip in clips:
        event_id=clip.get('event_id');need(event_id in events,'clip references unknown event')
        if d['stage']=='edit_ready':need(events[event_id].get('verified') is True,'edit_ready clip uses unverified event')
        a,b=source_clip(clip,source_duration)
        event_coverage.setdefault(event_id,[]).append({'start':a,'end':b})
        overlap=any(min(b,y)-max(a,x)>0.001 for x,y in used)
        if overlap:need(clip.get('replay') is True,'reused source interval must be marked replay')
        used.append((a,b))
    if d['stage']=='edit_ready':
        for event_id,intervals in event_coverage.items():
            cover_window(intervals,events[event_id]['source_in'],events[event_id]['source_out'])


def inspect_plan(data,base=None,check_files=False):
    try:
        need(isinstance(data,dict),'plan must be an object')
        need(data.get('skill')==SKILL,'plan belongs to a different skill')
        check_role(data,Path(base or '.'),check_files)
        errors=[]
    except (ContractError,KeyError,TypeError,ValueError,OSError,AttributeError) as exc:
        errors=[str(exc)]
    return {'skill':SKILL,'contract_valid':not errors,'errors':errors,'scope':'declared plan and optional file fingerprints only','quality':'requires role-specific human/semantic and rendered-output review; no tools, media generation or external services executed'}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path)
    # No external media/service inspection is claimed by this checker.
    args=p.parse_args()
    try:
        data=json.loads(args.plan.read_text(encoding='utf-8'))
        result=inspect_plan(data,args.plan.resolve().parent,False)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result['contract_valid'] else 1
    except (OSError,ValueError) as exc:
        print(json.dumps({'contract_valid':False,'errors':[str(exc)]},ensure_ascii=False));return 2
if __name__=='__main__': raise SystemExit(main())
