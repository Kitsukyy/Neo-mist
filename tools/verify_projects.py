"""Fixed synthetic CLI workflow across isolated processes of an installed wheel."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
CLI='''
import socket,sys
from unittest.mock import patch
from mist.cli import main
with patch.object(socket,'socket',side_effect=AssertionError('network forbidden')):
    raise SystemExit(main(['--memory-dir',sys.argv[1],'--audit-path',sys.argv[2]]))
'''
READ='''
import json,socket,sys
from unittest.mock import patch
from pathlib import Path
import mist
from mist.bootstrap import create_application
with patch.object(socket,'socket',side_effect=AssertionError('network forbidden')):
    app=create_application(audit_path=Path(sys.argv[2]),memory_dir=Path(sys.argv[1]))
    try:
        print(json.dumps({'version':mist.__version__,'module':mist.__file__,
              'project':app.projects.get('aurora').model_dump(mode='json'),
              'tasks':[t.model_dump(mode='json') for t in app.projects.tasks('aurora')],
              'progress':app.projects.progress('aurora'),
              'tools_enabled':app.settings.tools_enabled,'autonomy':app.settings.autonomy_level}))
    finally:app.close()
'''


def verify():
    with tempfile.TemporaryDirectory(prefix='mist-projects-installed-') as directory:
        root=Path(directory);state=root/'state';audit=root/'audit.jsonl'
        def call(script,commands=None):
            result=subprocess.run([sys.executable,'-I','-c',script,str(state),str(audit)],
                cwd=root,input='\n'.join(commands)+'\n' if commands is not None else None,
                capture_output=True,text=True,timeout=60)
            if result.returncode:raise RuntimeError('Installed project workflow failed')
            return {'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
        first=call(CLI,['/projects create aurora "Projeto Sintético Aurora" "Preparar exemplos fictícios"',
                       '/projects use aurora','/projects add aurora Revisar exemplo fictício',
                       '/projects add aurora Conferir roteiro fictício','/projects progress','/quit'])
        before=call(READ);initial=json.loads(before['stdout'])
        task_id=initial['tasks'][0]['id']
        second=call(CLI,[f'/projects task aurora {task_id} concluida',
                        f'/projects due aurora {task_id} 2026-10-20',
                        '/projects archive aurora','/projects reopen aurora','/projects use aurora',
                        '/projects tasks','/projects progress','/quit'])
        after=call(READ);final=json.loads(after['stdout'])
        checks={'installed_distribution': 'site-packages' in Path(final['module']).parts,
                'version':final['version']=='0.5.0',
                'same_project':initial['project']['key']==final['project']['key']=='aurora',
                'same_task_ids':[t['id'] for t in initial['tasks']]==[t['id'] for t in final['tasks']],
                'state_and_due_persisted':final['tasks'][0]['state']=='done' and final['tasks'][0]['due_date']=='2026-10-20',
                'reopened_project':final['project']['state']=='active',
                'progress':final['progress']['percent']==50.0,
                'local_records':all(t['sensitivity']=='local_only' for t in final['tasks']),
                'user_sources':all(t['updated_by']['origin']=='user' for t in final['tasks']),
                'permissions':final['tools_enabled'] is False and final['autonomy']==0,
                'no_generation_audit':not audit.exists(),
                'private_catalog':(state/'projects.sqlite3').stat().st_mode & 0o777==0o600}
        return {'verified_at':datetime.now(timezone.utc).isoformat(),
                'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src/mist').glob('*.py'))},
                'method':'four new isolated Python processes outside checkout; socket creation blocked; fixed fictitious data',
                'cli_sessions':[first,second],'initial':initial,'final':final,'checks':checks,'passed':all(checks.values())}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();evidence=verify()
    with args.output.open('x') as stream:
        json.dump(evidence,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({'version':evidence['final']['version'],'passed':evidence['passed']}))
    return 0 if evidence['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
