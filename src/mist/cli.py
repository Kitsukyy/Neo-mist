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
from mist.schemas import Sensitivity

HELP = (
    "/help | /mode AUTO|FAST|PRIMARY | /style auto|concise|detailed\n"
    "/local TEXTO | /status | /reset | /quit\n"
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
    args = parser.parse_args(argv)
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
                                 allow_external=args.allow_external, api_key=key)
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
            return 0
        except MistError as exc:
            print(f"{exc.code}: {exc}", file=sys.stderr)
            return 2
        except KeyboardInterrupt:
            print("\nInteração interrompida.", file=sys.stderr)
            return 130
    external = any(model.external for model in app.settings.models)
    label = "NVIDIA / envio externo habilitado" if external else "offline / FakeModel"
    print(f"Mist {__version__} — {label} / autonomia 0")
    print(HELP)
    while True:
        try:
            line = input("Você> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSessão encerrada.")
            return 0
        if not line:
            continue
        try:
            if line == "/quit":
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
                print(f"{label} | modo={app.mode} | estilo={app.style} | autonomia=0 | turnos={len(app.history)//2}")
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
        except MistError as exc:
            print(f"{exc.code}: {exc}", file=sys.stderr)
        except KeyboardInterrupt:
            print("\nInteração interrompida.")
