import tempfile,unittest,sys,json,threading,os
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import lite_worker as w
import scheduler_lite as sc
from core import defaults

SEG=(b'G'+b'\0'*187)*15
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def do_GET(self):
        u=self.path.split('?',1)[0]
        if u=='/input.m3u':
            rows=['#EXTM3U']
            for i in range(5):
                group='Live Events' if i==0 else 'VTV' if i==1 else 'TV khác'
                name='VTV1' if i==1 else 'Test'+str(i)
                rows.extend([f'#EXTINF:-1 group-title="{group}",{name}',f'http://127.0.0.1:{self.server.server_port}/valid.m3u8'])
            rows.extend(['#EXTINF:-1 group-title="Khác",Kênh hỏng',f'http://127.0.0.1:{self.server.server_port}/404'])
            body=('\n'.join(rows)+'\n').encode('utf8');typ='application/x-mpegURL';code=200
        elif u=='/valid.m3u8':
            body=b'#EXTM3U\n#EXT-X-TARGETDURATION:8\n#EXTINF:8,\nsegment.ts\n';typ='application/vnd.apple.mpegurl';code=200
        elif u=='/segment.ts':body=SEG;typ='video/mp2t';code=200
        else:body=b'Not Found';typ='text/plain';code=404
        self.send_response(code);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)

class LiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()

    def test_schedule_generators(self):
        d=Path('/opt/iptv-lite');py=Path('/usr/local/bin/python3')
        plist=sc.mac_plist(d,py,['07:00','19:00'])
        self.assertFalse(plist['RunAtLoad'])
        self.assertEqual(plist['StartCalendarInterval'],[{'Hour':7,'Minute':0},{'Hour':19,'Minute':0}])
        service,timer=sc.linux_units(d,py,['07:00','19:00'])
        self.assertIn('OnCalendar=*-*-* 19:00:00',timer)
        self.assertIn('Persistent=true',timer)
        script=sc.powershell_windows_install(Path('C:/Users/Test/AppData/Local/IPTVStudioLite'),Path('C:/Python/pythonw.exe'),['07:00','19:00'])
        self.assertIn('Hidden = $true',script)
        self.assertIn('pythonw.exe',script)
        self.assertIn('RegisterTaskDefinition',script)

    def test_validation(self):
        opt=w.settings_defaults()
        w.validate_settings(opt)
        opt['times']=['25:22']
        with self.assertRaises(ValueError):w.validate_settings(opt)

    def test_headless_worker_safely_exports(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            patchers=[patch.object(w,'APP_HOME',td/'cfg'),patch.object(w,'SETTINGS_PATH',td/'cfg'/'lite_settings.json'),
                      patch.object(w,'GUI_CONFIG_PATH',td/'cfg'/'config.json'),patch.object(w,'RUN_HOME',td/'run'),
                      patch.object(w,'STATUS_PATH',td/'run'/'last_run.json'),patch.object(w,'LOG_PATH',td/'run'/'run.log'),
                      patch.object(w,'LOCK_PATH',td/'run'/'lock')]
            for obj in patchers:obj.start()
            try:
                (td/'cfg').mkdir()
                cfg=defaults()
                cfg.update(sources=[{'id':'primary','title':'Nguồn 1','url':f'http://127.0.0.1:{self.server.server_port}/input.m3u','role':'primary1','enabled':True}],
                           output_dir=str(td/'out'),workers=3,rounds=2,retries=1,timeout=3)
                w.GUI_CONFIG_PATH.write_text(json.dumps(cfg),encoding='utf8')
                self.assertEqual(w.process_run(no_publish=True),0)
                body=(td/'out'/'iptv.m3u').read_text(encoding='utf8')
                self.assertEqual(body.count('#EXTINF'),6)
                self.assertIn('99 - KÊNH LỖI',body)
                self.assertIn('03 - LIVE EVENTS 🔴 | Kiểm tra:',body)
                st=json.loads(w.STATUS_PATH.read_text(encoding='utf8'))
                self.assertEqual(st['counts']['OK'],5)
                self.assertEqual(st['counts']['FAIL'],1)
                self.assertEqual(st['publish'],'off')
                self.assertEqual(st['state'],'success')
                self.assertTrue((td/'out'/'BAO_CAO_KENH_IPTV.csv').exists())
                # A missing source must NOT overwrite existing output.
                cfg['sources'][0]['url']=f'http://127.0.0.1:{self.server.server_port}/404'
                w.GUI_CONFIG_PATH.write_text(json.dumps(cfg),encoding='utf8')
                self.assertEqual(w.process_run(no_publish=True),1)
                self.assertEqual((td/'out'/'iptv.m3u').read_text(encoding='utf8'),body)
            finally:
                for p in reversed(patchers):p.stop()

if __name__=='__main__':unittest.main()
