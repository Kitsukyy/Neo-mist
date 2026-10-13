"""Exercise the installed mist-ui command across two local HTTP sessions."""
import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


class InstalledUI:
    def __init__(self, root):
        env = os.environ.copy()
        env.pop('PYTHONPATH', None)
        env.pop('NVIDIA_API_KEY', None)
        self.process = subprocess.Popen([str(Path(sys.executable).with_name('mist-ui')),
            '--memory-dir', str(root/'state'), '--audit-path', str(root/'audit.jsonl')],
            cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        line = self.process.stdout.readline()
        match = re.search(r'http://127\.0\.0\.1:(\d+)', line)
        if not match:
            self.close()
            raise AssertionError('Installed local UI did not start')
        self.port = int(match[1])
        self.origin = f'http://127.0.0.1:{self.port}'
        status, self.headers, body = self.request('GET', '/')
        assert status == 200
        self.token = re.search(rb'name="mist-token" content="([^"]+)"', body).group(1).decode('ascii')
        self.state = self.read()

    def request(self, method, path, data=None, auth=False, extra=None):
        headers = dict(extra or {})
        if auth:
            headers.update({'X-Mist-Token': self.token, 'Origin': self.origin})
        if data is not None:
            headers['Content-Type'] = 'application/json'
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        try:
            connection.request(method, path, json.dumps(data, ensure_ascii=False).encode('utf-8') if data is not None else None, headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def read(self):
        status, _, body = self.request('GET', '/api/state', auth=True)
        assert status == 200
        return json.loads(body)

    def command(self, op, **args):
        status, _, body = self.request('POST', '/api/command', {'op': op, 'revision': self.state['revision'], **args}, auth=True)
        assert status == 200, (op, status)
        self.state = json.loads(body)['state']
        return self.state

    def close(self):
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
        self.output, self.errors = self.process.communicate(timeout=10)
        assert self.process.returncode == 0 and not self.errors


def verify():
    inspect = subprocess.run([sys.executable, '-I', '-c', '''
import hashlib, json, platform
from importlib.resources import files
from pathlib import Path
import mist
print(json.dumps({'version':mist.__version__,'python':platform.python_version(),
 'module_path':str(Path(mist.__file__).resolve()),
 'asset_sha256':{name:hashlib.sha256(files('mist').joinpath('web',name).read_bytes()).hexdigest()
                 for name in ('index.html','style.css','app.js')}}))
'''], cwd='/tmp', check=True, capture_output=True, text=True)
    package = json.loads(inspect.stdout)
    assert 'site-packages' in Path(package['module_path']).parts
    evidence = {'verified_at': datetime.now(timezone.utc).isoformat(), 'package': package,
                'source_revision': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
                'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'fixtures': 'Fixed fictitious Aurora project, tasks and preference; no credentials or personal data',
                'checks': {}}
    checks = evidence['checks']
    with tempfile.TemporaryDirectory(prefix='mist-ui-installed-') as directory:
        root = Path(directory)
        ui = InstalledUI(root)
        try:
            assert ui.state['version'] == package['version'] and ui.state['external'] is False
            assert ui.request('GET', '/api/state')[0] == 403
            assert ui.request('GET', '/', extra={'Host': f'evil.test:{ui.port}'})[0] == 403
            checks['loopback_authentication'] = True
            assert ui.headers['Cache-Control'] == 'no-store' and ui.headers['X-Frame-Options'] == 'DENY'
            for path in ('/app.js', '/style.css'):
                assert ui.request('GET', path)[0] == 200
            checks['installed_assets_and_headers'] = True
            ui.command('project-create', key='aurora-fixture', name='Aurora fictício', objective='Revisar uma apresentação fictícia')
            ui.command('task-create', title='Roteiro fictício')
            task = ui.state['tasks'][0]
            ui.command('task-create', title='Ensaio fictício')
            ui.command('task-update', id=task['id'], title=task['title'], state='done', priority='high', due_date='2026-11-30')
            ui.command('chat', text='Eu prefiro respostas curtas', local=True)
            assert len(ui.state['history']) == 2 and len(ui.state['notices']) == 1
            assert len(ui.state['memories']) == 1 and ui.state['memories'][0]['candidate']['sensitivity'] == 'local_only'
            checks['local_conversation_and_automatic_memory'] = True
            status, _, _ = ui.request('POST', '/api/command', {'op':'reset','revision':0}, auth=True)
            assert status == 409 and len(ui.read()['history']) == 2
            checks['stale_tab_denied_without_mutation'] = True
            assert ui.state['progress']['percent'] == 50.0
            checks['manual_progress_and_task_fields'] = True
        finally:
            ui.close()
        restarted = InstalledUI(root)
        try:
            restarted.command('select', key='aurora-fixture')
            state = restarted.state
            assert state['history'] == [] and len(state['tasks']) == 2 and len(state['memories']) == 1
            assert state['tasks'][0]['id'] == task['id'] and state['tasks'][0]['due_date'] == '2026-11-30'
            assert state['progress']['percent'] == 50.0
            checks['restart_persists_projects_tasks_memory_not_chat'] = True
            restarted.command('project-state', key='aurora-fixture', state='archived')
            assert restarted.state['project'] is None
            restarted.command('project-state', key='aurora-fixture', state='active')
            restarted.command('select', key='aurora-fixture')
            assert len(restarted.state['tasks']) == 2
            checks['archive_reopen_preserve_data'] = True
        finally:
            restarted.close()
        records = [json.loads(line) for line in (root/'audit.jsonl').read_text().splitlines()]
        assert [r['phase'] for r in records] == ['approved', 'completed']
        checks['single_offline_generation_audited'] = True
        checks['graceful_shutdown_releases_storage'] = True
    evidence['passed'] = all(checks.values())
    return evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evidence = verify()
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(evidence, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'python':evidence['package']['python'],'passed':evidence['passed']}))
    return 0 if evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
