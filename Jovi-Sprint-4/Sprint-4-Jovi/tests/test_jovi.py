import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError, HTTPError
import jovi
from consumidor_integracao import gerar_relatorio


class TestJovi(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'jovi.json'
        self.banco = jovi.carregar_banco(self.path)

    def test_cadastro_login_persistencia_isolamento(self):
        for user in ('aluno1', 'aluno2'):
            jovi.cadastrar(self.banco, user, 'teste1234', self.path)
        self.assertTrue(jovi.autenticar(jovi.carregar_banco(self.path), 'aluno1', 'teste1234'))
        self.assertFalse(jovi.autenticar(self.banco, 'aluno1', 'errada123'))
        self.assertNotIn('teste1234', self.path.read_text())
        self.assertNotEqual(self.banco['usuarios']['aluno1']['hash'], self.banco['usuarios']['aluno2']['hash'])
        self.banco['usuarios']['aluno1']['perfil']['materias']['Física']['Leis de Newton']['flashcards'][0][2][0] += 1
        self.assertEqual(self.banco['usuarios']['aluno2']['perfil']['materias']['Física']['Leis de Newton']['flashcards'][0][2], [0, 0])

    def test_cadastro_invalido_e_duplicado(self):
        for user, senha in [('x', 'teste1234'), ('aluno', '123')]:
            with self.assertRaises(ValueError):
                jovi.cadastrar(self.banco, user, senha, self.path)
        jovi.cadastrar(self.banco, 'aluno', 'teste1234', self.path)
        with self.assertRaises(ValueError):
            jovi.cadastrar(self.banco, 'aluno', 'outrasenha', self.path)

    def test_corrupcao_preservada(self):
        for conteudo in ('{quebrado', '{"versao":2,"usuarios":[]}'):
            self.path.write_text(conteudo)
            with self.assertRaises(ValueError):
                jovi.carregar_banco(self.path)
            self.assertEqual(self.path.read_text(), conteudo)

    def test_falha_gravacao(self):
        jovi.salvar_json(self.path, self.banco)
        antes = self.path.read_bytes()
        with patch('jovi.os.replace', side_effect=PermissionError()):
            with self.assertRaises(OSError):
                jovi.cadastrar(self.banco, 'aluno', 'teste1234', self.path)
        self.assertEqual(self.path.read_bytes(), antes)
        self.assertEqual(self.banco['usuarios'], {})

    def test_fluxo_menu_e_reabertura(self):
        jovi.cadastrar(self.banco, 'aluno', 'teste1234', self.path)
        entradas = ['1','aluno','1','1','Conteúdo de teste','2','1','','s','3','1','1','4','0']
        with patch('jovi.ARQUIVO_DADOS', self.path), patch('builtins.input', side_effect=entradas), patch('jovi.getpass', return_value='teste1234'), redirect_stdout(io.StringIO()) as tela:
            jovi.main()
        self.assertEqual(tela.getvalue().count('MENU PRINCIPAL'), 5)
        perfil = jovi.carregar_banco(self.path)['usuarios']['aluno']['perfil']
        self.assertEqual(perfil['anotacoes'][0]['texto'], 'Conteúdo de teste')
        self.assertEqual(perfil['materias']['Matemática']['Geometria Plana']['flashcards'][0][2], [1, 0])
        self.assertEqual(perfil['simulados'][0]['acertos'], 1)
        self.assertTrue(perfil['modo_estudo'])

    def test_api_sucesso(self):
        respostas = [{'query': {'search': [{'pageid': 42}]}}, {'query': {'pages': [{'title': 'Geometria', 'extract': 'Formas geométricas.'}]}}]
        with patch('jovi.urlopen', side_effect=[io.BytesIO(json.dumps(r).encode()) for r in respostas]) as req:
            artigo = jovi.buscar_artigo('geometria plana')
        self.assertIn('srsearch=geometria+plana', req.call_args_list[0].args[0].full_url)
        self.assertEqual(artigo['resumo'], 'Formas geométricas.')

    def test_api_falhas(self):
        for erro in [URLError('offline'), TimeoutError(), ValueError(), KeyError(), HTTPError(jovi.API_URL, 429, 'limite', {}, None)]:
            with self.subTest(erro=erro), patch('jovi.buscar_artigo', side_effect=erro), patch('builtins.input', return_value='física'), redirect_stdout(io.StringIO()):
                perfil = jovi.novo_perfil()
                self.assertFalse(jovi.pesquisar(perfil))
                self.assertEqual(perfil['pesquisas'], [])

    def test_exportacao_consumidor_sem_credenciais(self):
        perfil = jovi.novo_perfil()
        with redirect_stdout(io.StringIO()):
            jovi.exportar(perfil, 'aluno', self.path)
        pacote = json.loads(self.path.read_text())
        self.assertNotIn('hash', pacote)
        self.assertEqual(set(pacote), {'sistema','versao_integracao','usuario','exportado_em','perfil'})
        relatorio = gerar_relatorio(self.path)
        self.assertIn('Usuário: aluno', relatorio.read_text())

    def test_validacao_e_cancelamento(self):
        with patch('builtins.input', side_effect=['abc','9','2']), redirect_stdout(io.StringIO()):
            self.assertEqual(jovi.ler_numero('?',0,7), 2)
        with patch('builtins.input', side_effect=['talvez','n']), redirect_stdout(io.StringIO()):
            self.assertFalse(jovi.ler_confirmacao('?'))
        with patch('builtins.input', return_value='0'), redirect_stdout(io.StringIO()):
            self.assertFalse(jovi.flashcards(jovi.novo_perfil()))

    def test_pesquisa_salva_offline(self):
        perfil = jovi.novo_perfil()
        artigo = {'data':jovi.agora(),'termo':'geometria','titulo':'Geometria','resumo':'Formas.','url':'https://pt.wikipedia.org/?curid=42'}
        with patch('jovi.buscar_artigo', return_value=artigo), patch('builtins.input', side_effect=['geometria','s']), redirect_stdout(io.StringIO()):
            self.assertTrue(jovi.pesquisar(perfil))
        jovi.salvar_json(self.path, perfil)
        with patch('jovi.urlopen', side_effect=AssertionError()), redirect_stdout(io.StringIO()) as tela:
            jovi.historico(jovi.validar_perfil(json.loads(self.path.read_text())))
        self.assertIn('Formas.', tela.getvalue())


class TestEvolucao(unittest.TestCase):
    def test_conteudo_alterado_e_materia_nova(self):
        perfil = jovi.novo_perfil()
        perfil['materias']['Matemática']['Geometria Plana']['flashcards'][0][0] = 'Pergunta revisada'
        perfil['materias']['Biologia'] = {'Células': {'flashcards': [['O que é uma célula?', 'Unidade básica da vida.', [3, 1]]], 'questoes': [['Qual é uma célula?', ['Neurônio', 'Água'], 0]]}}
        self.assertIs(jovi.validar_perfil(perfil), perfil)

    def test_questao_e_placar_invalidos(self):
        for valor in [-1, True, '1']:
            perfil = jovi.novo_perfil()
            perfil['materias']['Física']['Leis de Newton']['flashcards'][0][2][0] = valor
            with self.assertRaises(ValueError):
                jovi.validar_perfil(perfil)
        perfil = jovi.novo_perfil()
        perfil['materias']['Física']['Leis de Newton']['questoes'][0][2] = 99
        with self.assertRaises(ValueError):
            jovi.validar_perfil(perfil)

    def test_historico_de_topico_removido_e_data_invalida(self):
        perfil = jovi.novo_perfil()
        perfil['anotacoes'].append({'data':jovi.agora(),'materia':'Antiga','topico':'Arquivado','texto':'Preservar histórico'})
        jovi.validar_perfil(perfil)
        perfil['anotacoes'][0]['data'] = 'data inválida'
        with self.assertRaises(ValueError):
            jovi.validar_perfil(perfil)

    def test_topicos_sem_conteudo(self):
        perfil = jovi.novo_perfil()
        dados = perfil['materias']['Matemática']['Geometria Plana']
        dados['flashcards'] = []
        dados['questoes'] = []
        with patch('builtins.input', return_value='1'), redirect_stdout(io.StringIO()):
            self.assertFalse(jovi.flashcards(perfil))
            self.assertFalse(jovi.simulado(perfil))


if __name__ == '__main__':
    unittest.main()
