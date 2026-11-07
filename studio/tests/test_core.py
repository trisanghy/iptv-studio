import os, sys, tempfile, unittest, threading, hashlib
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import *
from advanced_probe import probe_round,aggregate,Probe,looks_media,normalize_url

TS=b''.join(bytes([0x47])+bytes([i%256])*187 for i in range(220))
MP4=b'\x00\x00\x00\x18ftypiso5'+b'\0'*4096

class Fixtures(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        path=self.path.split('?')[0]
        fixtures={
            '/valid.m3u8':(200,'application/vnd.apple.mpegurl',b'#EXTM3U\n#EXT-X-TARGETDURATION:8\n#EXT-X-MEDIA-SEQUENCE:5\n#EXTINF:8,\nsegment.ts\n'),
            '/master.m3u8':(200,'application/vnd.apple.mpegurl',b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=10000\nbroken.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=500000\nvalid.m3u8\n'),
            '/broken.m3u8':(200,'application/vnd.apple.mpegurl',b'#EXTM3U\n#EXT-X-TARGETDURATION:8\n#EXTINF:8,\nmissing\n'),
            '/empty.m3u8':(200,'application/vnd.apple.mpegurl',b'#EXTM3U\n#EXT-X-TARGETDURATION:8\n'),
            '/auth.m3u8':(200,'application/vnd.apple.mpegurl',b'#EXTM3U\n#EXT-X-TARGETDURATION:8\n#EXTINF:8,\nforbidden\n'),
            '/segment.ts':(200,'video/mp2t',TS),
            '/mp4':(200,'video/mp4',MP4),
            '/html':(200,'text/html',b'<html><title>Login</title></html>'),
            '/fake.m3u8':(200,'text/html',b'<html>temporarily unavailable</html>'),
            '/missing':(404,'text/plain',b'Not Found'),
            '/forbidden':(403,'text/plain',b'Forbidden'),
            '/list.m3u':(200,'text/plain',b'#EXTM3U\n#EXTINF:-1 group-title="TV",Test\nhttp://example.org/stream\n'),
        }
        status,ct,body=fixtures.get(path,(404,'text/plain',b'Not Found'))
        self.send_response(status)
        self.send_header('Content-Type',ct)
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        try:self.wfile.write(body)
        except BrokenPipeError:pass

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Fixtures)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def test_http_deep_manifest_and_media(self):
        for path,status in [('/valid.m3u8','OK'),('/master.m3u8','OK'),('/broken.m3u8','FAIL'),
                            ('/empty.m3u8','FAIL'),('/html','FAIL'),('/fake.m3u8','FAIL'),
                            ('/missing','FAIL'),('/forbidden','UNKNOWN'),('/auth.m3u8','UNKNOWN'),('/mp4','OK')]:
            self.assertEqual(probe_url(self.base+path,{'User-Agent':UA},timeout=3)[0],status,path)
        self.assertIn('segment',probe_url(self.base+'/valid.m3u8',{},3)[1])
    def test_multi_rounds_and_groups(self):
        s1={'title':'Nguồn 1','role':'primary1'}
        s3={'title':'Nguồn 3','role':'primary3'}
        s4={'title':'Nguồn thêm','role':'normal'}
        one=f'''#EXTM3U url-tvg="https://example.org/epg.xml"
#EXTINF:-1 tvg-id="vtv1hd" tvg-logo="a" group-title="VTV",VTV1
{self.base}/valid.m3u8
#EXTINF:-1 group-title="LIVE EVENTS",LIVE EVENTS special
{self.base}/missing
#EXTINF:-1 group-title="TV địa phương",THVL1
{self.base}/forbidden
'''
        three=f'''#EXTM3U
#EXTINF:-1 group-title="VTV",VTV3
{self.base}/master.m3u8
#EXTINF:-1 group-title="Movies",Phim HD
/ https://example.com/stream
'''
        four=f'''#EXTM3U
#EXTINF:-1 group-title="VTV",VTV2
{self.base}/valid.m3u8
#EXTINF:-1 group-title="Thể thao",Trận chung kết
{self.base}/html
'''
        entries,epgs,groups,total=merge_playlist([(s1,one),(s3,three),(s4,four)])
        self.assertEqual(total,7)
        self.assertEqual(entries[0].group,VTV_1)
        self.assertEqual(entries[1].group,VTV_3)
        self.assertEqual(entries[2].group,LIVE_GROUP)
        check_channels(entries,workers=4,timeout=3,retries=1,rounds=3)
        self.assertEqual(count_status(entries)['FAIL'],3)
        self.assertEqual(count_status(entries)['OK'],3)
        self.assertEqual(count_status(entries)['UNKNOWN'],1)
        self.assertEqual(len(entries[0].checks),3)
        with tempfile.TemporaryDirectory() as td:
            text,out,report=save_files(entries,epgs,td,checked_at='07/11/2026 20:53')
            self.assertEqual(Path(out).name,'iptv.m3u')
            self.assertEqual(text.count('#EXTINF'),7)
            self.assertEqual(text.count('group-title="99 - KÊNH LỖI"'),3)
            self.assertIn('group-title="03 - LIVE EVENTS 🔴 | Kiểm tra: 07/11/2026 20:53"',text) if any(ch.group.startswith(LIVE_GROUP) for ch in entries) else None
            self.assertEqual(text.find('group-title="99 - KÊNH LỖI"')>text.find('VTV - Nguồn thêm'),True)
            self.assertIn('VTV1',text);self.assertIn('VTV2',text);self.assertIn('VTV3',text)
            self.assertTrue(Path(report).exists());self.assertIn('Vòng kiểm tra',Path(report).read_text(encoding='utf-8-sig'))
    def test_live_timestamp_after_group3(self):
        s={'title':'Test','role':'primary1'}
        text=f'''#EXTM3U
#EXTINF:-1 group-title="VTV",VTV1
{self.base}/valid.m3u8
#EXTINF:-1 group-title="Live Events",Live Sport
{self.base}/valid.m3u8
#EXTINF:-1 group-title="Other",Other TV
{self.base}/valid.m3u8
'''
        channels,epgs,_,_=merge_playlist([(s,text)])
        check_channels(channels,rounds=2,timeout=3,retries=1)
        with tempfile.TemporaryDirectory() as td:
            result,_,_=save_files(channels,epgs,td,checked_at='07/11/2026 20:53')
            p1=result.index('group-title="01 - VTV NGUỒN 1"')
            p3=result.index('group-title="03 - LIVE EVENTS 🔴 | Kiểm tra: 07/11/2026 20:53"')
            p4=result.index('group-title="Other"')
            self.assertTrue(p1<p3<p4)
            self.assertEqual(result.count('#EXTINF'),3)
        channels,epgs,_,_=merge_playlist([(s,text)])
        with tempfile.TemporaryDirectory() as td:
            result,_,_=save_files(channels,epgs,td,was_checked=False)
            self.assertIn(LIVE_GROUP+' | CHƯA KIỂM TRA',result)
    def test_aggregate_conservative(self):
        ok=Probe('OK','HLS manifest+media','manifest+segment')
        fail=Probe('FAIL','HTTP 404')
        u=Probe('UNKNOWN','HTTP 403')
        self.assertEqual(aggregate([ok,ok,fail])[0],'OK')
        self.assertEqual(aggregate([fail,fail,fail])[0],'FAIL')
        self.assertEqual(aggregate([fail,fail,u])[0],'UNKNOWN')
        self.assertEqual(aggregate([fail,fail,u],strict_unknown=True)[0],'FAIL')
        self.assertEqual(aggregate([ok,fail,fail])[0],'UNKNOWN')
        self.assertEqual(aggregate([u,u,u])[0],'UNKNOWN')
    def test_input_validation(self):
        self.assertEqual(probe_url('/ https://a.tv/stream',{},3)[0],'FAIL')
        self.assertEqual(probe_url('https://a.tv/ stream',{},3)[0],'FAIL')
        self.assertEqual(normalize_url(self.base+'/valid.m3u8|User-Agent=hello&Referer=https%3A%2F%2Fa.io',{}),self.base+'/valid.m3u8')
        c=defaults();validate_config(c)
        c['rounds']=7
        with self.assertRaises(ValueError):validate_config(c)
        c['rounds']=3
        c['sources'].append({'id':'x','title':'new','url':'https://example.com/x.m3u','role':'primary1','enabled':True})
        with self.assertRaises(ValueError):validate_config(c)
    def test_http_fetch_source(self):self.assertIn('#EXTINF',download_text(self.base+'/list.m3u'))

class GistTests(unittest.TestCase):
    def test_update_existing_only(self):
        from unittest.mock import patch
        from github_publish import publish, OUTPUT_NAME, LEGACY_NAME
        gid='a'*32; actions=[]
        state={'owner':{'login':'trisanghy'},'files':{LEGACY_NAME:{'content':'old'}}}
        def fake_call(args,payload=None):
            if args[-1]=='user':return {'login':'trisanghy'}
            if args[-1]=='gists/'+gid and 'GET' in args:return state
            if args[-1]=='gists/'+gid and 'PATCH' in args:
                actions.append('PATCH');state['files'].update(payload['files']);return {'id':gid}
            raise AssertionError('Unexpected '+str(args))
        with patch('github_publish.gh_call',side_effect=fake_call),patch('github_publish.check_raw',return_value=(True,'')):
            out=publish('#EXTM3U\n#EXTINF:-1,OK\nhttp://a\n','trisanghy',gid,True)
        self.assertEqual(actions,['PATCH']);self.assertTrue(out['raw_verified'])
        self.assertIn(OUTPUT_NAME,state['files']);self.assertIn(LEGACY_NAME,state['files'])

if __name__=='__main__':unittest.main()
