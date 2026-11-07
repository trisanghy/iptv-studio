"""Explicit GitHub Gist publishing. No auto-create, no cron, no repository mutation."""
import hashlib, json, os, shutil, subprocess, time, urllib.request
from core import OUTPUT_NAME, LEGACY_NAME, CURRENT_GIST_ID


def gh_call(args,payload=None):
    if not shutil.which('gh'):
        raise RuntimeError('Chưa có GitHub CLI (gh). Cài gh rồi chạy gh auth login --scopes gist.')
    env=os.environ.copy()
    for name in ('GH_TOKEN','GITHUB_TOKEN','GH_HOST'):env.pop(name,None)
    # Background schedules must never trigger interactive auth prompts.
    env['GH_PROMPT_DISABLED']='1'
    env['GIT_TERMINAL_PROMPT']='0'
    env['GCM_INTERACTIVE']='Never'
    cmd=['gh','api','--hostname','github.com',*args]
    if payload is not None:cmd+=['--input','-']
    try:
        result=subprocess.run(cmd,input=json.dumps(payload,ensure_ascii=False) if payload is not None else None,
                              encoding='utf-8',capture_output=True,timeout=75,env=env)
    except subprocess.TimeoutExpired:raise RuntimeError('GitHub API hết thời gian phản hồi, hãy kiểm tra Gist trước khi thử lại.')
    if result.returncode:
        raise RuntimeError('GitHub API lỗi: '+(result.stderr or result.stdout)[-450:].strip())
    try:return json.loads(result.stdout)
    except ValueError:raise RuntimeError('GitHub API không trả JSON hợp lệ.')


def github_user():
    user=gh_call(['--method','GET','user'])
    return user.get('login','')


def verify_owned_gist(gist_id,account):
    if not isinstance(gist_id,str) or len(gist_id)!=32 or any(c not in '0123456789abcdefABCDEF' for c in gist_id):
        raise ValueError('Gist ID phải là chuỗi 32 ký tự hex.')
    gist=gh_call(['--method','GET','gists/'+gist_id])
    owner=(gist.get('owner') or {}).get('login','')
    if owner.lower()!=account.lower():
        raise RuntimeError('Gist không thuộc tài khoản GitHub đang đăng nhập. KHÔNG cập nhật.')
    return gist


def check_raw(url,expected,attempts=3):
    errors=[]
    for n in range(attempts):
        try:
            q='?refresh='+str(int(time.time()))+'-'+str(n)
            req=urllib.request.Request(url+q,headers={'Cache-Control':'no-cache','User-Agent':'IPTV-Studio/5.0'})
            with urllib.request.urlopen(req,timeout=15) as resp:
                body=resp.read(4*1024*1024).decode('utf-8-sig')
            if body.replace('\r\n','\n').strip()==expected.replace('\r\n','\n').strip():return True,''
            errors.append('Raw có nội dung chưa khớp với bản vừa tải')
        except Exception as exc:errors.append(type(exc).__name__+': '+str(exc)[:120])
        if n<attempts-1:time.sleep(2)
    return False,errors[-1]


def publish(content,account_expected,gist_id,keep_legacy,mode='update'):
    if not content.startswith('#EXTM3U') or '#EXTINF' not in content:
        raise ValueError('Không đăng nội dung không phải M3U.')
    account=github_user()
    if not account:raise RuntimeError('Terminal chưa có tài khoản GitHub hợp lệ.')
    if account_expected and account.casefold()!=account_expected.casefold():
        raise RuntimeError('Dừng để bảo vệ tài khoản: đang đăng nhập '+account+', nhưng bạn chọn '+account_expected)
    if mode not in ('update','create'):raise ValueError('Chế độ GitHub không hợp lệ.')
    if mode=='update':
        gist=verify_owned_gist(gist_id,account)
        files={OUTPUT_NAME:{'content':content}}
        # Legacy alias keeps users' previously saved Raw URL from breaking.
        if keep_legacy and LEGACY_NAME in (gist.get('files') or {}):
            files[LEGACY_NAME]={'content':content}
        result=gh_call(['--method','PATCH','gists/'+gist_id],{'files':files})
        result_id=result.get('id') or gist_id
    else:
        # Explicit user action only. No fallback to POST on an update failure.
        result=gh_call(['--method','POST','gists'],{'description':'Playlist IPTV cá nhân - cập nhật qua IPTV Studio',
                     'public':False,'files':{OUTPUT_NAME:{'content':content}}})
        result_id=result.get('id')
        if not result_id:raise RuntimeError('Gist được tạo nhưng không trả ID; kiểm tra trang Gist trước khi thử lại.')
    updated=verify_owned_gist(result_id,account)
    entry=(updated.get('files') or {}).get(OUTPUT_NAME)
    if not entry:raise RuntimeError('Gist không chứa file iptv.m3u sau cập nhật.')
    if not entry.get('truncated') and entry.get('content','').replace('\r\n','\n').strip()!=content.replace('\r\n','\n').strip():
        raise RuntimeError('Dữ liệu trên Gist chưa khớp với file xuất.')
    stable=f'https://gist.githubusercontent.com/{account}/{result_id}/raw/{OUTPUT_NAME}'
    ok,why=check_raw(stable,content)
    return {'account':account,'gist_id':result_id,'raw_url':stable,
            'gist_page':f'https://gist.github.com/{account}/{result_id}',
            'raw_verified':ok,'note':('Raw đã kiểm tra và trùng nội dung.' if ok else
            'Gist API đã cập nhật nhưng link Raw chưa xác nhận: '+why),
            'legacy_url':(f'https://gist.githubusercontent.com/{account}/{result_id}/raw/{LEGACY_NAME}'
                           if keep_legacy and mode=='update' and LEGACY_NAME in (updated.get('files') or {}) else '')}
