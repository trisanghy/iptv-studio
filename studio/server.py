#!/usr/bin/env python3
"""Localhost-only, zero-pip-dependency, browser-based wizard for Mac/Windows/Linux."""
from __future__ import annotations
import json, os, secrets, threading, time, webbrowser, sys, subprocess, urllib.parse, traceback
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from core import defaults,validate_config,download_text,merge_playlist,check_channels,save_files,count_status,publication_risk,OUTPUT_NAME,valid_web_url,vn_check_time
from github_publish import github_user,publish

APP_DIR=Path.home()/'.iptv_studio'
CONFIG_PATH=APP_DIR/'config.json'
WEB_DIR=(Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'web')
TOKEN=secrets.token_hex(24)
LOCK=threading.RLock()
job={'state':'idle','progress':0,'stage':'Sẵn sàng','message':'','result':None}
last={'playlist':None,'channels':None,'config':None,'summary':None,'epgs':None}


def load_config():
    cfg=defaults()
    if CONFIG_PATH.exists():
        try:
            data=json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
            if isinstance(data,dict):cfg.update(data)
        except Exception:pass
    return cfg


def save_config(cfg):
    validate_config(cfg)
    APP_DIR.mkdir(parents=True,exist_ok=True)
    tmp=CONFIG_PATH.with_suffix('.new')
    tmp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(tmp,CONFIG_PATH)


def update_job(**kwargs):
    with LOCK:job.update(kwargs)


def build_task(cfg):
    try:
        update_job(state='working',stage='Đang tải playlist nguồn…',progress=3,message='',result=None)
        sources=[s for s in cfg['sources'] if s.get('enabled',True)]
        pairs=[]
        for i,s in enumerate(sources):
            update_job(stage=f'Đang tải: {s["title"]}',progress=int(5+23*i/len(sources)))
            pairs.append((s,download_text(s['url'])))
        channels,epgs,groups,total=merge_playlist(pairs)
        if total>20000:raise ValueError('Playlist vượt 20.000 kênh, hãy dùng ít nguồn hơn.')
        if cfg.get('check_streams',True):
            update_job(stage=f'Kiểm tra sâu {len(channels)} kênh × {int(cfg.get("rounds",3))} vòng…',progress=30)
            def progress(done,count):update_job(progress=30+int(55*done/count),stage=f'Đã kiểm tra {done}/{count} link phát…')
            check_channels(channels,workers=int(cfg.get('workers',12)),
                           timeout=float(cfg.get('timeout',8)),retries=int(cfg.get('retries',2)),progress=progress,
                           rounds=int(cfg.get('rounds',3)),strict_unknown=bool(cfg.get('strict_unknown',False)),
                           ffprobe_enabled=bool(cfg.get('ffprobe_enabled',False)))
        update_job(stage='Đang xuất file và báo cáo…',progress=88)
        checked_at=vn_check_time()
        playlist,path,report=save_files(channels,epgs,cfg['output_dir'],checked_at=checked_at,
                                        was_checked=bool(cfg.get('check_streams',True)))
        statuses=count_status(channels)
        summary={'total':len(channels),'status':statuses,'groups':groups,'file':path,'report':report,
                 'risk':publication_risk(channels),'sources':[{'title':s['title'],'url':s['url']} for s in sources],
                 'timestamp':checked_at,'rounds':int(cfg.get('rounds',3)),
                 'deep_check':bool(cfg.get('check_streams',True))}
        with LOCK:last.update(playlist=playlist,channels=channels,config=cfg,summary=summary,epgs=epgs)
        update_job(state='done',stage='Đã xuất iptv.m3u',progress=100,result=summary)
    except Exception as exc:
        update_job(state='error',stage='Có lỗi',message=str(exc)[:1200],progress=0)


def publish_task(payload):
    try:
        update_job(state='publishing',stage='Đang xác minh tài khoản và quyền Gist…',progress=15,message='')
        with LOCK:
            content=last['playlist'];summary=last['summary'];cfg=last['config']
        if not content:raise ValueError('Hãy tạo playlist ở bước 3 trước.')
        if summary.get('risk') and not payload.get('force_risk'):
            raise ValueError(summary['risk']+' Hãy kiểm tra báo cáo trước khi đăng.')
        result=publish(content,payload.get('expected_account','').strip(),payload.get('gist_id','').strip(),
                       bool(payload.get('keep_legacy',True)),mode=payload.get('mode','update'))
        config=load_config()
        config['gist_id']=result['gist_id'];config['expected_account']=result['account'];config['keep_legacy']=bool(payload.get('keep_legacy',True))
        save_config(config)
        out=Path(summary['file']).parent/'LINK_IPTV_CO_DINH.txt'
        out.write_text(result['raw_url']+'\n',encoding='utf-8')
        update_job(state=('published' if result['raw_verified'] else 'published-warning'),
                   stage=('Link GitHub đã xác minh' if result['raw_verified'] else 'Gist nhận bản cập nhật, Raw chưa xác minh'),progress=100,
                   result={'publish':result,'summary':summary})
    except Exception as exc:
        update_job(state='publish-error',stage='Không thể đăng GitHub',progress=0,message=str(exc)[:1100])


class Handler(BaseHTTPRequestHandler):
    def log_message(self,format,*args):pass
    def _send(self,status,content,typ='application/json; charset=utf-8',extra=None):
        self.send_response(status)
        self.send_header('Content-Type',typ);self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer')
        if extra:
            for k,v in extra.items():self.send_header(k,v)
        self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
    def _json(self,data,status=200):self._send(status,json.dumps(data,ensure_ascii=False).encode('utf-8'))
    def _secure(self):
        return self.headers.get('X-IPTV-Token')==TOKEN and (not self.headers.get('Origin') or
                self.headers.get('Origin')==f'http://127.0.0.1:{self.server.server_port}')
    def do_GET(self):
        route=urllib.parse.urlsplit(self.path).path
        if route=='/':
            html=(WEB_DIR/'index.html').read_text(encoding='utf-8').replace('__APP_TOKEN__',TOKEN)
            return self._send(200,html.encode('utf-8'),'text/html; charset=utf-8',
                              {'Content-Security-Policy':"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; img-src 'self' data:"})
        if route=='/app.js':return self._send(200,(WEB_DIR/'app.js').read_bytes(),'text/javascript; charset=utf-8')
        if route=='/styles.css':return self._send(200,(WEB_DIR/'styles.css').read_bytes(),'text/css; charset=utf-8')
        if route=='/api/config':return self._json({'config':load_config()})
        if route=='/api/job':
            with LOCK:return self._json(dict(job))
        if route=='/api/account':
            try:return self._json({'account':github_user()})
            except Exception as exc:return self._json({'account':None,'error':str(exc)[:400]})
        if route in ('/download/iptv.m3u','/download/report.csv'):
            with LOCK:
                summary=last['summary']
                if not summary:return self._json({'error':'Chưa có file mới.'},400)
                path=Path(summary['file'] if route.endswith('iptv.m3u') else summary['report'])
            filename=OUTPUT_NAME if route.endswith('iptv.m3u') else 'BAO_CAO_KENH_IPTV.csv'
            return self._send(200,path.read_bytes(),'application/octet-stream',
                              {'Content-Disposition':f'attachment; filename="{filename}"'})
        return self._json({'error':'Không tìm thấy.'},404)
    def do_POST(self):
        if not self._secure():return self._json({'error':'Yêu cầu không hợp lệ.'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<0 or length>128000:return self._json({'error':'Yêu cầu quá lớn.'},413)
            payload=json.loads(self.rfile.read(length))
            route=urllib.parse.urlsplit(self.path).path
            if route=='/api/config':
                save_config(payload)
                return self._json({'ok':True})
            if route=='/api/build':
                validate_config(payload)
                with LOCK:
                    if job['state'] in ('working','publishing'):raise ValueError('Đang có tác vụ khác, chưa thể chạy thêm.')
                    job.update(state='working',stage='Đang chuẩn bị…',progress=1,message='',result=None)
                save_config(payload)
                threading.Thread(target=build_task,args=(payload,),daemon=True).start()
                return self._json({'ok':True})
            if route=='/api/publish':
                with LOCK:
                    if job['state'] not in ('done','published','published-warning','publish-error') or last['playlist'] is None:
                        raise ValueError('Cần hoàn thành bước tạo file trước khi đăng.')
                    job.update(state='publishing',stage='Bắt đầu kiểm tra GitHub…',progress=1,message='')
                threading.Thread(target=publish_task,args=(payload,),daemon=True).start()
                return self._json({'ok':True})
            return self._json({'error':'Không tìm thấy.'},404)
        except Exception as exc:return self._json({'error':str(exc)[:1000]},400)


def run():
    WEB_DIR.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    url=f'http://127.0.0.1:{server.server_port}'
    print('\nIPTV STUDIO v5 — GIAO DIEN:',url,'\nChi hoat dong tren may cua ban. Ctrl+C de thoat.\n',flush=True)
    try:webbrowser.open(url)
    except Exception:pass
    try:server.serve_forever(poll_interval=.3)
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':run()
