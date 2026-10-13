"""Loopback-only, single-session UI. The serving thread owns the SQLite connection."""
import argparse
import getpass
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.resources import files
import json
import os
from pathlib import Path
import secrets
import sys
import warnings
import webbrowser

from mist import __version__
from mist.bootstrap import create_application
from mist.errors import ErrorCode, MistError
from mist.schemas import RouterMode, Sensitivity, Style

MAX_BODY = 32768


def memory_notice(item):
    return ("Memória automática guardada localmente. Revise na aba Memórias."
            if item.status.value == "active" else "Uma memória automática aguarda confirmação na aba Memórias.")


class UIConflict(Exception):
    pass


def fields(data, required=(), optional=()):
    if not isinstance(data, dict) or set(data) - set(required) - set(optional) or set(required) - set(data):
        raise MistError(ErrorCode.INVALID_INPUT)
    return data


class UISession:
    def __init__(self, app):
        self.app = app
        self.revision = 0

    def state(self):
        app = self.app
        catalog = app.require_projects()
        projects = catalog.list()
        current = catalog.get(app.project) if app.project else None
        memories = app.require_memory().list_items(app.project, limit=201)
        return {
            'version': __version__, 'revision': self.revision,
            'external': any(m.external for m in app.settings.models),
            'destinations': list(app.settings.allowed_external_destinations),
            'mode': app.mode.value, 'style': app.style.value, 'project': app.project,
            'projects': [p.model_dump(mode='json') for p in projects],
            'current': current.model_dump(mode='json') if current else None,
            'tasks': [t.model_dump(mode='json') for t in catalog.tasks(app.project)] if current else [],
            'progress': catalog.progress(app.project) if current else None,
            'memories': [m.model_dump(mode='json') for m in memories[:200]],
            'memory_more': len(memories) > 200,
            'history': [m.model_dump(mode='json') for m in app.history],
            'notices': [memory_notice(m) for m in app.last_memory_changes],
            'max_input_chars': app.settings.max_input_chars,
        }

    def command(self, data):
        if not isinstance(data, dict) or type(data.get('revision')) is not int or not isinstance(data.get('op'), str):
            raise MistError(ErrorCode.INVALID_INPUT)
        if data['revision'] != self.revision:
            raise UIConflict()
        args = {k: v for k, v in data.items() if k not in ('revision', 'op')}
        self.app.last_memory_changes = ()
        try:
            return self._dispatch(data['op'], args)
        finally:
            # Even a failed generation can capture a local declaration. Another tab
            # must refresh before performing a mutation against this session.
            self.revision += 1

    def _dispatch(self, op, args):
        app = self.app
        store = app.require_projects()
        if op == 'chat':
            fields(args, ('text', 'local'))
            if type(args['local']) is not bool:
                raise MistError(ErrorCode.INVALID_INPUT)
            response = app.handle(args['text'], Sensitivity.LOCAL_ONLY if args['local'] else Sensitivity.EXTERNAL_ALLOWED)
            return {'response': response.model_dump(mode='json')}
        if op == 'reset':
            fields(args)
            app.reset()
        elif op == 'preferences':
            fields(args, ('mode', 'style'))
            try:
                mode, style = RouterMode(args['mode']), Style(args['style'])
            except (ValueError, TypeError):
                raise MistError(ErrorCode.INVALID_INPUT) from None
            app.set_mode(mode.value)
            app.set_style(style.value)
        elif op == 'select':
            fields(args, ('key',))
            if args['key'] is None:
                app.set_project(None)
            else:
                app.use_project(args['key'])
        elif op == 'project-create':
            fields(args, ('key', 'name', 'objective'))
            item = store.create(args['key'], args['name'], args['objective'], app._source())
            app.use_project(item.key)
        elif op == 'project-update':
            fields(args, ('key', 'name', 'objective'))
            store.update(args['key'], app._source(), name=args['name'], objective=args['objective'])
            app._history.clear()
        elif op == 'project-state':
            fields(args, ('key', 'state'))
            store.update(args['key'], app._source(), state=args['state'])
            if args['state'] == 'archived' and app.project == args['key']:
                app.set_project(None)
            app._history.clear()
        elif op == 'task-create':
            fields(args, ('title',))
            store.add_task(app.project, args['title'], app._source())
            app._history.clear()
        elif op == 'task-update':
            fields(args, ('id', 'title', 'state', 'priority', 'due_date'))
            if not isinstance(args['title'], str) or args['due_date'] is not None and not isinstance(args['due_date'], str):
                raise MistError(ErrorCode.INVALID_INPUT)
            store.update_task(app.project, args['id'], app._source(), **{k: v for k, v in args.items() if k != 'id'})
            app._history.clear()
        elif op == 'task-delete':
            fields(args, ('id', 'confirm'))
            self._confirmed(args)
            store.delete_task(app.project, args['id'], app._source())
            app._history.clear()
        elif op == 'memory-create':
            fields(args, ('text',))
            app.remember(args['text'])
            app._history.clear()
        elif op == 'memory-replace':
            fields(args, ('id', 'text'))
            if not isinstance(args['text'], str):
                raise MistError(ErrorCode.INVALID_INPUT)
            app.replace_memory(args['id'], args['text'])
        elif op == 'memory-delete':
            fields(args, ('id', 'confirm'))
            self._confirmed(args)
            app.forget(args['id'])
        elif op in ('memory-accept', 'memory-archive', 'memory-local'):
            fields(args, ('id',))
            action = {'memory-accept': 'accept', 'memory-archive': 'archive', 'memory-local': 'restrict_local'}[op]
            getattr(app.require_memory(), action)(args['id'], app.project)
            app._history.clear()
        else:
            raise MistError(ErrorCode.INVALID_INPUT)
        return {}

    @staticmethod
    def _confirmed(args):
        if args['confirm'] is not True:
            raise MistError(ErrorCode.INVALID_INPUT)


class LocalServer(HTTPServer):
    """Intentionally serial: Application and its SQLite owner never cross threads."""
    def __init__(self, session, port=0):
        self.session = session
        self.token = secrets.token_urlsafe(32)
        super().__init__(('127.0.0.1', port), LocalHandler)
        self.authority = f'127.0.0.1:{self.server_port}'
        self.origin = f'http://{self.authority}'


class LocalHandler(BaseHTTPRequestHandler):
    server_version = 'MistLocal'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, format, *args):
        # No URLs, headers, submitted texts or credentials in terminal logs.
        pass

    def send_error(self, code, message=None, explain=None):
        self._json(code, {'error': 'Solicitação HTTP não aceita.'})

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, status, data):
        self._send(status, json.dumps(data, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

    def _authorized(self, api=False, mutate=False):
        hosts = self.headers.get_all('Host', [])
        origins = self.headers.get_all('Origin', [])
        if hosts != [self.server.authority] or self.headers.get('Sec-Fetch-Site') not in (None, 'none', 'same-origin'):
            return False
        if origins and origins != [self.server.origin] or mutate and origins != [self.server.origin]:
            return False
        if api:
            tokens = self.headers.get_all('X-Mist-Token', [])
            if len(tokens) != 1 or not secrets.compare_digest(tokens[0].encode('utf-8'), self.server.token.encode('ascii')):
                return False
        return True

    def do_GET(self):
        api = self.path.startswith('/api/')
        if not self._authorized(api=api):
            self._json(403, {'error': 'Acesso local não autorizado.'})
            return
        if self.path == '/api/state':
            try:
                self._json(200, self.server.session.state())
            except MistError as exc:
                self._json(400, {'error': str(exc), 'code': exc.code})
            except Exception:
                self._json(500, {'error': 'Estado local indisponível.'})
            return
        asset = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                 '/style.css': ('style.css', 'text/css')}.get(self.path)
        if asset is None:
            self._json(404, {'error': 'Página não encontrada.'})
            return
        body = files('mist').joinpath('web', asset[0]).read_bytes()
        if self.path == '/':
            body = body.replace(b'__MIST_TOKEN__', self.server.token.encode('ascii'))
        self._send(200, body, asset[1] + '; charset=utf-8')

    def do_POST(self):
        if not self._authorized(api=True, mutate=True):
            self._json(403, {'error': 'Acesso local não autorizado.'})
            return
        if self.path != '/api/command':
            self._json(404, {'error': 'Operação inexistente.'})
            return
        lengths = self.headers.get_all('Content-Length', [])
        try:
            if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
                raise ValueError()
            length = int(lengths[0])
            if length < 1 or length > MAX_BODY or self.headers.get('Transfer-Encoding') is not None:
                raise ValueError()
            if self.headers.get('Content-Type') != 'application/json':
                raise ValueError()
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError()
            data = json.loads(raw)
        except (ValueError, UnicodeError, TimeoutError, RecursionError):
            self._json(400, {'error': 'Dados inválidos ou muito grandes.'})
            return
        try:
            result = self.server.session.command(data)
            self._json(200, {'result': result, 'state': self.server.session.state()})
        except UIConflict:
            self._json(409, {'error': 'A sessão mudou em outra aba. Atualize a página antes de tentar novamente.'})
        except MistError as exc:
            self._json(400, {'error': str(exc), 'code': exc.code,
                             'notices': [memory_notice(m) for m in self.server.session.app.last_memory_changes]})
        except Exception:
            # A mutation may have committed before its response failed; never retry.
            self._json(500, {'error': 'Operação interrompida. Atualize para conferir os dados; não houve repetição automática.'})


def main(argv=None):
    parser = argparse.ArgumentParser(description='Mist — interface visual local')
    parser.add_argument('--config-dir', type=Path)
    parser.add_argument('--audit-path', type=Path)
    parser.add_argument('--memory-dir', type=Path)
    parser.add_argument('--port', type=int, default=0, help='Porta local; 0 escolhe uma disponível')
    parser.add_argument('--allow-external', action='store_true')
    parser.add_argument('--ask-api-key', action='store_true')
    parser.add_argument('--open-browser', action='store_true')
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error('Porta inválida.')
    state_root = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local' / 'state')) / 'neo-mist'
    app = None
    try:
        if args.ask_api_key and not args.allow_external:
            raise MistError(ErrorCode.EXTERNAL_DISABLED)
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            key = getpass.getpass('Chave NVIDIA (entrada oculta): ') if args.ask_api_key else None
        app = create_application(args.config_dir, args.audit_path, allow_external=args.allow_external,
                                 api_key=key, memory_dir=args.memory_dir or state_root / 'ui')
        key = None
        with LocalServer(UISession(app), args.port) as server:
            print(f'Mist {__version__}: {server.origin}', flush=True)
            print('Interface local. Memória automática ativa; ferramentas desabilitadas. Ctrl+C encerra.', flush=True)
            if args.open_browser:
                webbrowser.open(server.origin)
            server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print('\nInterface encerrada.')
        return 0
    except (MistError, OSError, EOFError, getpass.GetPassWarning) as exc:
        print(str(exc) if isinstance(exc, MistError) else 'Não foi possível iniciar a interface local. Confira porta, armazenamento e entrada oculta.', file=sys.stderr)
        return 2
    finally:
        if app is not None:
            app.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
