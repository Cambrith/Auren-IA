"""Refresh historical primary-source links without reusing old numeric claims."""
import concurrent.futures,hashlib,json,sys,threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx
ROOT=Path(__file__).resolve().parents[1]
def main():
 run=Path(sys.argv[1]);old=json.loads((ROOT/'reports/AUREN-BENCHMARKS-INVENTARIO-2026-10-13.json').read_text());by={r['source'] for r in old['routes'] if str(r.get('source','')).startswith('https://')};output=run/'source-refresh.json';data=json.loads(output.read_text()) if output.exists() else {'checked_at':datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),'method':'HTTP/source freshness only. No score inherited or automatically certified.','sources':{}};lock=threading.Lock()
 def fetch(url):
  if url in data['sources']:return
  row={'source':url}
  try:
   with httpx.Client(trust_env=False,timeout=15,follow_redirects=True) as client:
    response=client.get(url);row.update(http_status=response.status_code,final_url=str(response.url),body_sha256=hashlib.sha256(response.content).hexdigest(),bytes=len(response.content),benchmark_numeric_review=False)
  except Exception as error:row['error']=type(error).__name__
  with lock:
   data['sources'][url]=row;temp=output.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2));temp.replace(output)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(fetch,sorted(by)))
 print('Refreshed source links',len(data['sources']))
if __name__=='__main__':main()
