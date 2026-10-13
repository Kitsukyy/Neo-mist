'use strict';
const token = document.querySelector('meta[name="mist-token"]').content;
const $ = id => document.getElementById(id);
let state, busy = false, tab = 'chat', dialogSubmit;
const statuses = {todo:'Pendente',doing:'Em andamento',blocked:'Bloqueada',done:'Concluída',cancelled:'Cancelada'};
const priorities = {low:'Baixa',normal:'Normal',high:'Alta'};
const memoryStatuses = {active:'Ativa',candidate:'Aguardando confirmação',archived:'Arquivada',superseded:'Substituída'};
const epistemic = {declared:'Declaração atribuída',inferred:'Inferência',hypothesis:'Hipótese'};
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function button(text, action, className) {
  const node = el('button', text, className);
  node.type = 'button'; node.addEventListener('click', action); return node;
}
function feedback(id, text) { $(id).textContent = text || ''; $(id).hidden = !text; }
function setBusy(value) {
  busy = value;
  document.querySelectorAll('button,input,select,textarea,summary').forEach(n => {
    if (n.tagName === 'SUMMARY') n.style.pointerEvents = value ? 'none' : '';
    else n.disabled = value;
  });
  $('busy-label').textContent = value ? 'Aguarde…' : '';
  if (!value && state) {
    ['edit-project','archive-project','new-task'].forEach(id => $(id).disabled = !state.current);
  }
}
async function request(path, data) {
  const options = {headers:{'X-Mist-Token':token}, cache:'no-store'};
  if (data) { options.method='POST'; options.headers['Content-Type']='application/json'; options.body=JSON.stringify(data); }
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) { const error = new Error(body.error || 'Operação não concluída.'); error.notices=body.notices; throw error; }
  return body;
}
async function load() { state = await request('/api/state'); render(); }
async function command(op, args={}) {
  if (busy || !state) return false;
  setBusy(true); feedback('error',''); feedback('notice','');
  try {
    const reply = await request('/api/command',{op,revision:state.revision,...args});
    state = reply.state; render(); return true;
  } catch(error) {
    // Refresh is read-only. A timed-out/disconnected POST is never resubmitted.
    try { await load(); } catch { feedback('notice','Não foi possível atualizar os dados. Reinicie a interface ou atualize a página.'); }
    feedback('error',error.message || 'Conexão interrompida. Confira os dados antes de tentar novamente.');
    if (error.notices?.length) feedback('notice',error.notices.join('\n')+' A geração não foi concluída.');
    return false;
  } finally { setBusy(false); }
}
function showTab(name) {
  tab=name;
  document.querySelectorAll('[data-tab]').forEach(n => n.setAttribute('aria-pressed',String(n.dataset.tab===name)));
  ['chat','tasks','memories'].forEach(name => $(name+'-panel').hidden=name!==tab);
}
function render() {
  $('scope-title').textContent=state.current?.name || 'Conversa global';
  $('provider-label').textContent=state.external ? 'NVIDIA · envio externo habilitado' : 'Offline · simulação';
  $('version').textContent=state.version;
  $('mode').value=state.mode; $('style').value=state.style;
  $('message').maxLength=state.max_input_chars;
  $('chat-help').textContent=state.external
    ? 'Envio permitido usa '+state.destinations.join(', ')+'. “Somente local” bloqueia a API. Memórias locais ficam fora do envio.'
    : 'FakeModel é uma simulação: não interpreta perguntas. Memórias automáticas ficam locais. Enter envia · Shift+Enter cria uma linha.';
  const projectList=$('project-list'); projectList.replaceChildren();
  const global=button('Conversa global',()=>command('select',{key:null}),'project-link');
  global.setAttribute('aria-current',String(!state.project)); projectList.append(global);
  state.projects.filter(p=>p.state==='active').forEach(p=>{
    const node=button(p.name,()=>command('select',{key:p.key}),'project-link');
    node.prepend(el('span','◇','project-mark')); node.setAttribute('aria-current',String(state.project===p.key));
    projectList.append(node);
  });
  const archives=$('archive-list'); archives.replaceChildren();
  state.projects.filter(p=>p.state==='archived').forEach(p=>archives.append(button('Reabrir '+p.name,()=>command('project-state',{key:p.key,state:'active'}),'project-link')));
  $('archives').hidden=!archives.childElementCount;
  renderChat(); renderTasks(); renderMemories();
  feedback('notice',state.notices.join('\n'));
  showTab(tab); setBusy(busy);
}
function renderChat() {
  const messages=$('messages'); messages.replaceChildren();
  if (!state.history.length) {
    const welcome=el('div',undefined,'welcome'); welcome.append(el('div','m','orb'),el('h2','Por onde começamos?'),el('p','Um espaço para conversar, organizar seus projetos e continuar de onde você parou.'));
    const suggestions=el('div',undefined,'suggestions');
    suggestions.append(button('Organizar um projeto',()=>{showTab('tasks');projectEditor();}),button('Revisar minhas memórias',()=>showTab('memories')),button('Começar uma conversa',()=>{$('message').focus();}));
    welcome.append(suggestions); messages.append(welcome);
  } else {
    state.history.forEach(m=>{
      const node=el('div',undefined,'message '+m.role);
      if(m.role==='assistant')node.append(el('span',state.external?'Mist':'Mist · resposta simulada','message-label'));
      node.append(el('span',m.content)); messages.append(node);
    });
    messages.scrollTop=messages.scrollHeight;
  }
}
function renderTasks() {
  const project=state.current;
  $('task-title').textContent=project?.name || 'Seu próximo projeto começa aqui';
  $('objective').textContent=project?.objective || (project ? 'Adicione um objetivo para dar direção ao projeto.' : 'Crie um projeto ou selecione um na barra lateral para organizar suas tarefas.');
  const progress=$('progress'); progress.replaceChildren(); progress.hidden=!project;
  if(project) {
    const data=state.progress; const percent=data.percent===null?'—':Math.round(data.percent)+'%';
    const detail=el('div',undefined,'progress-detail'); detail.append(el('div',(data.counts.done||0)+' de '+data.eligible+' tarefas elegíveis concluídas · progresso declarado'));
    const track=el('progress',undefined,'progress-track');track.max=100;track.value=data.percent||0;track.setAttribute('aria-label','Progresso declarado'); detail.append(track);
    progress.append(el('span',percent,'progress-number'),detail);
  }
  const list=$('tasks');list.replaceChildren();
  if(!project || !state.tasks.length) list.append(el('div',project?'Nenhuma tarefa ainda. Adicione o primeiro passo.':'Seus projetos e tarefas são guardados somente neste computador.','empty-state'));
  state.tasks.forEach(t=>{
    const card=el('article',undefined,'card');const top=el('div',undefined,'card-top');
    top.append(el('h3',t.title,'card-title'),el('span',statuses[t.state],'tag'));
    const actions=el('div',undefined,'card-actions');actions.append(button('Editar tarefa',()=>taskEditor(t)),button('Excluir tarefa',()=>confirmDialog('Excluir tarefa?',t.title,'Esta exclusão não tem lixeira. Cópias antigas do catálogo podem conter o texto.',()=>command('task-delete',{id:t.id,confirm:true}))));
    card.append(top,el('div','Prioridade '+priorities[t.priority]+(t.due_date?' · Prazo '+t.due_date:' · Sem prazo'),'card-meta'),actions);list.append(card);
  });
}
function renderMemories() {
  const query=$('memory-search').value.toLocaleLowerCase('pt-BR');const list=$('memories');list.replaceChildren();
  $('memory-count').textContent=state.memories.length+(state.memories.length===1?' memória exibida · ':' memórias exibidas · ')+(state.current?'globais e deste projeto':'escopo global')+(state.memory_more?' · Há mais memórias; use o terminal para consultá-las.':'');
  state.memories.filter(m=>m.candidate.content.toLocaleLowerCase('pt-BR').includes(query)).forEach(m=>{
    const c=m.candidate;const card=el('article',undefined,'card');const top=el('div',undefined,'card-top');
    top.append(el('p',c.content,'card-title'),el('span',memoryStatuses[m.status],'tag'));
    const meta=epistemic[c.state]+' · '+(c.project||'global')+' · '+(c.sensitivity==='local_only'?'Somente local':'Envio externo permitido')+'\nFonte: '+({user:'você',model:'modelo',application:'aplicação'}[c.source.origin]||c.source.origin)+' · '+new Date(c.source.timestamp).toLocaleString('pt-BR')+' · Versão '+m.revision;
    const actions=el('div',undefined,'card-actions');actions.append(button('Corrigir',()=>memoryEditor(m)));
    if(m.status==='candidate')actions.append(button('Confirmar',()=>command('memory-accept',{id:m.id})));
    if(m.status==='active'||m.status==='candidate')actions.append(button('Arquivar memória',()=>command('memory-archive',{id:m.id})));
    if(c.sensitivity!=='local_only')actions.append(button('Restringir ao local',()=>command('memory-local',{id:m.id})));
    actions.append(button('Excluir memória',()=>confirmDialog('Excluir memória?',c.content,'Exclui também versões e derivados e limpa a conversa. Backups antigos continuam privados; a restauração respeita o registro de exclusões.',()=>command('memory-delete',{id:m.id,confirm:true}))));
    card.append(top,el('div',meta,'card-meta'),actions);list.append(card);
  });
  if(!list.childElementCount)list.append(el('div',query?'Nenhuma memória exibida corresponde à busca.':'Nenhuma memória neste escopo. Você também pode guardar uma declaração manualmente.','empty-state'));
}
function editor(title, specs, help, submit, save='Salvar') {
  if(busy)return;
  $('dialog-title').textContent=title;const container=$('dialog-fields');container.replaceChildren();
  specs.forEach(s=>{
    const label=el('label',s.label);const control=el(s.options?'select':s.multiline?'textarea':'input');
    control.name=s.name;
    if(s.options)Object.entries(s.options).forEach(([value,text])=>{const option=el('option',text);option.value=value;control.append(option);});
    else {if(!s.multiline)control.type=s.type||'text';if(s.max)control.maxLength=s.max;if(s.multiline)control.rows=4;}
    control.value=s.value||'';control.required=Boolean(s.required);if(s.pattern)control.pattern=s.pattern;
    label.append(control);container.append(label);
  });
  $('dialog-help').textContent=help;$('save-dialog').textContent=save;$('save-dialog').className=save==='Excluir'?'danger':'primary';dialogSubmit=submit;
  $('editor').showModal();
}
function projectEditor(project) {
  const specs=[{name:'name',label:'Nome do projeto',max:200,required:true,value:project?.name},{name:'objective',label:'Objetivo',max:2000,multiline:true,value:project?.objective}];
  editor(project?'Editar projeto':'Criar projeto',specs,'Projetos ficam locais. Selecionar um projeto limpa a conversa e muda o escopo das memórias.',data=>{const key=project?.key || (data.name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,60)||'projeto')+'-'+crypto.randomUUID().slice(0,8);return command(project?'project-update':'project-create',{...data,key});});
}
function taskEditor(task) {
  if(!state.current)return;
  const specs=[{name:'title',label:'Título da tarefa',max:500,required:true,value:task?.title}];
  if(task)specs.push({name:'state',label:'Estado',options:statuses,value:task.state},{name:'priority',label:'Prioridade',options:priorities,value:task.priority},{name:'due_date',label:'Prazo (opcional)',type:'date',value:task.due_date});
  editor(task?'Editar tarefa':'Adicionar tarefa',specs,'Os estados são registrados por você; nenhuma tarefa é executada automaticamente.',data=>command(task?'task-update':'task-create',task?{...data,id:task.id,due_date:data.due_date||null}:data));
}
function memoryEditor(memory) {
  editor(memory?'Corrigir memória':'Guardar memória',[{name:'text',label:'Declaração',max:2000,multiline:true,required:true,value:memory?.candidate.content}],memory?'A correção fica somente local e limpa o contexto da conversa.':'Informação atribuída a você, guardada somente neste computador.',data=>command(memory?'memory-replace':'memory-create',{...data,...(memory?{id:memory.id}:{})}));
}
function confirmDialog(title, text, help, action) {
  editor(title,[],help,action,'Excluir');$('dialog-fields').append(el('p',text,'muted'));
}
$('editor-form').addEventListener('submit',async event=>{
  event.preventDefault();if(busy)return;
  const data=Object.fromEntries(new FormData(event.currentTarget));$('editor').close();
  await dialogSubmit(data);
});
['close-dialog','cancel-dialog'].forEach(id=>$(id).addEventListener('click',()=>$('editor').close()));
document.querySelectorAll('[data-tab]').forEach(n=>n.addEventListener('click',()=>showTab(n.dataset.tab)));
$('new-project').addEventListener('click',()=>projectEditor());
$('edit-project').addEventListener('click',()=>projectEditor(state.current));
$('archive-project').addEventListener('click',()=>command('project-state',{key:state.project,state:'archived'}));
$('new-task').addEventListener('click',()=>taskEditor());
$('new-memory').addEventListener('click',()=>memoryEditor());
$('new-chat').addEventListener('click',async()=>{if(await command('reset'))showTab('chat');});
$('memory-search').addEventListener('input',()=>{if(state)renderMemories();});
['mode','style'].forEach(id=>$(id).addEventListener('change',()=>command('preferences',{mode:$('mode').value,style:$('style').value})));
$('chat-form').addEventListener('submit',async event=>{
  event.preventDefault();const text=$('message').value;if(busy||!text.trim())return;
  if(await command('chat',{text,local:$('privacy').value==='local'})){$('message').value='';$('message').focus();}
});
$('message').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();$('chat-form').requestSubmit();}});
setBusy(true);
load().catch(error=>feedback('error',error.message||'Não foi possível conectar. Confira se o terminal continua aberto.')).finally(()=>setBusy(false));
