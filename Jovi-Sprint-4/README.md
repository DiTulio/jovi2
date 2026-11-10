# Jovi V70 + Python - Sprint 4

Projeto integrado de Computational Thinking with Python. O site apresenta o protótipo do Jovi e o programa Python complementa os estudos com persistência, API e exportação de dados para a interface web.

## Integrantes
| Nome | RM |
|---|---|
| Vinicius Di Tulio Gomes Silva | 573019 |
| Lucas Zarantonelli Lourenço | 569164 |
| Felipe Romano de Paula Souza | 571653 |
| Nicole Barbosa Oliveira de Lima | 569505 |
| Ryan Romagnoli Santos | 568845 |

## Organização para o GitHub
Use **um único repositório com duas pastas separadas**:

- `Jovi-V70-main/`: site HTML, CSS e JavaScript, incluindo importação de JSON.
- `Sprint-4-Jovi/`: programa Python e testes.
- `exemplos/`: exportação fictícia para testar a integração.
- `index.html`: encaminha a página inicial para o site.
- `.gitignore`: evita incluir senhas derivadas, dados pessoais e arquivos temporários gerados.

Extraia o ZIP e envie **o conteúdo da pasta Jovi-Sprint-4 para a raiz do repositório**. Envie os arquivos e as duas pastas, não apenas o ZIP. Não é necessário colocar os arquivos Python dentro da pasta do site.

O GitHub guarda os arquivos de ambos. O GitHub Pages serve o site estático; **não executa Python**. O Python é executado no computador e o JSON é importado manualmente no site. A publicação pelo Pages pode usar a raiz do repositório, pois o index.html da raiz encaminha para Jovi-V70-main/.

## Executar o Python
No terminal, dentro de `Sprint-4-Jovi`, execute:

```bash
python jovi.py
```

Requer Python 3.10+. Crie uma conta na opção 2 e entre pela opção 1. Não há senha padrão no Python. Em terminais Windows, `py jovi.py` também pode ser usado. A senha não aparece enquanto é digitada.

Realize atividades e use **7 - Exportar JSON para integração**. O arquivo será criado em `Sprint-4-Jovi/integracao/SEU_USUARIO.json`. Dados de contas permanecem em `Sprint-4-Jovi/dados/jovi_v2.json`; não envie esse banco ao GitHub.

## Abrir o site e importar
Abra `Jovi-V70-main/index.html` no navegador. Para testar com um endereço local estável, execute na raiz deste projeto:

```bash
python -m http.server 8000
```

Acesse `http://localhost:8000/Jovi-V70-main/`.

1. Entre no protótipo web com **aluno / 1234**. Este é o login demonstrativo do site.
2. No início, use **Dados do Python → Importar JSON**.
3. Selecione o arquivo exportado pela opção 7 do Python.
4. Confira usuário, data da exportação, placares por flashcard, simulados, anotações e pesquisas.
5. Para atualizar os dados, exporte novamente no Python e importe o novo arquivo.

O JSON vem diretamente do Python e é lido pela interface principal do Jovi: esta é a integração por arquivos exigida pelo enunciado. O site não acessa automaticamente a pasta local do Python.

## O que é sincronizado
Fluxo **Python → JSON → Jovi**, somente para consulta. O painel tem registros paginados de 10 em 10. A cópia importada é guardada no armazenamento local do navegador, quando permitido. O botão Remover cópia apaga somente essa cópia, sem alterar o JSON nem o banco do Python. Uma nova importação substitui a anterior; não soma registros e não mistura perfis.

As contas não são sincronizadas. O usuário mostrado no painel é o do arquivo exportado, e não o login demonstrativo do site. Os dados importados não substituem as atividades e os indicadores fictícios das telas originais. Exercícios realizados no site não voltam para o Python. Esta direção única já demonstra a integração por arquivos; não há API local de sincronização.

## Validação e privacidade
O site aceita apenas o contrato v2, com no máximo 5 MB. Valida a estrutura antes de trocar os dados atuais. Um arquivo inválido exibe mensagem e preserva a importação anterior. Textos são exibidos como texto, sem executar HTML; links de pesquisas só são habilitados para HTTPS na Wikipédia em português.

A exportação não inclui senha, hash, salt nem outras contas. Ela contém anotações e histórico do usuário: evite publicar arquivos pessoais. O armazenamento no navegador é local, não criptografado; em computador compartilhado, use Remover cópia ao terminar.

## Testar com exemplo
Use `exemplos/demonstracao.json`. É um arquivo **fictício**, gerado pelo exportador Python, com placar 3/1 (75%), um simulado 1/1 e uma anotação identificada como demonstração. Não contém pesquisas fingindo ser resultados de API.

## Persistência, API e limitações
O Python salva dados em JSON após cada operação confirmada e recupera ao reabrir. Pesquisa na API da Wikipédia com tratamento de erros e permite salvar a introdução para consulta offline. O uso de funções, parâmetros, retorno, listas/dicionários e try/except é mantido.

Câmera IA, bloqueio de aplicativos e outros elementos do protótipo continuam simulados. O site não possui autenticação de produção. Não há necessidade de servidor Python para a importação manual; apenas a pesquisa online do Python exige internet.

## Verificação
Na pasta Sprint-4-Jovi:

```bash
python -m unittest discover -s tests -v
```

São 14 testes de Python, incluindo persistência, login, isolamento de contas, erros, evolução do catálogo e integração por JSON. O teste JavaScript executa os manipuladores de importação e exibição com um DOM simulado: verifica o JSON gerado pelo Python, dados inválidos, placares, tamanho máximo, preservação após erro, armazenamento, paginação e remoção. Na raiz, execute `node Jovi-V70-main/tests/test_integracao.cjs` (Node.js necessário apenas para esse teste). A conferência visual em navegador deve seguir o roteiro de importação acima; o navegador automatizado deste ambiente não pôde acessar o servidor local.

O código-fonte não contém comentários nem docstrings. A documentação acadêmica específica de Python (PDF e README da disciplina) está somente no pacote separado Sprint-4-Python-Entrega.zip. Este repositório mantém as instruções gerais de execução e integração do Jovi.
