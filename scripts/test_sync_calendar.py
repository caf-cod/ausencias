import unittest
from sync_calendar import parse_document, compile_docs, discover
class CalendarTests(unittest.TestCase):
 def test_recess_cross_year(self):
  doc=parse_document('<h1>Recesso federal 2026</h1><p>Períodos de 21 a 25 de dezembro de 2026 e de 28 de dezembro de 2026 a 1º de janeiro de 2027.</p>','https://www.gov.br/gestao/recesso')
  self.assertEqual(doc['periods'][1]['end'],'2027-01-01')
 def test_reject_partial_calendar(self):
  with self.assertRaises(ValueError):parse_document('<h1>Feriados 2027</h1><p>1 de janeiro, Ano Novo (feriado nacional)</p>','https://www.gov.br/gestao/feriados')
 def test_reject_incomplete_recess(self):
  with self.assertRaises(ValueError):parse_document('<h1>Recesso 2027</h1><p>Períodos serão publicados.</p>','https://www.gov.br/gestao/recesso')
 def test_transfer(self):
  url='https://www.gov.br/gestao/2026/outubro/transferencia'
  doc=parse_document('<h1>Ponto facultativo do Dia do Servidor Público será transferido</h1><p>Será transferido para esta sexta-feira, 30 de outubro de 2026.</p>',url)
  self.assertEqual(doc['date'],'2026-10-30')
  base={'type':'calendar','published':'2025-12-30','year':2026,'url':'base','entries':[{'date':'2026-10-28','name':'Dia do Servidor Público','kind':'Ponto facultativo federal'}]}
  doc['published']='2026-10-27'
  years,_=compile_docs({'base':base,url:doc});self.assertEqual(years['2026']['entries'][0]['date'],'2026-10-30')
 def test_allowlisted_discovery(self):
  urls=discover('<a href="https://evil.example/recesso">Recesso</a><a href="https://www.gov.br/gestao/2027/feriados">Feriados</a>','https://www.gov.br/gestao/')
  self.assertEqual(urls,['https://www.gov.br/gestao/2027/feriados'])
if __name__=='__main__':unittest.main()
