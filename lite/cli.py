#!/usr/bin/env python3
"""IPTV Studio Lite: no web interface, cron-like native scheduled runs."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import traceback

import lite_worker as worker
import scheduler_lite as scheduler
from core import validate_config,valid_web_url,defaults

RUNTIME_FILES=('cli.py','lite_worker.py','scheduler_lite.py','core.py','advanced_probe.py','github_publish.py')


def install():
    source=Path(__file__).resolve().parent
    dest=scheduler.runtime_dir()
    dest.mkdir(parents=True,exist_ok=True)
    if source!=dest:
        for name in RUNTIME_FILES:shutil.copy2(source/name,dest/name)
    settings=worker.load_settings()
    if not worker.SETTINGS_PATH.exists():worker.save_settings(settings)
    # Windows portable Python must be installed alongside the scheduled worker;
    # otherwise deleting the downloaded ZIP would break the hidden scheduler.
    py_for_schedule=Path(sys.executable).resolve()
    if os.name=='nt' and py_for_schedule.parent.name.lower()=='python' and py_for_schedule.parent.parent.name.lower()=='runtime':
        imported_runtime=dest/'runtime'/'python'
        shutil.copytree(py_for_schedule.parent,imported_runtime,dirs_exist_ok=True)
        py_for_schedule=imported_runtime/'python.exe'
    print('Đã đặt chương trình tại:',dest)
    print('Đang đăng ký lịch:',', '.join(settings['times']))
    result=scheduler.install(dest,py_for_schedule,settings['times'])
    print('THÀNH CÔNG:',result)
    print('Chạy nền: không mở trình duyệt, Terminal hay thông báo khi đến giờ.')
    print('GitHub tự động:', 'BẬT' if settings['auto_publish'] else 'TẮT (an toàn)')
    print('Kiểm tra: python cli.py status | Chạy thử: python cli.py run --no-publish')
    print('Log:',worker.LOG_PATH)


def reconfigure():
    dest=scheduler.runtime_dir()
    if not (dest/'cli.py').exists():raise RuntimeError('Chưa cài. Chạy install trước.')
    times=worker.load_settings()['times']
    py=dest/'runtime'/'python'/'python.exe' if os.name=='nt' and (dest/'runtime'/'python'/'python.exe').exists() else Path(sys.executable).resolve()
    print(scheduler.install(dest,py,times))


def display_status():
    opts=worker.load_settings()
    print('IPTV Studio Lite — không có Web GUI')
    print('Lịch giờ máy:',', '.join(opts['times']))
    print('Tự cập nhật Gist:', 'BẬT' if opts['auto_publish'] else 'TẮT')
    print('Lưu playlist tại:',worker.read_config()[0]['output_dir'])
    print('Bản lịch:',scheduler.runtime_dir())
    print('Log:',worker.LOG_PATH)
    if worker.STATUS_PATH.exists():
        st=json.loads(worker.STATUS_PATH.read_text(encoding='utf-8'))
        print('Lần cuối:',st.get('finish_utc',st.get('start_utc','-')))
        print('Kết quả:',st.get('state'),'; Kênh:',st.get('counts',{}))
        print('Xuất:',st.get('output','-'))
        print('GitHub:',st.get('publish','-'))
        if st.get('risk'):print('CẢNH BÁO:',st['risk'])
        if st.get('error'):print('LỖI:',st['error'])
    else:print('Chưa có lượt chạy.')


def update_setting(action,values):
    opts=worker.load_settings()
    if action=='times':
        opts['times']=values.replace(' ','').split(',')
        worker.save_settings(opts)
        print('Đã lưu lịch:',opts['times'])
        print('CHÚ Ý: chạy reschedule để lịch hệ điều hành nhận giờ mới.')
    elif action=='publish':
        if values not in ('on','off'):raise ValueError('Dùng: publish on hoặc publish off')
        opts['auto_publish']=values=='on'
        worker.save_settings(opts)
        print('Tự cập nhật Gist:', 'BẬT' if opts['auto_publish'] else 'TẮT')
        if opts['auto_publish']:
            print('Sẽ dùng gh CLI đang đăng nhập; chỉ PATCH Gist hiện có, không tạo Gist mới.')
            print('LƯU Ý: đảm bảo quyền phát lại nội dung và tài khoản GitHub hợp lệ.')
    else:raise ValueError('Cài đặt không hợp lệ')


def sources(op,values):
    cfg,opts=worker.read_config()
    src=opts['source_overrides'] if opts['source_overrides'] is not None else cfg['sources']
    src=[dict(s) for s in src]
    if op=='list':
        for i,s in enumerate(src,1):print(f'{i:02d}  {s.get("title")}  [{s.get("role")}]  {s.get("url")}')
        return
    if op=='reset':
        opts['source_overrides']=None
        worker.save_settings(opts)
        print('Đã trở lại nguồn theo cấu hình GUI (hoặc 2 nguồn mặc định).')
        return
    if op=='add':
        if len(values)<2:raise ValueError('Cú pháp: sources add URL "Tên nguồn"')
        url=values[0];title=' '.join(values[1:]).strip()
        if not valid_web_url(url):raise ValueError('URL nguồn không hợp lệ')
        src.append({'id':'lite-'+str(len(src)+1),'title':title,'url':url,'role':'normal','enabled':True})
    elif op=='remove':
        if len(values)!=1 or not values[0].isdigit():raise ValueError('Cú pháp: sources remove SỐ_THỨ_TỰ')
        i=int(values[0])-1
        if not 0<=i<len(src):raise ValueError('Không tìm thấy số thứ tự nguồn.')
        del src[i]
    else:raise ValueError('Lệnh nguồn không hợp lệ.')
    candidate=dict(cfg,sources=src)
    validate_config(candidate)
    opts['source_overrides']=src
    worker.save_settings(opts)
    print('Đã lưu',len(src),'nguồn. Chạy sources list để kiểm tra.')


def main(argv=None):
    p=argparse.ArgumentParser(description='IPTV Studio Lite — tự kiểm tra & gộp M3U, chạy nền không Web GUI')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('install',help='Cài vào thư mục ổn định + đăng ký lịch hệ điều hành')
    sub.add_parser('reschedule',help='Cập nhật lịch sau khi đổi giờ')
    sub.add_parser('remove-schedule',help='Tắt và xóa lịch; không xóa playlist')
    sub.add_parser('status',help='Xem lượt chạy cuối')
    run=sub.add_parser('run',help='Chạy ngay (mặc định theo cấu hình)')
    run.add_argument('--no-publish',action='store_true',help='Chỉ tạo file trên máy, không ghi GitHub')
    run.add_argument('--scheduled',action='store_true',help='Được gọi bởi trình lập lịch; không có hộp thoại')
    sett=sub.add_parser('config',help='Đặt giờ chạy hoặc tùy chọn tự cập nhật GitHub')
    sett.add_argument('key',choices=['times','publish']);sett.add_argument('value')
    src=sub.add_parser('sources',help='Danh sách nguồn cho bản Lite')
    src.add_argument('operation',choices=['list','add','remove','reset']);src.add_argument('values',nargs='*')
    args=p.parse_args(argv)
    if args.command=='install':install()
    elif args.command=='reschedule':reconfigure()
    elif args.command=='remove-schedule':print(scheduler.remove())
    elif args.command=='status':display_status()
    elif args.command=='config':update_setting(args.key,args.value)
    elif args.command=='sources':sources(args.operation,args.values)
    elif args.command=='run':
        result=worker.process_run(no_publish=args.no_publish)
        if not args.scheduled:
            display_status()
            print('Xem chi tiết:',worker.LOG_PATH)
        return result
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:
        # A scheduled pythonw.exe launch has no stdout; always keep an error log.
        log=worker.logger_setup()
        log.exception('IPTV Studio Lite thất bại: %s',e)
        print('LỖI:',str(e),file=sys.stderr)
        sys.exit(1)
