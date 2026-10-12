from typing import Protocol

from mist.schemas import Envelope


class Provider(Protocol):
    def generate(self, envelope: Envelope) -> str: ...


class FakeModel:
    """A deterministic simulation, with no imports or clients for network access."""

    def generate(self, envelope: Envelope) -> str:
        instructions = envelope.request.messages[0].content
        if "Comunicação nesta interação: didática e detalhada" in instructions:
            return (
                "[Simulação — FakeModel] O fluxo de entrada, identidade, Guarda, auditoria e resposta "
                "foi percorrido. Não sou um modelo de linguagem: não interpretei sua pergunta. "
                "Não executei ferramentas e não enviei dados à rede."
            )
        return "[Simulação — FakeModel] Fluxo validado. Não interpretei a pergunta nem executei ações."

