"""OS-native background schedules. No GUI, browser or persistent Python daemon."""
from __future__ import annotations
import os
from pathlib import Path
import platform
import plistlib
import subprocess
import sys
import textwrap
import xml.sax.saxutils as sax

LABEL='vn.iptv.studio.lite'
TASK_PREFIX='IPTVStudioLite_'


def runtime_dir():
    if os.name=='nt':
        return Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData'/'Local'))/'IPTVStudioLite'
    return Path.home()/'.local'/'share'/'iptv-studio-lite'


def _run(cmd,allow_error=False):
    p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35)
    if p.returncode and not allow_error:
        raise RuntimeError('Lệnh lên lịch không thành công: '+str(cmd[0])+': '+(p.stderr or p.stdout)[-350:])
    return p


def mac_plist(runtime,py,times):
    home=Path.home()
    logs=home/'.iptv_studio'/'lite'
    return {'Label':LABEL,
            'ProgramArguments':[str(py),str(runtime/'cli.py'),'run','--scheduled'],
            'WorkingDirectory':str(runtime),'ProcessType':'Background',
            'StartCalendarInterval':[{'Hour':int(t[:2]),'Minute':int(t[3:])} for t in times],
            'StandardOutPath':str(logs/'scheduler.stdout.log'),
            'StandardErrorPath':str(logs/'scheduler.stderr.log'),
            'EnvironmentVariables':{'PATH':'/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'},
            'RunAtLoad':False}


def linux_units(runtime,py,times):
    def q(s):
        return '"' + str(s).replace('\\','\\\\').replace('\"','\\\"') + '"'
    service=textwrap.dedent(f'''\
        [Unit]
        Description=IPTV Studio Lite - headless playlist check
        [Service]
        Type=oneshot
        WorkingDirectory={q(runtime)}
        ExecStart={q(py)} {q(runtime/'cli.py')} run --scheduled
        TimeoutStartSec=3h
    ''')
    timer='[Unit]\nDescription=IPTV Studio Lite - background schedule\n[Timer]\n'
    timer+=''.join(f'OnCalendar=*-*-* {t}:00\n' for t in times)
    timer+='Persistent=true\nAccuracySec=1min\nUnit='+LABEL+'.service\n[Install]\nWantedBy=timers.target\n'
    return service,timer


def powershell_windows_install(runtime,pyw,times):
    # COM Task Scheduler v2: task is hidden, executes pythonw (windowless).
    # InteractiveToken: only while current user is logged on; no password stored.
    # Use a quoted literal here-string for path safety; block literal quote injection.
    for val in (runtime,pyw):
        if "'" in str(val):raise RuntimeError('Windows user path contains a single quote; cannot safely generate PowerShell.')
    script=str(runtime/'cli.py')
    lines=[]
    lines.append('$ErrorActionPreference = "Stop"')
    lines.append('$service = New-Object -ComObject "Schedule.Service"')
    lines.append('$service.Connect()')
    lines.append('$folder = $service.GetFolder("\\")')
    lines.append('$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name')
    lines.append(f'$prefix = "{TASK_PREFIX}"')
    lines.append('foreach ($i in 1..8) { try { $folder.DeleteTask($prefix + $i,0) } catch {} }')
    lines.append('''$times = @('''+','.join("'"+t+"'" for t in times)+''')''')
    lines.append('$n = 1')
    lines.append('foreach ($t in $times) {')
    lines.append('  $task = $service.NewTask(0)')
    lines.append('  $task.RegistrationInfo.Description = "IPTV Studio Lite schedule (background, no GUI)"')
    lines.append('  $task.Settings.Enabled = $true')
    lines.append('  $task.Settings.Hidden = $true')
    lines.append('  $task.Settings.StartWhenAvailable = $true')
    lines.append('  $task.Settings.MultipleInstances = 2') # TASK_INSTANCES_IGNORE_NEW
    lines.append('  $task.Settings.ExecutionTimeLimit = "PT3H"')
    lines.append('  $task.Principal.UserId = $identity')
    lines.append('  $task.Principal.LogonType = 3') # interactive
    lines.append('  $task.Principal.RunLevel = 0') # least privileges
    lines.append('  $trigger = $task.Triggers.Create(2)') # daily
    lines.append('  $trigger.DaysInterval = 1')
    lines.append('  $trigger.StartBoundary = (Get-Date -Format "yyyy-MM-dd") + "T" + $t + ":00"')
    lines.append('  $action = $task.Actions.Create(0)')
    lines.append(f"  $action.Path = '{pyw}'")
    lines.append(f"  $action.Arguments = '\"{script}\" run --scheduled'")
    lines.append(f"  $action.WorkingDirectory = '{runtime}'")
    lines.append('  $null = $folder.RegisterTaskDefinition($prefix + $n,$task,6,$null,$null,3,$null)')
    lines.append('  $n++')
    lines.append('}')
    lines.append('Write-Output "Đã cài lịch IPTV Studio Lite chạy ẩn: $($times -join ", ")"')
    return '\n'.join(lines)+'\n'


def powershell_windows_remove():
    return ('$ErrorActionPreference="Stop"\n'
            '$service=New-Object -ComObject "Schedule.Service"\n'
            '$service.Connect()\n$folder=$service.GetFolder("\\")\n'
            f'foreach ($i in 1..8) {{ try {{ $folder.DeleteTask("{TASK_PREFIX}"+$i,0) }} catch {{ }} }}\n')


def _ps(script):
    dest=runtime_dir()/'schedule.ps1'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(script,encoding='utf-8-sig')
    try:return _run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(dest)])
    finally:dest.unlink(missing_ok=True)


def install(runtime,py,times):
    run_home=Path.home()/'.iptv_studio'/'lite';run_home.mkdir(parents=True,exist_ok=True)
    osname=platform.system()
    if osname=='Darwin':
        pl=Path.home()/'Library'/'LaunchAgents'/f'{LABEL}.plist'
        pl.parent.mkdir(parents=True,exist_ok=True)
        pl.write_bytes(plistlib.dumps(mac_plist(runtime,py,times)))
        target=f'gui/{os.getuid()}'
        _run(['launchctl','bootout',target,str(pl)],True)
        _run(['launchctl','bootstrap',target,str(pl)])
        _run(['launchctl','enable',target+'/'+LABEL],True)
        return 'macOS launchd: '+str(pl)
    if osname=='Windows':
        pyw=Path(py).with_name('pythonw.exe')
        if not pyw.exists():raise RuntimeError('Thiếu pythonw.exe: cài Python chuẩn từ python.org.')
        _ps(powershell_windows_install(runtime,pyw,times))
        return 'Windows Task Scheduler (Hidden + pythonw.exe), '+', '.join(times)
    if osname=='Linux':
        userdir=Path.home()/'.config'/'systemd'/'user'
        userdir.mkdir(parents=True,exist_ok=True)
        service,timer=linux_units(runtime,py,times)
        (userdir/f'{LABEL}.service').write_text(service,encoding='utf-8')
        (userdir/f'{LABEL}.timer').write_text(timer,encoding='utf-8')
        _run(['systemctl','--user','daemon-reload'])
        _run(['systemctl','--user','enable','--now',LABEL+'.timer'])
        return 'Linux systemd --user: '+', '.join(times)
    raise RuntimeError('Chỉ hỗ trợ lập lịch trên Mac, Windows và Linux.')


def remove():
    osname=platform.system()
    if osname=='Darwin':
        pl=Path.home()/'Library'/'LaunchAgents'/f'{LABEL}.plist'
        _run(['launchctl','bootout',f'gui/{os.getuid()}',str(pl)],True)
        pl.unlink(missing_ok=True)
        return 'Đã ngừng lịch launchd.'
    if osname=='Windows':
        _ps(powershell_windows_remove())
        return 'Đã xóa lịch ẩn trên Task Scheduler.'
    if osname=='Linux':
        _run(['systemctl','--user','disable','--now',LABEL+'.timer'],True)
        for ext in ('.timer','.service'):
            (Path.home()/'.config'/'systemd'/'user'/(LABEL+ext)).unlink(missing_ok=True)
        _run(['systemctl','--user','daemon-reload'],True)
        return 'Đã dừng và xóa lịch systemd.'
    raise RuntimeError('Hệ điều hành chưa hỗ trợ.')
