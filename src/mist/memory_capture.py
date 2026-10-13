"""Conservative local declaration capture. No LLM and no whole-chat recording."""
import re

from mist.memory_types import MemoryCandidate, MemoryKind, MemorySource
from mist.safety import OutputGuard
from mist.schemas import Style


def capture_declaration(text: str, source: MemorySource, project=None):
    if (len(text) > 1000 or any(char in text for char in ('\n', '?', '"', '`', '“', '”'))
            or any(pattern.search(text) for pattern in OutputGuard()._secret_patterns)):
        return None
    content = text.strip()
    correction = False
    if content.casefold().startswith(('correção:', 'correcao:')):
        content = content.split(':', 1)[1].strip()
        correction = True
    folded = content.casefold().rstrip('.!')
    slot, kind, style = None, MemoryKind.SEMANTIC, None
    if re.fullmatch(r'meu nome (?:é|e) [\w À-ÿ-]{2,80}', folded):
        slot = 'user.name'
    elif re.fullmatch(r'(?:eu )?prefiro respostas (?:curtas|concisas|detalhadas)', folded):
        slot, kind = 'communication.style', MemoryKind.PREFERENCE
        style = Style.DETAILED if folded.endswith('detalhadas') else Style.CONCISE
    elif re.fullmatch(r'(?:eu )?prefiro .{3,500}', folded):
        kind = MemoryKind.PREFERENCE
    elif re.fullmatch(r'meu objetivo (?:é|e) .{3,500}', folded):
        slot = 'user.goal'
    elif project and re.fullmatch(r'o prazo (?:é|e) .{3,200}', folded):
        slot, kind = 'project.deadline', MemoryKind.EPISODIC
    elif project and re.fullmatch(r'decidimos .{3,500}', folded):
        kind = MemoryKind.EPISODIC
    else:
        return None
    return MemoryCandidate(content=content, source=source, project=project, slot=slot,
                           kind=kind, style=style, correction=correction)
