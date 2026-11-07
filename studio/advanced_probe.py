"""Multi-stage IPTV probes: URL -> manifest -> child playlists -> real media bytes.

No third-party dependencies. A successful manifest ALONE is never sufficient for OK.
Non-http streams, geo restrictions and most transient failures are UNKNOWN, not proof of death.
"""
from __future__ import annotations
import concurrent.futures
import json
import re
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

MAX_MANIFEST = 512 * 1024
MAX_MEDIA_PROBE = 32 * 1024
_MAX_REDIRECTS = 8
UA = 'Mozilla/5.0 (compatible; IPTVStudio/5.0; local-playlist-check)'

@dataclass
class Probe:
    status: str
    reason: str
    evidence: str = ''

class ProbeError(Exception):
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason
        super().__init__(reason)


def normalize_url(url: str, headers: dict):
    url = (url or '').strip()
    if not url: raise ProbeError('FAIL', 'URL phát trống')
    if any(ord(c) < 32 or c.isspace() for c in url):
        raise ProbeError('FAIL', 'URL chứa ký tự trắng/điều khiển')
    if url.startswith('/http') or url.startswith('http:/ '):
        raise ProbeError('FAIL', 'URL bị thêm dấu /')
    # IPTV (Kodi-style) uses |Referer=x&User-Agent=y as headers.
    if '|' in url:
        base,pipe = url.split('|',1)
        if '=' in pipe and re.search(r'(?i)(?:^|&)(?:user-agent|referer|referrer|origin|cookie|authorization)=', pipe):
            url=base
            for k,v in urllib.parse.parse_qsl(pipe,keep_blank_values=True):
                if k.casefold() in ('user-agent','referer','referrer','origin','cookie','authorization'):
                    headers['Referer' if k.casefold()=='referrer' else k.title() if k.casefold()!='user-agent' else 'User-Agent']=v
    try: parsed=urllib.parse.urlsplit(url)
    except ValueError: raise ProbeError('FAIL', 'URL không hợp lệ')
    if parsed.scheme.lower() not in ('http','https'):
        raise ProbeError('UNKNOWN', 'Luồng không phải HTTP/HLS: '+parsed.scheme[:24])
    if not parsed.hostname:raise ProbeError('FAIL','URL thiếu hostname')
    if parsed.port is not None and (parsed.port<1 or parsed.port>65535):
        raise ProbeError('FAIL','Cổng URL sai')
    return url


def fetch(url,headers,timeout,max_bytes,segment=False):
    request_headers = {'User-Agent':UA, 'Accept':'*/*', 'Accept-Encoding':'identity', **headers}
    # Partial transfer for live video; some servers ignore Range, which is also fine.
    if segment:request_headers['Range']=f'bytes=0-{max_bytes-1}'
    request=urllib.request.Request(url,headers=request_headers,method='GET')
    try:
        with urllib.request.urlopen(request,timeout=timeout) as resp:
            status=resp.getcode()
            ct=(resp.headers.get('Content-Type') or '').lower()
            body=resp.read(max_bytes)
            final=resp.geturl()
            if status not in (200,206):raise ProbeError('UNKNOWN',f'HTTP {status}')
            return body,ct,final
    except urllib.error.HTTPError as e:
        if e.code in (404,410):raise ProbeError('FAIL',f'HTTP {e.code}: luồng/segment không tồn tại')
        if e.code in (401,403,407,429,451):raise ProbeError('UNKNOWN',f'HTTP {e.code}: yêu cầu xác thực/giới hạn truy cập')
        if e.code in (400,422):raise ProbeError('FAIL',f'HTTP {e.code}: yêu cầu URL không hợp lệ')
        raise ProbeError('UNKNOWN',f'HTTP {e.code}: máy chủ tạm lỗi')
    except (TimeoutError, socket.timeout):raise ProbeError('UNKNOWN','Timeout khi đọc dữ liệu')
    except urllib.error.URLError as e:
        msg=str(e.reason).lower()
        if any(t in msg for t in ('name or service not known','nodename nor servname','no address associated','name resolution','no such host','nxdomain')):
            raise ProbeError('FAIL','DNS không phân giải được tên miền')
        if 'certificate verify failed' in msg:raise ProbeError('UNKNOWN','Lỗi chứng chỉ SSL')
        raise ProbeError('UNKNOWN','Lỗi kết nối '+str(e.reason)[:90])
    except ConnectionError:raise ProbeError('UNKNOWN','Máy chủ ngắt kết nối')
    except (ValueError,UnicodeError) as e:raise ProbeError('FAIL','URL sai định dạng '+str(e)[:60])


def looks_html(body:bytes,content_type:str):
    sample=body[:2048].lstrip(b'\xef\xbb\xbf\x00 \t\n\r').lower()
    if 'text/html' in content_type:return True
    return any(marker in sample[:900] for marker in (b'<html',b'<!doctype html',b'<head',b'<body',b'<title>'))


def looks_media(data:bytes,ct='', encrypted=False):
    if len(data)<256:return False,'Dữ liệu media quá ngắn'
    if looks_html(data,ct):return False,'Nhận HTML thay vì video'
    if data.lstrip().startswith((b'{',b'[',b'<?xml',b'#EXTM3U')):
        return False,'Nhận JSON/XML/playlist thay vì segment'
    # MPEG-TS is 188 bytes/packet. Accept packet alignment offsets for ID3-prefix streams.
    for start in (0,4,16,32,64,128,188):
        if len(data)>start+188*3 and all(data[start+188*i]==0x47 for i in range(4)):
            return True,'MPEG-TS có 4 sync packets'
    if any(tag in data[4:32] for tag in (b'ftyp',b'moof',b'mdat',b'styp',b'sidx')):
        return True,'MP4/fMP4 media bytes'
    if data.startswith((b'\x1a\x45\xdf\xa3',b'ID3',b'OggS',b'FLV')):
        return True,'Có chữ ký container media'
    if data[:2] in (b'\xff\xf1',b'\xff\xf9'):
        return True,'AAC ADTS'
    if 'video/' in ct or 'audio/' in ct or 'octet-stream' in ct or 'application/mp2t' in ct:
        if len(data)>=4096 and len(set(data[:2048]))>12:
            return True,'Nhận đủ binary media, định dạng chưa nhận diện chắc chắn'
    if encrypted and len(data)>=1024 and any(b!=0 for b in data[:1024]):
        return True,'Segment mã hóa: nhận đủ dữ liệu (không xác minh giải mã)'
    return False,'Không nhận diện được bytes media'


def parse_attr(tag:str,attr='URI'):
    match=re.search(r'(?i)(?:^|[:,])\s*'+re.escape(attr)+r'\s*=\s*"([^"]+)"',tag)
    return match.group(1) if match else None


def check_hls(text:str,base_url:str,headers:dict,timeout:float,depth:int=0):
    if depth>2:return Probe('UNKNOWN','Playlist HLS lồng quá sâu')
    lines=[ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines or lines[0].lstrip('\ufeff')!='#EXTM3U':
        return Probe('FAIL','HLS thiếu #EXTM3U')
    if not any(ln.startswith('#EXT-X-') for ln in lines):
        return Probe('FAIL','M3U kênh, không phải playlist HLS có media')
    variants=[];segments=[];init_map=[];key_urls=[];key_required=False; encrypted=False;drm=False;expect_variant=False
    for i,ln in enumerate(lines):
        if expect_variant:
            if not ln.startswith('#'):variants.append(urllib.parse.urljoin(base_url,ln))
            expect_variant=False
        if ln.startswith('#EXT-X-STREAM-INF:'):expect_variant=True
        elif ln.startswith('#EXT-X-MAP:'):
            map_uri=parse_attr(ln)
            if map_uri:init_map.append(urllib.parse.urljoin(base_url,map_uri))
        elif ln.startswith('#EXT-X-PART:'):
            uri=parse_attr(ln)
            if uri:segments.append(urllib.parse.urljoin(base_url,uri))
        elif ln.startswith('#EXT-X-KEY:'):
            meth=parse_attr(ln,'METHOD') or re.search(r'(?i)METHOD=([^,]+)',ln)
            method=meth if isinstance(meth,str) else (meth.group(1) if meth else '')
            if method.upper() not in ('NONE',''):
                encrypted=True
                if 'KEYFORMAT=' in ln and 'identity' not in ln:drm=True
                if method.upper()=='AES-128':
                    key_required=True
                    key_uri=parse_attr(ln)
                    if key_uri:key_urls.append(urllib.parse.urljoin(base_url,key_uri))
        elif not ln.startswith('#'):
            segments.append(urllib.parse.urljoin(base_url,ln))
    if variants:
        outcomes=[]
        for candidate in variants[:3]:
            try:
                b,ct,url=fetch(candidate,headers,timeout,MAX_MANIFEST)
                if looks_html(b,ct):raise ProbeError('FAIL','Playlist nhánh trả HTML')
                o=check_hls(b.decode('utf-8-sig',errors='replace'),url,headers,timeout,depth+1)
            except ProbeError as e:o=Probe(e.status,'HLS nhánh '+e.reason)
            outcomes.append(o)
            if o.status=='OK':return Probe('OK','HLS master → nhánh → '+o.reason,'manifest+segment')
        # If any variant is unknown, do not claim dead globally.
        return Probe('UNKNOWN' if any(o.status=='UNKNOWN' for o in outcomes) else 'FAIL',
                     'HLS master: '+ '; '.join(o.reason for o in outcomes[:2]))
    if not segments:return Probe('FAIL','Playlist HLS không chứa segment video')
    if drm:return Probe('UNKNOWN','Playlist sử dụng DRM: không xác minh được khả năng giải mã')
    if key_required:
        if not key_urls:return Probe('FAIL','HLS AES-128 không có URL key')
        for key_uri in key_urls[:2]:
            try:
                key_data,key_ct,_=fetch(key_uri,headers,timeout,32,segment=True)
                if looks_html(key_data,key_ct) or len(key_data)!=16:
                    return Probe('FAIL','HLS AES-128 key không hợp lệ')
            except ProbeError as e:
                return Probe('UNKNOWN' if e.status=='UNKNOWN' else 'FAIL','HLS key: '+e.reason)
    # Select newest segment first; one stale media sequence must not be enough to label dead.
    indices=list(dict.fromkeys([len(segments)-1,max(0,len(segments)-2),0]))
    checks=[]
    for idx in indices[:3]:
        seg=segments[idx]
        try:
            body,ct,final=fetch(seg,headers,timeout,MAX_MEDIA_PROBE,segment=True)
            ok,detail=looks_media(body,ct,encrypted)
            if ok:
                if init_map:
                    try:
                        im,ict,_=fetch(init_map[0],headers,timeout,4096,segment=True)
                        if len(im)<8 or looks_html(im,ict):raise ProbeError('FAIL','Init segment hỏng')
                    except ProbeError as e:return Probe('UNKNOWN' if e.status=='UNKNOWN' else 'FAIL','HLS init: '+e.reason)
                return Probe('OK','HLS: manifest hợp lệ + segment video thật ('+detail+')','manifest+segment')
            checks.append(Probe('FAIL',detail))
        except ProbeError as e:checks.append(Probe(e.status,e.reason))
    if all(c.status=='FAIL' for c in checks):return Probe('FAIL','Các segment thử đều lỗi: '+checks[0].reason)
    return Probe('UNKNOWN','Segment không chắc chắn: '+checks[0].reason)


def probe_round(url:str,headers:dict,timeout:float=8):
    headers=dict(headers)
    try:
        url=normalize_url(url,headers)
        body,ct,final=fetch(url,headers,timeout,MAX_MANIFEST if '.m3u8' in url.lower() else 65536)
        if not body:return Probe('UNKNOWN','HTTP 200 nhưng không có dữ liệu')
        if looks_html(body,ct):return Probe('FAIL','HTTP 200 nhưng trả trang HTML')
        trimmed=body.lstrip(b'\xef\xbb\xbf\r\n\t ')
        if trimmed.startswith(b'#EXTM3U') or 'mpegurl' in ct or '.m3u8' in urllib.parse.urlsplit(final).path.lower():
            if not trimmed.startswith(b'#EXTM3U'):
                return Probe('FAIL','HTTP 200 nhưng nội dung không phải HLS')
            return check_hls(trimmed.decode('utf-8-sig',errors='replace'),final,headers,timeout)
        ok,detail=looks_media(body,ct)
        return Probe('OK' if ok else 'UNKNOWN',detail,'media-bytes' if ok else '')
    except ProbeError as exc:return Probe(exc.status,exc.reason)
    except Exception as exc:return Probe('UNKNOWN','Lỗi ngoài dự kiến: '+type(exc).__name__)


def aggregate(outcomes:list[Probe], strict_unknown=False):
    n=len(outcomes);oks=[o for o in outcomes if o.status=='OK'];fails=[o for o in outcomes if o.status=='FAIL'];unknown=[o for o in outcomes if o.status=='UNKNOWN']
    evidence=any(o.evidence in ('manifest+segment','media-bytes') for o in oks)
    min_ok=2 if n>=3 else n
    if len(oks)>=min_ok and evidence:
        status='OK'
    elif not oks and len(fails)>=max(2,(n+1)//2) and not unknown:
        status='FAIL'
    elif not oks and len(fails)>=max(2,(n+1)//2) and strict_unknown:
        status='FAIL'
    else:status='UNKNOWN'
    # Isolate status indicators to preserve row readability, count all rounds.
    count=f'{len(oks)}/{n} OK, {len(fails)} FAIL, {len(unknown)} UNKNOWN'
    why=next((o.reason for o in (fails if status=='FAIL' else unknown if status=='UNKNOWN' else oks) if o.reason),'')
    return status,count+'; '+why


def ffprobe_fallback(url,headers,timeout=8):
    exe=shutil.which('ffprobe')
    if not exe:return Probe('UNKNOWN','ffprobe chưa được cài')
    try:
        args=[exe,'-v','error','-rw_timeout',str(int(timeout*1_000_000)),'-probesize','1000000',
              '-analyzeduration','2000000','-show_entries','stream=codec_type,codec_name',
              '-of','json',url]
        proc=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout+3)
        if proc.returncode==0:
            body=json.loads(proc.stdout or b'{}')
            if any(s.get('codec_type') in ('video','audio') for s in body.get('streams',[])):
                return Probe('OK','ffprobe giải mã được metadata codec','media-bytes')
        return Probe('UNKNOWN','ffprobe chưa xác minh được codec: '+proc.stderr.decode(errors='replace')[:90])
    except Exception as e:return Probe('UNKNOWN','ffprobe lỗi: '+type(e).__name__)
