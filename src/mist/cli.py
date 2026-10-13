import argparse
import getpass
import sys
import warnings
from pathlib import Path

from mist import __version__
from mist.authorization import Authorizer
from mist.bootstrap import create_application
from mist.errors import ErrorCode, MistError
from mist.output import load_output_contract
from mist.memory_cli import automatic_notice, memory_command
from mist.memory_recovery import recover_memory
from mist.schemas import Sensitivity

HELP = (
    "/help | /mode AUTO|FAST|PRIMARY | /style auto|concise|detailed\n"
    "/local TEXTO | /status | /reset | /quit\n"
    "/memory (com --memory-dir) | /project NOME | /project global\n"
    "FakeModel é uma simulação. O modo NVIDIA envia contexto permitido à API. Ferramentas desabilitadas."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mist — FakeModel offline ou API NVIDIA explícita")
    parser.add_argument("--config-dir", type=Path, help="Diretório com os três arquivos JSON")
    parser.add_argument("--audit-path", type=Path, help="Arquivo privado para auditoria de metadados")
    parser.add_argument("--message", help="Executar uma interação e sair")
    parser.add_argument("--output-contract", type=Path, help="Contrato JSON de saída para --message")
    parser.add_argument("--allow-external", action="store_true", help="Habilitar envio ao destino externo configurado")
    parser.add_argument("--ask-api-key", action="store_true", help="Ler a chave NVIDIA com entrada oculta, sem salvá-la")
    parser.add_argument("--memory-dir", type=Path, help="Habilitar memória local neste diretório privado (gravação automática por padrão)")
    parser.add_argument("--project", help="Escopo de projeto das memórias; omitido usa escopo global")
    parser.add_argument("--recover-memory", type=Path, help="Restaurar snapshot local mantendo o registro de exclusões; não inicia conversa nem rede")
    args = parser.parse_args(argv)
    if args.recover_memory is not None:
        try:
            if args.memory_dir is None or args.allow_external or args.ask_api_key or args.message is not None:
                raise MistError(ErrorCode.MEMORY_INVALID)
            count = recover_memory(args.memory_dir, args.recover_memory)
            print(f'{count} memória(s) restaurada(s) como locais; registro de exclusões preservado.')
            return 0
        except MistError as exc:
            print(f'{exc.code}: {exc}', file=sys.stderr)
            return 2
    try:
        if args.output_contract is not None and args.message is None:
            raise MistError(ErrorCode.INVALID_INPUT)
        contract = load_output_contract(args.output_contract) if args.output_contract is not None else None
        if args.ask_api_key and not args.allow_external:
            raise MistError(ErrorCode.EXTERNAL_DISABLED)
        # Refuse getpass's echoing fallback when no private terminal is available.
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            key = getpass.getpass("Chave NVIDIA (entrada oculta): ") if args.ask_api_key else None
        app = create_application(args.config_dir, args.audit_path,
                                 allow_external=args.allow_external, api_key=key,
                                 memory_dir=args.memory_dir, project=args.project)
        key = None
    except (EOFError, KeyboardInterrupt):
        print("\nInicialização interrompida.", file=sys.stderr)
        return 130
    except getpass.GetPassWarning:
        print("Entrada oculta indisponível. Use um terminal interativo ou NVIDIA_API_KEY.", file=sys.stderr)
        return 2
    except MistError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        return 2
    if args.message is not None:
        try:
            response = app.handle(args.message, output_contract=contract)
            print(f"Mist ({response.model}): {response.text}")
            for item in app.last_memory_changes:
                print(automatic_notice(item))
            return 0
        except MistError as exc:
            print(f"{exc.code}: {exc}", file=sys.stderr)
            return 2
        except KeyboardInterrupt:
            print("\nInteração interrompida.", file=sys.stderr)
            return 130
        finally:
            app.close()
    external = any(model.external for model in app.settings.models)
    label = "NVIDIA / envio externo habilitado" if external else "offline / FakeModel"
    print(f"Mist {__version__} — {label} / autonomia 0")
    print(HELP)
    while True:
        try:
            line = input("Você> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSessão encerrada.")
            app.close()
            return 0
        if not line:
            continue
        app.last_memory_changes = ()
        try:
            if line == "/quit":
                app.close()
                return 0
            if line == "/help":
                print(HELP)
            elif line.startswith("/mode "):
                app.set_mode(line[6:].strip())
                print(f"Modo: {app.mode}")
            elif line.startswith("/style "):
                app.set_style(line[7:].strip())
                print(f"Estilo: {app.style}")
            elif line == "/status":
                print(f"{label} | modo={app.mode} | estilo={app.style} | autonomia=0 | turnos={len(app.history)//2} | memória={'ativa' if app.memory else 'desligada'} | projeto={app.project or 'global'}")
            elif line == '/memory' or line.startswith('/memory '):
                print(memory_command(app, line))
            elif line.startswith('/project '):
                name = line[9:].strip()
                app.set_project(None if name == 'global' else name)
                print(f'Escopo: {app.project or "global"}. Contexto transitório limpo.')
            elif line == "/reset":
                app.reset()
                print("Contexto e preferências da sessão reiniciados.")
            elif line.startswith("/tool "):
                Authorizer().require_tool(line[6:])
            elif line.startswith("/") and not line.startswith("/local "):
                raise MistError(ErrorCode.INVALID_INPUT)
            else:
                local = line.startswith("/local ")
                response = app.handle(line[7:] if local else line,
                                      Sensitivity.LOCAL_ONLY if local else Sensitivity.EXTERNAL_ALLOWED)
                print(f"Mist ({response.model}): {response.text}")
                for item in app.last_memory_changes:
                    print(automatic_notice(item))
        except MistError as exc:
            print(f"{exc.code}: {exc}", file=sys.stderr)
            for item in app.last_memory_changes:
                print(automatic_notice(item) + ' Geração não concluída.')
        except KeyboardInterrupt:
            print("\nInteração interrompida.")
