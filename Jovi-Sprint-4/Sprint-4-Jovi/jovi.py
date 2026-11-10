import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
ARQUIVO_DADOS = BASE / "dados" / "jovi_v2.json"
API_URL = "https://pt.wikipedia.org/w/api.php"
ITERACOES = 600_000
APPS_BLOQUEADOS = ["Instagram", "TikTok"]
APPS_LIBERADOS = ["Khan Academy", "Wikipedia"]

MATERIAS = {
    "Matemática": {
        "Geometria Plana": {
            "flashcards": [("Fórmula da área de um triângulo?", "A = (base x altura) / 2", [0, 0])],
            "questoes": [("Fórmula da área de um círculo?", ["A = 2πr", "A = πr²"], 1)],
        }
    },
    "Física": {
        "Leis de Newton": {
            "flashcards": [("O que diz a 1ª Lei de Newton?", "Inércia.", [0, 0])],
            "questoes": [("Fórmula da 2ª Lei de Newton?", ["F = m . a", "V = v0 + at"], 0)],
        }
    },
}

def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def salvar_json(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=caminho.parent,
                                         suffix=".tmp", delete=False) as arquivo:
            temporario = Path(arquivo.name)
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    finally:
        if temporario is not None and temporario.exists():
            temporario.unlink()

def ler_numero(mensagem, minimo, maximo):
    while True:
        try:
            numero = int(input(mensagem).strip())
            if minimo <= numero <= maximo:
                return numero
        except ValueError:
            pass
        print(f"Digite um número inteiro entre {minimo} e {maximo}.")

def ler_texto(mensagem, limite=3000):
    while True:
        texto = input(mensagem).strip()
        if 1 <= len(texto) <= limite:
            return texto
        print(f"Digite um texto com 1 a {limite} caracteres.")

def ler_confirmacao(mensagem):
    while True:
        resposta = input(mensagem + " (s/n): ").strip().lower()
        if resposta in ("s", "n"):
            return resposta == "s"
        print("Resposta inválida. Digite s para sim ou n para não.")

def alternar_modo(dados):
    dados["modo_estudo"] = not dados["modo_estudo"]
    print("Modo Estudo:", "ATIVADO" if dados["modo_estudo"] else "DESATIVADO")
    print("Simulação acadêmica: não bloqueia aplicativos no computador/celular.")
    if dados["modo_estudo"]:
        print("Bloqueados na simulação:", ", ".join(APPS_BLOQUEADOS))
        print("Liberados na simulação:", ", ".join(APPS_LIBERADOS))
    return True

def consultar_api(parametros):
    parametros = {"action": "query", "format": "json", "formatversion": 2, **parametros}
    requisicao = Request(API_URL + "?" + urlencode(parametros), headers={
        "User-Agent": "JoviStudySprint4/1.0 (educational Python project)",
        "Accept": "application/json",
    })
    with urlopen(requisicao, timeout=10) as resposta:
        dados = json.load(resposta)
    if not isinstance(dados, dict) or "error" in dados or not isinstance(dados.get("query"), dict):
        raise ValueError("Resposta inesperada da API.")
    return dados["query"]

def buscar_artigo(termo):
    busca = consultar_api({"list": "search", "srsearch": termo, "srlimit": 1})
    resultados = busca["search"]
    if not isinstance(resultados, list):
        raise ValueError("Lista de resultados inválida.")
    if not resultados:
        return None
    pagina_id = resultados[0]["pageid"]
    if type(pagina_id) is not int or pagina_id <= 0:
        raise ValueError("Identificador de página inválido.")
    consulta = consultar_api({"prop": "extracts", "pageids": pagina_id,
                              "exintro": 1, "explaintext": 1})
    pagina = consulta["pages"][0]
    titulo, resumo = pagina["title"], pagina.get("extract", "")
    if not isinstance(titulo, str) or not titulo.strip() or not isinstance(resumo, str):
        raise ValueError("Artigo inválido.")
    if not resumo.strip():
        return None
    return {"data": agora(), "termo": termo, "titulo": titulo, "resumo": resumo,
            "url": f"https://pt.wikipedia.org/?curid={pagina_id}"}

def pesquisar(dados):
    termo = ler_texto("Assunto para pesquisar na Wikipédia: ", 150)
    try:
        artigo = buscar_artigo(termo)
    except HTTPError as erro:
        print(f"A API retornou HTTP {erro.code}. Tente novamente mais tarde.")
        return False
    except (URLError, TimeoutError, OSError):
        print("Não foi possível acessar a API. Verifique a internet e tente novamente.")
        return False
    except (ValueError, KeyError, IndexError, TypeError):
        print("A API enviou uma resposta inválida. Nenhuma pesquisa foi salva.")
        return False
    if artigo is None:
        print("Nenhum artigo com introdução encontrado. Tente outro termo.")
        return False
    print(f"\n{artigo['titulo']}\n{artigo['resumo']}\nFonte: {artigo['url']}")
    print("Conteúdo da Wikipédia: confira a fonte antes de usar em trabalhos.")
    if ler_confirmacao("Salvar esta pesquisa para consultar sem internet?"):
        dados["pesquisas"].append(artigo)
        return True
    return False

def novo_perfil():
    return {"materias": json.loads(json.dumps(MATERIAS)), "modo_estudo": False,
            "anotacoes": [], "simulados": [], "pesquisas": []}


def exigir(condicao):
    if not condicao:
        raise ValueError("Estrutura de dados inválida.")


def texto_valido(valor):
    return isinstance(valor, str) and bool(valor.strip())


def inteiro_valido(valor):
    return type(valor) is int and valor >= 0


def validar_perfil(perfil):
    try:
        exigir(isinstance(perfil, dict) and type(perfil["modo_estudo"]) is bool)
        materias = perfil["materias"]
        exigir(isinstance(materias, dict) and bool(materias))
        for materia, topicos in materias.items():
            exigir(texto_valido(materia) and isinstance(topicos, dict) and bool(topicos))
            for topico, conteudo in topicos.items():
                exigir(texto_valido(topico) and isinstance(conteudo, dict))
                exigir(isinstance(conteudo["flashcards"], list))
                exigir(isinstance(conteudo["questoes"], list))
                for card in conteudo["flashcards"]:
                    exigir(isinstance(card, list) and len(card) == 3)
                    exigir(texto_valido(card[0]) and texto_valido(card[1]))
                    exigir(isinstance(card[2], list) and len(card[2]) == 2)
                    exigir(all(inteiro_valido(n) for n in card[2]))
                for questao in conteudo["questoes"]:
                    exigir(isinstance(questao, list) and len(questao) == 3)
                    enunciado, alternativas, correta = questao
                    exigir(texto_valido(enunciado))
                    exigir(isinstance(alternativas, list) and len(alternativas) >= 2)
                    exigir(all(texto_valido(item) for item in alternativas))
                    exigir(inteiro_valido(correta) and correta < len(alternativas))
        campos = {"anotacoes": ("data", "materia", "topico", "texto"),
                  "simulados": ("data", "materia", "topico"),
                  "pesquisas": ("data", "termo", "titulo", "resumo", "url")}
        for colecao, chaves in campos.items():
            exigir(isinstance(perfil[colecao], list))
            for item in perfil[colecao]:
                exigir(isinstance(item, dict))
                exigir(all(texto_valido(item[c]) for c in chaves))
                datetime.fromisoformat(item["data"])
                if colecao == "simulados":
                    exigir(inteiro_valido(item["total"]) and inteiro_valido(item["acertos"]))
                    exigir(0 <= item["acertos"] <= item["total"] and item["total"] > 0)
    except (ValueError, KeyError, TypeError, IndexError) as erro:
        raise ValueError("Perfil inválido ou incompatível. Confira o formato dos registros.") from erro
    return perfil


def validar_banco(banco):
    try:
        exigir(isinstance(banco, dict) and type(banco["versao"]) is int and banco["versao"] == 2)
        exigir(isinstance(banco["usuarios"], dict))
        for usuario, conta in banco["usuarios"].items():
            exigir(re.fullmatch(r"[a-z0-9_]{3,30}", usuario))
            exigir(isinstance(conta, dict))
            exigir(re.fullmatch(r"[0-9a-f]{32}", conta["salt"]))
            exigir(re.fullmatch(r"[0-9a-f]{64}", conta["hash"]))
            validar_perfil(conta["perfil"])
    except (KeyError, TypeError) as erro:
        raise ValueError("Arquivo de usuários inválido. Nenhum dado foi substituído.") from erro
    return banco


def carregar_banco(caminho):
    try:
        with caminho.open(encoding="utf-8") as arquivo:
            return validar_banco(json.load(arquivo))
    except FileNotFoundError:
        return {"versao": 2, "usuarios": {}}


def hash_senha(senha, salt):
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt), ITERACOES).hex()


def cadastrar(banco, usuario, senha, caminho):
    if not re.fullmatch(r"[a-z0-9_]{3,30}", usuario):
        raise ValueError("Usuário: use 3 a 30 letras minúsculas, números ou sublinhado.")
    if usuario in banco["usuarios"]:
        raise ValueError("Esse usuário já está cadastrado.")
    if not 8 <= len(senha) <= 128 or not senha.strip():
        raise ValueError("A senha deve ter entre 8 e 128 caracteres e não ser só espaços.")
    salt = secrets.token_hex(16)
    novo = deepcopy(banco)
    novo["usuarios"][usuario] = {"salt": salt, "hash": hash_senha(senha, salt), "perfil": novo_perfil()}
    salvar_json(caminho, novo)
    banco.clear()
    banco.update(novo)


def autenticar(banco, usuario, senha):
    conta = banco["usuarios"].get(usuario)
    if conta is None or not 8 <= len(senha) <= 128:
        return False
    return hmac.compare_digest(conta["hash"], hash_senha(senha, conta["salt"]))


def login(banco, caminho):
    while True:
        print("\nJOVI V70 - SPRINT 4\n1. Entrar\n2. Criar conta\n0. Sair")
        opcao = ler_numero("Escolha: ", 0, 2)
        if opcao == 0:
            return None
        usuario = ler_texto("Usuário: ", 30).lower()
        senha = getpass("Senha (não aparece enquanto digita): ")
        if opcao == 1:
            if autenticar(banco, usuario, senha):
                print(f"Bem-vindo, {usuario}!")
                return usuario
            print("Usuário ou senha inválidos.")
        else:
            if senha != getpass("Confirme a senha: "):
                print("As senhas não coincidem.")
                continue
            try:
                cadastrar(banco, usuario, senha, caminho)
                print("Conta criada e salva. Agora entre com suas credenciais.")
            except (ValueError, OSError) as erro:
                print("Cadastro não concluído:", erro)


def escolher_topico(materias):
    lista = [(m, t) for m, topicos in materias.items() for t in topicos]
    print("\n0. Voltar ao menu")
    for i, (materia, topico) in enumerate(lista, 1):
        print(f"{i}. {materia}: {topico}")
    escolha = ler_numero("Tópico: ", 0, len(lista))
    return lista[escolha - 1] if escolha else None


def registrar_conteudo(perfil):
    escolha = escolher_topico(perfil["materias"])
    if escolha is None:
        return False
    materia, topico = escolha
    print("Registro manual do caderno; digite ou cole uma linha de texto.")
    texto = ler_texto("Conteúdo: ")
    perfil["anotacoes"].append({"data": agora(), "materia": materia, "topico": topico, "texto": texto})
    return True


def flashcards(perfil):
    escolha = escolher_topico(perfil["materias"])
    if escolha is None:
        return False
    materia, topico = escolha
    cards = perfil["materias"][materia][topico]["flashcards"]
    if not cards:
        print("Este tópico ainda não tem flashcards.")
        return False
    for pergunta, resposta, placar in cards:
        print("\nPergunta:", pergunta)
        input("ENTER para ver a resposta...")
        print("Resposta:", resposta)
        placar[0 if ler_confirmacao("Você acertou?") else 1] += 1
    acertos = sum(card[2][0] for card in cards)
    total = sum(sum(card[2]) for card in cards)
    print(f"Progresso acumulado: {acertos / total:.1%}" if total else "Sem tentativas.")
    return True


def simulado(perfil):
    escolha = escolher_topico(perfil["materias"])
    if escolha is None:
        return False
    materia, topico = escolha
    questoes = perfil["materias"][materia][topico]["questoes"]
    if not questoes:
        print("Este tópico ainda não tem questões.")
        return False
    acertos = 0
    for enunciado, alternativas, correta in questoes:
        print("\n" + enunciado)
        for i, alternativa in enumerate(alternativas):
            print(f"{i}. {alternativa}")
        resposta = ler_numero("Alternativa: ", 0, len(alternativas) - 1)
        if resposta == correta:
            acertos += 1
            print("Correto!")
        else:
            print("Resposta correta:", alternativas[correta])
    perfil["simulados"].append({"data": agora(), "materia": materia, "topico": topico,
                                "acertos": acertos, "total": len(questoes)})
    print(f"Resultado: {acertos}/{len(questoes)}")
    return True


def formatar_data(data):
    return datetime.fromisoformat(data).astimezone().strftime("%d/%m/%Y %H:%M")


def historico(perfil):
    print("\n===== PROGRESSO DOS FLASHCARDS =====")
    for materia, topicos in perfil["materias"].items():
        for topico, dados in topicos.items():
            print(f"\n{materia} - {topico}")
            for indice, (pergunta, _, placar) in enumerate(dados["flashcards"], 1):
                total = sum(placar)
                percentual = f"{placar[0] / total:.0%}" if total else "Sem tentativas"
                print(f"  {indice}. {pergunta}")
                print(f"     Acertos: {placar[0]} | Erros: {placar[1]} | {percentual}")
    for nome, titulo in (("anotacoes", "ANOTAÇÕES"), ("simulados", "SIMULADOS"),
                         ("pesquisas", "PESQUISAS SALVAS")):
        print(f"\n===== {titulo} ({len(perfil[nome])}) =====")
        if not perfil[nome]:
            print("Nenhum registro ainda.")
        for indice, item in enumerate(perfil[nome], 1):
            print(f"\n{indice}. {formatar_data(item['data'])}")
            if nome == "pesquisas":
                print(f"   {item['titulo']}\n{item['resumo']}\nFonte: {item['url']}")
            else:
                print(f"   {item['materia']} - {item['topico']}")
                if nome == "anotacoes":
                    print(item["texto"])
                else:
                    print(f"   Acertos: {item['acertos']}/{item['total']} ({item['acertos'] / item['total']:.0%})")
    return False


def exportar(perfil, usuario, caminho):
    salvar_json(caminho, {"sistema": "Jovi V70", "versao_integracao": 2,
                         "usuario": usuario, "exportado_em": agora(), "perfil": perfil})
    print("JSON exportado:", caminho)
    print("No site Jovi, entre e use Dados do Python > Importar JSON para visualizar este arquivo.")
    return False


def main():
    try:
        try:
            banco = carregar_banco(ARQUIVO_DADOS)
        except (ValueError, OSError) as erro:
            print("Não foi possível abrir os dados:", erro)
            print("Corrija o arquivo ou faça uma cópia e renomeie-o antes de reiniciar.")
            return
        usuario = login(banco, ARQUIVO_DADOS)
        if usuario is None:
            return
        destino = BASE / "integracao" / f"{usuario}.json"
        acoes = {1: registrar_conteudo, 2: flashcards, 3: simulado, 4: alternar_modo,
                 5: pesquisar, 6: historico, 7: lambda p: exportar(p, usuario, destino)}
        while True:
            print("\n===== MENU PRINCIPAL =====\n1. Registrar conteúdo\n2. Revisar flashcards")
            print("3. Realizar simulado\n4. Modo Estudo (simulação)\n5. Pesquisar na Wikipédia (API)")
            print("6. Histórico e progresso\n7. Exportar JSON para integração\n0. Sair")
            opcao = ler_numero("Escolha: ", 0, 7)
            if opcao == 0:
                print("Até logo! Operações confirmadas foram salvas.")
                return
            novo = deepcopy(banco)
            perfil = novo["usuarios"][usuario]["perfil"]
            try:
                if acoes[opcao](perfil):
                    validar_perfil(perfil)
                    salvar_json(ARQUIVO_DADOS, novo)
                    banco = novo
                    print("Dados salvos com sucesso.")
            except (OSError, ValueError) as erro:
                print("Operação não confirmada:", erro)
    except (EOFError, KeyboardInterrupt):
        print("\nEncerrado. Apenas operações já confirmadas permanecem salvas.")


if __name__ == "__main__":
    main()
