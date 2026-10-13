"""Explicit local UI commands; never invoked by generated model text."""
import json
from pathlib import Path
import shlex

from mist.errors import ErrorCode, MistError


def automatic_notice(item):
    state = 'guardada localmente' if item.status.value == 'active' else 'aguardando confirmação'
    return f'Memória automática: {item.id} — {state}.'


def describe(item):
    states = {'declared': 'declaração atribuída', 'inferred': 'inferência', 'hypothesis': 'hipótese'}
    statuses = {'active': 'ativa', 'candidate': 'aguardando confirmação', 'archived': 'arquivada', 'superseded': 'substituída'}
    privacy = 'somente local' if item.candidate.sensitivity.value == 'local_only' else 'envio externo permitido'
    return (f'{item.id} | {statuses[item.status.value]} | versão {item.revision}\n'
            f'{item.candidate.content}\n'
            f'{states[item.candidate.state.value]} | projeto: {item.candidate.project or "global"} | {privacy}\n'
            f'Fonte: {item.candidate.source.origin}, {item.candidate.source.timestamp}; {len(item.sources)} registro(s) de origem.')


def memory_command(app, line):
    try:
        parts = shlex.split(line)
    except ValueError:
        raise MistError(ErrorCode.MEMORY_INVALID) from None
    store = app.require_memory()
    if len(parts) < 2:
        return ('/memory list | find TEXTO | show ID | remember TEXTO | replace ID TEXTO\n'
                '/memory accept ID | archive ID | delete ID | local ID | allow-external ID\n'
                '/memory export ARQUIVO | backup ARQUIVO | restore ARQUIVO\n'
                'Memórias automáticas ficam locais. Backups/exportações contêm conteúdo privado.')
    operation, args = parts[1], parts[2:]
    if operation == 'remember' and args:
        item = app.remember(' '.join(args))
        return f'Memória guardada: {item.id} ({item.status.value}, local).'
    if operation == 'replace' and len(args) >= 2:
        item = app.replace_memory(args[0], ' '.join(args[1:]))
        return f'Memória corrigida: {item.id}, versão {item.revision}. Contexto transitório limpo.'
    if operation == 'delete' and len(args) == 1:
        count = app.forget(args[0])
        return f'{count} memória(s) e versões/derivados excluídos. Contexto transitório limpo. Backups antigos permanecem privados; a restauração respeita as exclusões.'
    if operation == 'list' and not args:
        items = store.list_items(app.project)
    elif operation == 'find' and args:
        items = store.retrieve(' '.join(args), app.project, settings=app.settings.memory)
    elif operation == 'show' and len(args) == 1:
        items = (store.get(args[0], app.project),)
    elif operation in ('archive', 'accept', 'local', 'allow-external') and len(args) == 1:
        action = {'local': store.restrict_local, 'allow-external': store.allow_external,
                  'archive': store.archive, 'accept': store.accept}[operation]
        action(args[0], app.project)
        app._history.clear()
        return 'Memória atualizada. Contexto transitório limpo.'
    elif operation in ('export', 'backup', 'restore') and len(args) == 1:
        path = Path(args[0])
        if operation == 'restore':
            count = store.restore(path)
            app._history.clear()
            return f'{count} memória(s) restaurada(s) como locais; exclusões e versões recentes preservadas.'
        store.snapshot(path)
        return 'Arquivo privado criado, sem sobrescrever outro. Guarde o registro de exclusões junto do armazenamento; backups antigos podem conter textos depois excluídos.'
    else:
        raise MistError(ErrorCode.MEMORY_INVALID)
    return '\n\n'.join(describe(item) for item in items) if items else 'Nenhuma memória encontrada neste escopo.'
