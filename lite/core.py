"""IPTV Studio core - standard library only. Nothing is sent to GitHub here."""
from __future__ import annotations
import concurrent.futures, csv, datetime, json, os, re, socket, urllib.parse, urllib.request, urllib.error, ssl, time
from advanced_probe import probe_round,aggregate,ffprobe_fallback
from dataclasses import dataclass, field
from pathlib import Path

SOURCE_1 = 'https://raw.githubusercontent.com/khanh71/All-In-One-IPTV/main/http-iptv.m3u'
SOURCE_3 = 'https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/main/vmttv'
CURRENT_GIST_ID = 'e63b2927598a4b932b3708ddd3183aaa'
OUTPUT_NAME = 'iptv.m3u'
LEGACY_NAME = 'VTV_FULL_2_NGUON.m3u'
FAIL_GROUP = '99 - KÊNH LỖI'
VTV_1 = '01 - VTV NGUỒN 1'
VTV_3 = '02 - VTV NGUỒN 3'
LIVE_GROUP = '03 - LIVE EVENTS 🔴'
UA = 'Mozilla/5.0 (compatible; IPTVStudio/5.0; +local)' 
GROUP_RE = re.compile(r'\bgroup-title\s*=\s*(?:"[^"]*"|\x27[^\x27]*\x27|[^\s,]+)',re.I)
GROUP_GET = re.compile(r'\bgroup-title\s*=\s*(?:"([^"]*)"|\x27([^\x27]*)\x27|([^\s,]+))',re.I)
HEADER_RE = re.compile(r'\b(?:url-tvg|x-tvg-url)\s*=\s*"([^"]*)"',re.I)


def defaults():
    return {
        'sources': [
            {'id':'source-1','title':'Nguồn 1 · All-In-One-IPTV','url':SOURCE_1,'role':'primary1','enabled':True},
            {'id':'source-3','title':'Nguồn 3 · VMTTV','url':SOURCE_3,'role':'primary3','enabled':True},
        ],
        'check_streams': True,
        'workers': 12,
        'timeout': 6,
        'retries': 2,
        'rounds': 3,
        'strict_unknown': False,
        'ffprobe_enabled': False,
        'gist_id': CURRENT_GIST_ID,
        'expected_account': 'trisanghy',
        'keep_legacy': True,
        'output_dir': str(Path.home()/'Downloads'),
    }


def validate_config(cfg):
    sources = cfg.get('sources')
    if not isinstance(sources,list) or not sources or len(sources)>25:
        raise ValueError('Cần 1–25 nguồn playlist.')
    seen=set()
    for s in sources:
        if not isinstance(s,dict): raise ValueError('Nguồn không hợp lệ.')
        if not s.get('enabled',True): continue
        if not str(s.get('title','')).strip(): raise ValueError('Nguồn thiếu tên.')
        url = str(s.get('url','')).strip()
        if not valid_web_url(url): raise ValueError('URL nguồn phải là http:// hoặc https://: '+str(s.get('title')))
        if s.get('role') not in ('primary1','primary3','normal'):
            raise ValueError('Vai trò nguồn không hợp lệ.')
        if s.get('role') in ('primary1','primary3'):
            if s['role'] in seen: raise ValueError('Mỗi nguồn VTV ưu tiên chỉ được chọn một lần.')
            seen.add(s['role'])
    if not any(s.get('enabled',True) for s in sources): raise ValueError('Hãy bật ít nhất 1 nguồn.')
    workers = int(cfg.get('workers',12)); timeout=float(cfg.get('timeout',6)); retries=int(cfg.get('retries',1))
    if not (1 <= workers <= 24 and 2<=timeout<=25 and 1<=retries<=3): raise ValueError('Tùy chọn kiểm tra ngoài khoảng cho phép.')
    rounds = int(cfg.get('rounds',3))
    if rounds not in (2,3,4): raise ValueError('Số vòng kiểm tra phải là 2, 3 hoặc 4.')
    dest = Path(cfg.get('output_dir') or str(Path.home()/'Downloads')).expanduser()
    if not dest.is_absolute(): raise ValueError('Thư mục lưu phải là đường dẫn tuyệt đối.')


def valid_web_url(url):
    if not isinstance(url,str) or any(c.isspace() for c in url) or any(ord(c)<32 for c in url):return False
    try:
        p=urllib.parse.urlsplit(url)
        return p.scheme.lower() in ('http','https') and bool(p.hostname)
    except (ValueError,UnicodeError):return False


def download_text(url,timeout=25):
    req=urllib.request.Request(url, headers={'User-Agent':UA,'Accept':'*/*','Cache-Control':'no-cache'})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        buf=resp.read(16*1024*1024+1)
    if len(buf)>16*1024*1024: raise ValueError('Playlist vượt giới hạn 16 MB.')
    text=buf.decode('utf-8-sig',errors='replace')
    if '#EXTINF' not in text:raise ValueError('Không tìm thấy dòng #EXTINF trong nguồn.')
    if '<html' in text[:256].lower():raise ValueError('Máy chủ trả HTML thay vì M3U.')
    return text


@dataclass
class Channel:
    lines: list[str]
    source_title: str
    role: str
    origin_group: str
    group: str = ''
    status: str='UNCHECKED'
    reason: str='Chưa kiểm tra'
    checks: list = field(default_factory=list)

    @property
    def url(self):
        for x in self.lines[1:]:
            if x.strip() and not x.lstrip().startswith('#'):
                return x.strip()
        return ''
    @property
    def name(self):
        return self.lines[0].split(',',1)[-1].strip() if self.lines else ''


def group_of(lines):
    if not lines:return ''
    m=GROUP_GET.search(lines[0])
    if m:return next((g for g in m.groups() if g is not None),'')
    for line in lines[1:]:
        if line.upper().startswith('#EXTGRP:'): return line.partition(':')[2].strip()
    return ''


def parse_m3u(data,source):
    header = '#EXTM3U'
    channels=[]; cur=None
    for raw in data.lstrip('\ufeff').splitlines():
        line=raw.strip()
        if line.startswith('#EXTM3U') and cur is None and not channels:
            header=line
        elif line.startswith('#EXTINF'):
            if cur:channels.append(Channel(cur,source['title'],source['role'],group_of(cur)))
            cur=[line]
        elif cur is not None and line:
            cur.append(line)
    if cur:channels.append(Channel(cur,source['title'],source['role'],group_of(cur)))
    if not channels:raise ValueError('Playlist không chứa kênh.')
    return header,channels


def is_vtv(ch):
    n=ch.name.casefold().strip(); g=ch.origin_group.casefold().strip()
    if re.match(r'^vtv\s*(?:[1-9]|10)(?!\d)',n):return True
    if n.startswith('vietnam today'):return True
    return g in {'vtv','📺 vtv','🇻🇳 vtv','📺| vtv'} and not n.startswith('vtvcab')


def is_live(ch):
    return 'live event' in ch.origin_group.casefold() or 'live event' in ch.name.casefold() and not ch.origin_group


def set_group(lines,new_group):
    lines=list(lines)
    sanitized=new_group.replace('"','\x27').replace('\r','').replace('\n','')
    tag=f'group-title="{sanitized}"'
    if GROUP_RE.search(lines[0]):lines[0]=GROUP_RE.sub(lambda m:tag,lines[0],count=1)
    else:
        i=lines[0].find(',')
        lines[0]=(lines[0][:i]+' '+tag+lines[0][i:]) if i>=0 else (lines[0]+' '+tag)
    for i in range(1,len(lines)):
        if lines[i].upper().startswith('#EXTGRP:'):lines[i]='#EXTGRP:'+sanitized
    return lines


def merge_playlist(source_pairs):
    if not source_pairs:raise ValueError('Không có playlist hợp lệ.')
    from collections import OrderedDict
    groups=OrderedDict([(VTV_1,[]),(VTV_3,[]),(LIVE_GROUP,[])])
    epgs=[]; total=0
    for source,text in source_pairs:
        header,channels=parse_m3u(text,source)
        for header_epg in HEADER_RE.findall(header):
            for epg in re.split(r'[,;]',header_epg):
                if epg.strip() and epg.strip() not in epgs:epgs.append(epg.strip())
        total+=len(channels)
        for ch in channels:
            if is_vtv(ch) and source['role']=='primary1': group=VTV_1
            elif is_vtv(ch) and source['role']=='primary3':group=VTV_3
            elif is_live(ch):group=LIVE_GROUP
            elif is_vtv(ch):group='VTV - '+source['title']
            else:group=ch.origin_group or ('KHÁC - '+source['title'])
            ch.group=group
            groups.setdefault(group,[]).append(ch)
    return [ch for items in groups.values() for ch in items],epgs,dict((g,len(v)) for g,v in groups.items() if v),total


def header_for(epgs):
    return '#EXTM3U' + (' url-tvg="'+','.join(epgs)+'"' if epgs else '')


def serialize(channels,epgs):
    result=[header_for(epgs)]
    for ch in channels:
        result.extend(set_group(ch.lines,ch.group))
    return '\n'.join(result)+'\n'


def headers_for(ch):
    headers={'User-Agent':UA,'Accept':'*/*','Cache-Control':'no-cache'}
    for line in ch.lines[1:]:
        low=line.lower()
        if low.startswith('#extvlcopt:http-user-agent='):headers['User-Agent']=line.split('=',1)[1].strip()
        elif low.startswith('#extvlcopt:http-referrer='):headers['Referer']=line.split('=',1)[1].strip()
    return headers


def probe_url(url,headers,timeout=8):
    """Compatibility wrapper: a single multi-stage probe (not full round consensus)."""
    result=probe_round(url,headers,timeout)
    return result.status,result.reason


def check_channels(channels,workers=12,timeout=8,retries=2,progress=None,rounds=3,
                   strict_unknown=False,ffprobe_enabled=False):
    """Repeated independent probes, no HEAD-only false positives.

    Round checks: URL + GET manifest + variant(s) + real segment bytes.
    Voting: >=2 successful proof rounds => OK; repeated proven failures => FAIL;
    ambiguous/blocked/transient => UNKNOWN unless explicitly strict.
    """
    unique={}
    for ch in channels:
        key=(ch.url,tuple(sorted(headers_for(ch).items())))
        unique.setdefault(key,[]).append(ch)
    done=0;total=len(unique)
    def check_one(item):
        (url,h_items),chan=item
        outcome=[]
        for round_no in range(rounds):
            result=probe_round(url,dict(h_items),timeout)
            # Retry transient failure once per round when enabled; 404/410 are definitive.
            if result.status=='UNKNOWN' and retries>1:
                for _ in range(retries-1):
                    again=probe_round(url,dict(h_items),timeout)
                    if again.status!='UNKNOWN':result=again;break
            outcome.append(result)
            if round_no < rounds-1: time.sleep(0.15)
        state,detail=aggregate(outcome,strict_unknown=strict_unknown)
        if state=='UNKNOWN' and ffprobe_enabled:
            ff=ffprobe_fallback(url,dict(h_items),timeout)
            if ff.status=='OK':state,detail='OK',detail+'; '+ff.reason
        return chan,state,detail,[p.status+': '+p.reason for p in outcome]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(check_one,kv) for kv in unique.items()]
        for f in concurrent.futures.as_completed(futures):
            try:
                all_channels,state,detail,outcomes=f.result()
            except Exception as e:
                all_channels=[];state='UNKNOWN';detail='Lỗi worker '+type(e).__name__;outcomes=[]
            for ch in all_channels:
                ch.status=state;ch.reason=detail;ch.checks=outcomes
            done+=1
            if progress and (done%5==0 or done==total):progress(done,total)
    return channels


def vn_check_time():
    """Use Vietnam's UTC+7 time independently of host machine timezone."""
    tz=datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz).strftime('%d/%m/%Y %H:%M')


def date_live_group(channels,checked_at=None,was_checked=True):
    checked_at=checked_at or vn_check_time()
    name=LIVE_GROUP + (' | Kiểm tra: '+checked_at if was_checked else ' | CHƯA KIỂM TRA')
    for ch in channels:
        if ch.group==LIVE_GROUP:ch.group=name
    return name


def finalize(channels,epgs):
    kept=[];bad=[]
    for ch in channels:
        if ch.status=='FAIL':
            ch.group=FAIL_GROUP;bad.append(ch)
        else:kept.append(ch)
    return serialize(kept+bad,epgs)


def count_status(channels):
    return {s:sum(ch.status==s for ch in channels) for s in ('OK','FAIL','UNKNOWN','UNCHECKED')}


def publication_risk(channels):
    total=len(channels)
    if not total:return 'Không có kênh.'
    statuses=count_status(channels)
    if statuses['UNCHECKED']==total:return ''
    if statuses['OK']<max(4,int(total*0.04)):
        return 'Quá ít kênh phản hồi OK; có thể đường mạng/CDN bị chặn. Chưa nên ghi đè Gist.'
    if statuses['FAIL']>max(20,int(total*.3)):
        return 'Hơn 30% kênh báo FAIL; cần kiểm tra trước khi ghi đè Gist.'
    return ''


def save_files(channels,epgs,out_dir,checked_at=None,was_checked=True):
    target=Path(out_dir).expanduser()
    target.mkdir(parents=True,exist_ok=True)
    if not target.is_dir():raise ValueError('Thư mục xuất không hợp lệ.')
    original=serialize(channels,epgs) # Keep original categories before moving FAIL.
    live_label=date_live_group(channels,checked_at,was_checked=was_checked)
    final=finalize(channels,epgs)
    # final file atomically replaced only after success of full workflow
    def write_atomic(path,value):
        tmp=path.with_suffix(path.suffix+'.tmp')
        tmp.write_text(value,encoding='utf-8')
        os.replace(tmp,path)
    write_atomic(target/'iptv_goc_chua_loc.m3u',original)
    write_atomic(target/OUTPUT_NAME,final)
    report=target/'BAO_CAO_KENH_IPTV.csv'
    tmp=report.with_suffix('.tmp')
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['STT','Nguồn','Kênh','Nhóm gốc','Nhóm xuất','Trạng thái','Lý do','Vòng kiểm tra','URL'])
        for n,ch in enumerate(channels,1):
            w.writerow([n,ch.source_title,ch.name,ch.origin_group,ch.group,ch.status,ch.reason,' | '.join(ch.checks),ch.url])
    os.replace(tmp,report)
    return final,str(target/OUTPUT_NAME),str(report)
