"""Read announced card Try API pages, retaining only public native examples."""
import datetime,hashlib,json,re,sys,time
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
run=Path(sys.argv[1]);out=[]
cards=json.loads((run/'nvidia-additional-cards.json').read_text())['models']
with httpx.Client(trust_env=False,follow_redirects=True,timeout=20) as client:
 for card in cards:
  url=card['source'].split('?')[0]+'/api';entry={'card_slug':card['card_slug'],'source':url,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
  try:
   response=client.get(url);entry['http_status']=response.status_code
   if response.status_code==200:
    soup=BeautifulSoup(response.text,'html.parser');codes=[v.get_text() for v in soup.find_all('code')];text=soup.get_text('\n',strip=True)
    entry.update(examples=codes,text_sha256=hashlib.sha256(text.encode()).hexdigest(),function_ids=sorted(set(re.findall(r'''function-id\s+["']?([a-f0-9-]{36})''','\n'.join(codes)))),reference_links=sorted({v['href'] for v in soup.find_all('a',href=True) if 'docs.api.nvidia.com' in v['href'] or 'github.com/nvidia-riva' in v['href']}))
  except Exception as error:entry['error']=type(error).__name__
  out.append(entry);tmp=run/'.nvidia-api-examples.tmp';tmp.write_text(json.dumps({'models':out},ensure_ascii=False,indent=2));tmp.replace(run/'nvidia-api-examples.json');print(card['card_slug'],entry.get('http_status'),len(entry.get('examples',[])),flush=True)
  if entry.get('http_status')==429:break
  time.sleep(1.5)
