"""Headless IPTV 5.1 runner: same IPTV Studio v5 core, no HTTP listener or UI."""
from __future__ import annotations
import copy
import datetime as dt
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

from core import (defaults,validate_config,download_text,merge_playlist,check_channels,
                  save_files,count_status,publication_risk,vn_check_time,OUTPUT_NAME)
from github_publish import publish

APP_HOME=Path.home()/'.iptv_studio'
SETTINGS_PATH=APP_HOME/'lite_settings.json'
GUI_CONFIG_PATH=APP_HOME/'config.json'
RUN_HOME=APP_HOME/'lite'
STATUS_PATH=RUN_HOME/'last_run.json'
LOG_PATH=RUN_HOME/'run.log'
LOCK_PATH=RUN_HOME/'run.lock'


def settings_defaults():
    return {'times':['07:00','19:00'], 'auto_publish':False,
            'protect_on_warning':True, 'source_overrides':None}


def load_settings():
    settings=settings_defaults()
    if SETTINGS_PATH.exists():
        content=json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))
        if not isinstance(content,dict):raise ValueError('lite_settings.json phải là đối tượng JSON.')
        settings.update(content)
    validate_settings(settings)
    return settings


def validate_settings(settings):
    times=settings.get('times')
    if not isinstance(times,list) or not 1<=len(times)<=8 or len(set(times))!=len(times):
        raise ValueError('Lịch cần từ 1 đến 8 mốc giờ khác nhau.')
    for s in times:
        if not isinstance(s,str) or len(s)!=5 or s[2]!=':' or not s.replace(':','').isdigit():
            raise ValueError('Giờ phải dạng HH:MM (ví dụ 07:00).')
        h,m=map(int,s.split(':'))
        if not 0<=h<=23 or not 0<=m<=59:raise ValueError('Giờ không hợp lệ: '+s)
    if not isinstance(settings.get('auto_publish'),bool):raise ValueError('auto_publish phải là true/false')
    if not isinstance(settings.get('protect_on_warning'),bool):raise ValueError('protect_on_warning phải là true/false')
    override=settings.get('source_overrides')
    if override is not None and (not isinstance(override,list) or not 1<=len(override)<=25):
        raise ValueError('source_overrides phải là danh sách 1–25 nguồn hoặc null.')


def save_settings(settings):
    validate_settings(settings)
    APP_HOME.mkdir(parents=True,exist_ok=True)
    temp=SETTINGS_PATH.with_suffix('.tmp')
    temp.write_text(json.dumps(settings,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(temp,SETTINGS_PATH)


def read_config():
    cfg=defaults()
    if GUI_CONFIG_PATH.exists():
        saved=json.loads(GUI_CONFIG_PATH.read_text(encoding='utf-8'))
        if not isinstance(saved,dict):raise ValueError('config.json của bản GUI không hợp lệ.')
        cfg.update(saved)
    opts=load_settings()
    if opts['source_overrides'] is not None:cfg['sources']=copy.deepcopy(opts['source_overrides'])
    validate_config(cfg)
    return cfg,opts


def logger_setup():
    RUN_HOME.mkdir(parents=True,exist_ok=True)
    logger=logging.getLogger('IPTVStudioLite')
    for previous in logger.handlers[:]:
        logger.removeHandler(previous)
        previous.close()
    logger.setLevel(logging.INFO)
    handler=RotatingFileHandler(LOG_PATH,maxBytes=1_500_000,backupCount=3,encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    return logger


class ProcessLock:
    """Advisory process lock; released automatically if Python terminates."""
    def __init__(self):self.file=None
    def __enter__(self):
        RUN_HOME.mkdir(parents=True,exist_ok=True)
        self.file=open(LOCK_PATH,'a+b')
        try:
            if os.name=='nt':
                import msvcrt
                if self.file.seek(0,2)==0:self.file.write(b'0');self.file.flush()
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except (BlockingIOError,OSError):
            self.file.close();self.file=None
            return False
        return True
    def __exit__(self,*args):
        if self.file:
            try:
                if os.name=='nt':
                    import msvcrt
                    self.file.seek(0);msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(self.file.fileno(),fcntl.LOCK_UN)
            finally:self.file.close()


def save_status(data):
    RUN_HOME.mkdir(parents=True,exist_ok=True)
    temp=STATUS_PATH.with_suffix('.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(temp,STATUS_PATH)


def download_retry(source,logger,attempts=2):
    for attempt in range(1,attempts+1):
        try:
            logger.info('Tải nguồn %s (%s) - lần %s/%s',source['title'],source['url'],attempt,attempts)
            return download_text(source['url'],timeout=25)
        except Exception as e:
            if attempt==attempts:raise RuntimeError('Nguồn '+source['title']+' lỗi: '+str(e)[:200]) from e
            time.sleep(2)


def atomic_copy(src,dst):
    src,dst=Path(src),Path(dst)
    dst.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dst.parent,delete=False) as out:
        temp=Path(out.name)
    try:
        shutil.copyfile(src,temp)
        os.replace(temp,dst)
    finally:
        temp.unlink(missing_ok=True)


def process_run(no_publish=False):
    log=logger_setup()
    with ProcessLock() as has_lock:
        if not has_lock:
            log.info('Một lần kiểm tra khác đang chạy, bỏ qua lịch trùng.')
            return 0
        start=dt.datetime.now(dt.timezone.utc).isoformat()
        status={'state':'running','start_utc':start,'file':'iptv.m3u','publish':'not_requested'}
        save_status(status)
        try:
            cfg,opts=read_config()
            selected=[s for s in cfg['sources'] if s.get('enabled',True)]
            pairs=[(s,download_retry(s,log)) for s in selected]
            channels,epgs,groups,total=merge_playlist(pairs)
            if total>20000:raise ValueError('Quá 20.000 kênh, không kiểm tra để bảo vệ tài nguyên máy.')
            checked=bool(cfg.get('check_streams',True))
            if checked:
                log.info('Bắt đầu kiểm tra %s kênh × %s vòng, %s luồng',len(channels),cfg['rounds'],cfg['workers'])
                last_progress=[0]
                def progress(done,count):
                    if done==count or done-last_progress[0]>=50:
                        log.info('Đã kiểm tra %s/%s URL',done,count)
                        last_progress[0]=done
                check_channels(channels,workers=int(cfg['workers']),timeout=float(cfg['timeout']),
                               retries=int(cfg['retries']),rounds=int(cfg['rounds']),
                               strict_unknown=bool(cfg.get('strict_unknown',False)),
                               ffprobe_enabled=bool(cfg.get('ffprobe_enabled',False)),progress=progress)
            else:log.warning('Chế độ kiểm tra link đã tắt trong cấu hình GUI.')
            flags=count_status(channels)
            issue=publication_risk(channels) if checked else 'Chưa kiểm tra kênh: từ chối đăng Gist tự động.'
            dest=Path(cfg['output_dir']).expanduser()
            dest.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.iptv-staging-',dir=dest) as td:
                content,staged_file,staged_report=save_files(channels,epgs,td,
                                                             checked_at=vn_check_time(),was_checked=checked)
                blocked=bool(issue and opts['protect_on_warning'])
                filename='iptv_can_kiem_tra.m3u' if blocked else OUTPUT_NAME
                atomic_copy(staged_file,dest/filename)
                atomic_copy(staged_report,dest/'BAO_CAO_KENH_IPTV.csv')
                atomic_copy(Path(td)/'iptv_goc_chua_loc.m3u',dest/'iptv_goc_chua_loc.m3u')
            log.info('Xong %s kênh: %s; file: %s',total,flags,dest/filename)
            status.update(state='warning' if blocked else 'success',finish_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                          total=total,counts=flags,output=str(dest/filename),
                          risk=issue or '',checked_at=vn_check_time(),sources=len(pairs))
            if blocked:log.warning('Cảnh báo - không ghi đè iptv.m3u và Gist: %s',issue)
            if opts['auto_publish'] and not no_publish and not blocked and checked:
                try:
                    published=publish(content,cfg.get('expected_account','trisanghy'),cfg.get('gist_id',''),
                                      bool(cfg.get('keep_legacy',True)),mode='update')
                    status['publish']='verified' if published.get('raw_verified') else 'raw_unverified'
                    status['raw_url']=published['raw_url']
                    status['note']=published['note']
                    if not published.get('raw_verified'):
                        log.warning('Gist đã cập nhật nhưng link Raw chưa xác minh: %s',published['note'])
                        status['state']='warning'
                    else:log.info('Gist Raw đã xác minh: %s',published['raw_url'])
                    (dest/'LINK_IPTV_CO_DINH.txt').write_text(published['raw_url']+'\n',encoding='utf-8')
                except Exception as exc:
                    status.update(state='warning',publish='failed',publish_error=str(exc)[:300])
                    log.error('Không cập nhật được Gist: %s',exc)
            elif opts['auto_publish'] and no_publish:status['publish']='disabled_for_this_run'
            elif opts['auto_publish'] and blocked:status['publish']='blocked_by_safety'
            else:status['publish']='off'
            save_status(status)
            return 0 if status['state']=='success' else 2
        except Exception as e:
            log.exception('Lượt kiểm tra thất bại, giữ file và Gist cũ: %s',e)
            status.update(state='error',finish_utc=dt.datetime.now(dt.timezone.utc).isoformat(),error=str(e)[:500])
            save_status(status)
            return 1
