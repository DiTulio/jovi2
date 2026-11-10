import json
from pathlib import Path
from jovi import validar_perfil, ler_numero

BASE = Path(__file__).resolve().parent


def gerar_relatorio(origem):
    with origem.open(encoding="utf-8") as arquivo:
        pacote = json.load(arquivo)
    if not isinstance(pacote, dict) or pacote.get("sistema") != "Jovi V70" or pacote.get("versao_integracao") != 2:
        raise ValueError("Formato de integração incompatível.")
    if not isinstance(pacote.get("usuario"), str):
        raise ValueError("Usuário ausente no pacote.")
    perfil = validar_perfil(pacote.get("perfil"))
    acertos = sum(s["acertos"] for s in perfil["simulados"])
    total = sum(s["total"] for s in perfil["simulados"])
    linhas = ["JOVI V70 - RELATÓRIO DE ESTUDOS", f"Usuário: {pacote['usuario']}",
              f"Anotações: {len(perfil['anotacoes'])}", f"Pesquisas: {len(perfil['pesquisas'])}",
              f"Simulados: {len(perfil['simulados'])}", f"Acertos nos simulados: {acertos}/{total}"]
    for materia, topicos in perfil["materias"].items():
        for topico, dados in topicos.items():
            for pergunta, _, placar in dados["flashcards"]:
                linhas.append(f"{materia} / {topico} / {pergunta}: {placar[0]} acertos, {placar[1]} erros")
    destino = origem.with_suffix(".txt")
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return destino


def main():
    try:
        arquivos = sorted((BASE / "integracao").glob("*.json"))
        if not arquivos:
            print("Use a opção 7 do Jovi para exportar dados primeiro.")
            return
        print("0. Sair")
        for i, caminho in enumerate(arquivos, 1):
            print(f"{i}. {caminho.name}")
        escolha = ler_numero("Exportação: ", 0, len(arquivos))
        if escolha:
            print("Relatório gerado:", gerar_relatorio(arquivos[escolha - 1]))
    except (ValueError, OSError) as erro:
        print("Não foi possível gerar o relatório:", erro)
    except (EOFError, KeyboardInterrupt):
        print("\nEncerrado.")


if __name__ == "__main__":
    main()
