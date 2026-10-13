"""Explicit human project commands. Model responses are never parsed as commands."""
from pathlib import Path
import shlex

from mist.errors import ErrorCode, MistError
from mist.project_types import ProjectState

HELP = (
    '/projects list | create ID "Nome" ["Objetivo"] | use ID | show [ID]\n'
    '/projects rename ID NOME | objective ID TEXTO | archive ID | reopen ID\n'
    '/projects tasks [ID] | add ID TEXTO | task ID UUID STATUS\n'
    '/projects edit-task ID UUID TEXTO | priority ID UUID baixa|normal|alta\n'
    '/projects due ID UUID AAAA-MM-DD|none | delete-task ID UUID\n'
    '/projects progress [ID] | export ARQUIVO\n'
    'STATUS: pendente | andamento | bloqueada | concluida | cancelada.\n'
    'Projetos e tarefas ficam locais. Progresso é declarado pelo usuário.'
)
STATES = {'todo':'pendente','doing':'em andamento','blocked':'bloqueada','done':'concluída','cancelled':'cancelada'}
STATUS_INPUT = {**{key:key for key in STATES},'pendente':'todo','andamento':'doing','bloqueada':'blocked','concluida':'done','concluída':'done','cancelada':'cancelled'}
PRIORITIES = {'baixa':'low','normal':'normal','alta':'high','low':'low','high':'high'}


def describe_project(item):
    state='ativo' if item.state is ProjectState.ACTIVE else 'arquivado'
    return (f'{item.key} — {item.name} | {state} | versão {item.revision}\n'
            f'Objetivo: {item.objective or "não informado"}\n'
            f'Local | declaração do usuário | atualizado em {item.updated_by.timestamp}')


def describe_task(item):
    priority={'low':'baixa','normal':'normal','high':'alta'}[item.priority.value]
    return (f'{item.id} | {STATES[item.state.value]} | prioridade {priority}\n'
            f'{item.title} | prazo: {item.due_date or "não informado"} | versão {item.revision}')


def project_command(app,line):
    try:parts=shlex.split(line)
    except ValueError:raise MistError(ErrorCode.PROJECT_INVALID) from None
    if not parts or parts[0]!='/projects':raise MistError(ErrorCode.PROJECT_INVALID)
    if len(parts)==1:return HELP
    store=app.require_projects()
    operation,args=parts[1],parts[2:]
    if operation=='create' and len(args) in (2,3):
        return describe_project(store.create(args[0],args[1],args[2] if len(args)==3 else '',app._source()))
    if operation=='list' and not args:
        items=store.list()
        return '\n\n'.join(describe_project(item) for item in items) if items else 'Nenhum projeto cadastrado.'
    if operation=='use' and len(args)==1:
        item=app.use_project(args[0])
        return f'Projeto atual: {item.key} — {item.name}. Contexto transitório limpo; memórias neste escopo.'
    if operation in ('show','tasks','progress') and len(args)<=1:
        key=args[0] if args else app.project
        if key is None:raise MistError(ErrorCode.PROJECT_INVALID)
        if operation=='show':return describe_project(store.get(key))
        if operation=='tasks':
            items=store.tasks(key)
            return '\n\n'.join(describe_task(item) for item in items) if items else 'Nenhuma tarefa cadastrada neste projeto.'
        progress=store.progress(key)
        percent=f"{progress['percent']}%" if progress['percent'] is not None else 'sem percentual: nenhuma tarefa elegível'
        counts=', '.join(f'{STATES[state]}: {progress["counts"].get(state,0)}' for state in STATES)
        return f'Progresso declarado: {percent}. Canceladas fora do percentual.\n{counts}'
    if operation in ('rename','objective') and len(args)>=2:
        item=store.update(args[0],app._source(),**{('name' if operation=='rename' else 'objective'):' '.join(args[1:])})
        app._history.clear()
        return describe_project(item)
    if operation in ('archive','reopen') and len(args)==1:
        item=store.update(args[0],app._source(),state=('archived' if operation=='archive' else 'active'))
        if operation=='archive' and app.project==item.key:app.set_project(None)
        else:app._history.clear()
        return describe_project(item)+'\nMemórias e tarefas preservadas; arquivamento não é exclusão.'
    if operation=='add' and len(args)>=2:
        return describe_task(store.add_task(args[0],' '.join(args[1:]),app._source()))
    if operation=='delete-task' and len(args)==2:
        store.delete_task(args[0],args[1],app._source())
        app._history.clear()
        return 'Tarefa excluída do catálogo. Exportações/cópias antigas podem conservar o texto.'
    if operation=='edit-task' and len(args)>=3:
        change={'title':' '.join(args[2:])}
    elif operation=='task' and len(args)==3 and args[2] in STATUS_INPUT:
        change={'state':STATUS_INPUT[args[2]]}
    elif operation=='priority' and len(args)==3 and args[2] in PRIORITIES:
        change={'priority':PRIORITIES[args[2]]}
    elif operation=='due' and len(args)==3:
        change={'due_date':None if args[2]=='none' else args[2]}
    elif operation=='export' and len(args)==1:
        store.export(Path(args[0]))
        return 'Exportação JSON privada criada, sem sobrescrever outro arquivo. Inclui todos os projetos/tarefas e fontes; não inclui memórias nem permite restauração.'
    else:raise MistError(ErrorCode.PROJECT_INVALID)
    item=store.update_task(args[0],args[1],app._source(),**change)
    app._history.clear()
    return describe_task(item)
