"""Extract bounded calendar data from official HTML; never guess an official date."""
import concurrent.futures, datetime as dt, hashlib, html, json, os, re, unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MONTHS = {n:i+1 for i,n in enumerate('janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro'.split())}
SEEDS = [
 'https://agenciagov.ebc.com.br/noticias/202512/confira-o-calendario-oficial-de-feriados-nacionais-e-pontos-facultativos-em-2026',
 'https://www.gov.br/gestao/pt-br/assuntos/noticias/2026/outubro/ponto-facultativo-do-dia-do-servidor-publico-sera-transferido-para-30-de-outubro',
 'https://www.gov.br/gestao/pt-br/assuntos/editoria-defeso-eleitoral/portaria-do-mgi-orienta-sobre-o-recesso-de-fim-de-ano-de-2026-no-servico-publico-federal',
]
def norm(s):
 return ''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn')
def allowed(url):
 p=urlparse(url)
 return p.scheme=='https' and ((p.hostname=='www.gov.br' and p.path.startswith('/gestao/')) or p.hostname=='agenciagov.ebc.com.br')
def fetch(url):
 if not allowed(url): raise ValueError('Fonte fora da lista permitida')
 with urlopen(Request(url,headers={'User-Agent':'CAF-Calendario/1.0'}),timeout=25) as r:
  if not allowed(r.url): raise ValueError('Redirecionamento fora das fontes oficiais')
  data=r.read(3_000_001)
  if len(data)>3_000_000: raise ValueError('Documento excessivamente grande')
  return data.decode('utf-8')
def plain(s):
 s=re.sub(r'<(script|style)\b[^>]*>.*?</\1>','',s,flags=re.S|re.I)
 s=re.sub(r'</(?:p|li|h[1-6]|tr|div)>|<br\s*/?>','\n',s,flags=re.I)
 s=html.unescape(re.sub('<[^>]+>',' ',s))
 return '\n'.join(' '.join(line.split()) for line in s.splitlines() if line.strip())
def title_of(s):
 match=re.search(r'<h1\b[^>]*>(.*?)</h1>',s,re.S|re.I)
 return plain(match[1]) if match else ''
def article_body(s):
 # Avoid navigation/footer text being interpreted as part of a publication.
 for marker in ['id="content-core"','class="documentDescription"','id="parent-fieldname-text"']:
  if marker in s:
   return s[s.index(marker):].split('<footer',1)[0]
 return s

def parse_document(s,url):
 title=title_of(s); nt=norm(title)
 if not any(w in nt for w in ['feriado','facultativo','recesso']): raise ValueError('Título não identifica calendário ou recesso')
 body=plain(article_body(s)); text=norm(body)
 years=re.findall(r'\b20\d{2}\b',title)
 if not years and 'transferid' in nt: years=re.findall(r'/(20\d{2})/',url)
 if not years: raise ValueError('Ano ausente no título: revisão necessária')
 year=int(years[0]); result={'url':url,'title':title,'year':year,'hash':hashlib.sha256(s.encode()).hexdigest()}
 # Prefer machine-readable publication date, then visible Brazilian date.
 pub=re.search(r'(?:datePublished["\s:]+|property="article:published_time" content="|name="DC.date.created" content=")([0-9T:+.Z-]+)',s)
 visible=re.search(r'Publicado em\s+(\d{2})/(\d{2})/(\d{4})',body)
 result['published']=pub[1][:10] if pub else (f'{visible[3]}-{visible[2]}-{visible[1]}' if visible else '0000-00-00')
 entries=[]
 for line in body.splitlines():
  n=norm(line)
  if not ('feriado nacional' in n or 'ponto facultativo' in n): continue
  m=re.match(r'^\s*(?:[-–•]|[IVXLCDM]+\s*[-–])?\s*(\d{1,2})(?:o|º|°)?\s+de\s+(\w+)\b(.*)$',n)
  if not m or m[2] not in MONTHS: continue
  day=int(m[1]); month=MONTHS[m[2]]
  value=dt.date(year,month,day).isoformat()
  # Original human-readable label, excluding weekday and category parentheses.
  label=re.sub(r'^.*?de\s+\w+\s*(?:\([^)]*\))?\s*[,–-]?\s*','',line,count=1,flags=re.I)
  label=re.sub(r'\([^)]*(?:feriado nacional|ponto facultativo)[^)]*\)[.;]?\s*$','',label,flags=re.I).strip(' ;,.')
  kind='Feriado nacional' if 'feriado nacional' in n else 'Ponto facultativo federal'
  partial=re.search(r'(ate|apos)\s+as?\s+(\d{1,2})\s*(?:h|horas)',n)
  if partial: label+=' — '+('até' if partial[1]=='ate' else 'após')+' as '+partial[2]+'h'
  entries.append({'date':value,'name':label or kind,'kind':kind,'automatic':True,'source':url})
 if entries:
  # Accept only a full annual federal list; partial news cannot replace a year.
  unique={(e['date'],e['kind']):e for e in entries}
  entries=list(unique.values())
  nationals=[e for e in entries if e['kind']=='Feriado nacional']
  if len(nationals)>=9 and len(entries)>=14 and any(e['date'].endswith('-01-01') for e in entries) and any(e['date'].endswith('-12-25') for e in entries):
   result.update(type='calendar',entries=entries); return result
 # Recognize the explicitly reported transfer of the federal public servant day.
 if 'servidor publico' in nt and 'transferid' in nt:
  m=re.search(r'transferid[ao].{0,100}?(\d{1,2})\s+de\s+(\w+)\s+(?:de\s+)?(20\d{2})',text)
  if m and m[2] in MONTHS and int(m[3])==year:
   result.update(type='transfer',date=dt.date(year,MONTHS[m[2]],int(m[1])).isoformat());return result
 if 'recesso' in nt:
  # Strict, explicit two-period sentence; cross-year ending must include the year.
  m=re.search(r'periodos de (\d{1,2}) a (\d{1,2}) de dezembro de (20\d{2}) e de (\d{1,2}) de dezembro de (20\d{2}) a (\d{1,2})(?:o|º)? de janeiro de (20\d{2})',text)
  if m:
   a,b,y,c,y2,d,y3=map(int,m.groups())
   if y==year and y2==y and y3==y+1:
    result.update(type='recess',periods=[{'start':dt.date(y,12,a).isoformat(),'end':dt.date(y,12,b).isoformat(),'name':'Recesso de Natal'},{'start':dt.date(y,12,c).isoformat(),'end':dt.date(y3,1,d).isoformat(),'name':'Recesso de Ano Novo'}])
    if all(p['start']<=p['end'] and (dt.date.fromisoformat(p['end'])-dt.date.fromisoformat(p['start'])).days<15 for p in result['periods']):return result
 raise ValueError('Texto não corresponde a um formato validado; mantida a versão anterior')

def discover(s,base):
 urls=[]
 for href,label in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',s,re.I|re.S):
  url=urljoin(base,html.unescape(href)).split('#')[0].split('?')[0]
  title=norm(plain(label)+' '+url.rsplit('/',1)[-1])
  if allowed(url) and any(w in title for w in ['recesso','feriados','ponto-facultativo','pontos-facultativos']) and '/@@' not in url and not url.endswith(('.pdf','/RSS')):urls.append(url)
 return sorted(set(urls))
def compile_docs(documents):
 years={};recess={}
 for doc in sorted(documents.values(),key=lambda d:(d['published'],d['url'])):
  year=str(doc['year'])
  if doc['type']=='calendar': years[year]={'entries':doc['entries'],'source':doc['url'],'published':doc['published']}
  elif doc['type']=='recess':recess[year]={'periods':doc['periods'],'source':doc['url'],'published':doc['published']}
  elif doc['type']=='transfer' and year in years:
   entries=years[year]['entries']; targets=[e for e in entries if 'servidor publico' in norm(e['name'])]
   if len(targets)!=1:continue
   years[year]['entries']=[dict(e,date=doc['date'],source=doc['url']) if 'servidor publico' in norm(e['name']) else e for e in entries]
 for payload in years.values():payload['entries']=sorted(payload['entries'],key=lambda e:(e['date'],e['name']))
 return years,recess

def main():
 path=ROOT/'dados/calendario-federal.json';path.parent.mkdir(parents=True,exist_ok=True)
 old=json.loads(path.read_text()) if path.exists() else {};documents=old.get('documents',{});errors=[];urls=set(SEEDS)
 listings=['https://www.gov.br/gestao/pt-br/assuntos/noticias?b_start:int='+str(n) for n in (0,30,60)]
 listings+=['https://www.gov.br/gestao/pt-br/assuntos/editoria-defeso-eleitoral','https://agenciagov.ebc.com.br/']
 for url in listings:
  try:urls.update(discover(fetch(url),url))
  except Exception as exc:errors.append({'source':url,'reason':str(exc)})
 def process(url):
  try:return url,parse_document(fetch(url),url),None
  except Exception as exc:return url,None,str(exc)
 # Re-read previously accepted publications, plus bounded current discovery.
 urls.update(documents)
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
  for url,doc,error in pool.map(process,sorted(urls)[:60]):
   if doc:documents[url]=doc
   else:errors.append({'source':url,'reason':error})
 years,recess=compile_docs(documents)
 now=dt.datetime.now(dt.timezone.utc).isoformat()
 result={'version':1,'checkedAt':now,'years':years,'recess':recess,'documents':documents,'review':errors,'discovery':'Notícias recentes do MGI (até 3 páginas), Agência Gov e fontes já conhecidas. Não abrange todo o DOU.'}
 # Preserve prior accepted publications on network/parse errors; no blank overwrite.
 path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 summary=f'Consulta: {now}\nAnos com calendário validado: {", ".join(years) or "nenhum"}\nRecessos validados: {", ".join(recess) or "nenhum"}\nOcorrências para revisão: {len(errors)}\n'
 if os.getenv('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(summary+'\n'+ '\n'.join('- '+e['source']+' — '+e['reason'] for e in errors))
 print(summary)
 if not documents:raise SystemExit('Nenhuma fonte validada; consulte o relatório antes de publicar.')
if __name__=='__main__':main()
