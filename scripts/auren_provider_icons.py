"""Fetch only publicly declared brand assets from official provider sites, never credentials."""
import hashlib
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit
import xml.etree.ElementTree as ET
import httpx

ROOT=Path(__file__).resolve().parents[1]
SITES={
 'aihorde':'https://aihorde.net/','bedrock':'https://aws.amazon.com/bedrock/',
 'anthropic':'https://www.anthropic.com/','assemblyai':'https://www.assemblyai.com/',
 'canva':'https://www.canva.dev/','cartesia':'https://cartesia.ai/',
 'cerebras':'https://www.cerebras.ai/','cloudflare':'https://www.cloudflare.com/',
 'cohere':'https://cohere.com/','deepgram':'https://deepgram.com/',
 'deepinfra':'https://deepinfra.com/','deepseek':'https://www.deepseek.com/',
 'elevenlabs':'https://elevenlabs.io/','fal':'https://fal.ai/',
 'fireworks':'https://fireworks.ai/','gemini':'https://gemini.google.com/',
 'groq':'https://groq.com/','huggingface':'https://huggingface.co/',
 'hyperbolic':'https://www.hyperbolic.ai/','mistral':'https://mistral.ai/',
 'nvidia':'https://www.nvidia.com/','novita':'https://novita.ai/',
 'ollama':'https://ollama.com/','openai':'https://openai.com/',
 'openrouter':'https://openrouter.ai/','replicate':'https://replicate.com/',
 'stability':'https://stability.ai/','voyage':'https://www.voyageai.com/',
 'xai':'https://x.ai/','zai':'https://z.ai/',
}

class Assets(HTMLParser):
    def __init__(self,provider):super().__init__();self.candidates=[];self.provider=provider
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);src=a.get('href' if tag=='link' else 'src','')
        rel=a.get('rel','').lower();alt=a.get('alt','').lower()
        if tag=='link' and 'icon' in rel and src:
            score=0 if '.svg' in src else 2 if 'apple' in rel else 3
            if 'mask' in rel:score+=10
            self.candidates.append((score,src))
        elif tag=='img' and 'logo' in alt and self.provider in re.sub(r'[^a-z0-9]','',alt) and src:
            self.candidates.append((5 if '.svg' in src else 6,src))

def safe_svg(data):
    if re.search(rb'<!DOCTYPE|<!ENTITY',data,re.I):return False
    try:root=ET.fromstring(data)
    except ET.ParseError:return False
    if root.tag.split('}')[-1]!='svg':return False
    for node in root.iter():
        if node.tag.split('}')[-1] in ('script','foreignObject','image','iframe'):return False
        if node.tag.split('}')[-1]=='style' and re.search(r'@import|url\(\s*["\']?(?!#)',node.text or '',re.I):return False
        for attr,value in node.attrib.items():
            if attr.lower().startswith('on'):return False
            if attr.split('}')[-1] in ('href','src') and not value.startswith('#'):return False
            if re.search(r'url\(\s*["\']?(?!#)',value):return False
    return True

def fetch(provider,site):
    with httpx.Client(trust_env=False,timeout=15,follow_redirects=True) as client:
        try:
            page=client.get(site);page.raise_for_status();parser=Assets(provider);parser.feed(page.text)
            candidates=sorted(parser.candidates)+[(20,'/favicon.ico')]
            for score,src in candidates[:12]:
                url=urljoin(str(page.url),src)
                if urlsplit(url).scheme!='https' or urlsplit(url).username:continue
                try:
                    result=client.get(url)
                    if result.status_code!=200 or not 40<len(result.content)<500_000:continue
                    data=result.content
                    svg=b'<svg' in data[:2000] or 'svg' in result.headers.get('content-type','')
                    if svg:
                        if not safe_svg(data):continue
                        ext='svg'
                        dark=bool(re.search(rb'(?:fill|stroke)=["\'](?:white|#fff(?:fff)?)["\']',data,re.I)) and not bool(re.search(rb'(?:fill|stroke)=["\'](?:black|#000(?:000)?)["\']',data,re.I))
                    else:
                        from PIL import Image
                        im=Image.open(io.BytesIO(data)).convert('RGBA')
                        if min(im.size)<16:continue
                        im.thumbnail((256,256));buf=io.BytesIO();im.save(buf,format='PNG');data=buf.getvalue();ext='png';dark=False
                    path=ROOT/'static/brand-icons/providers'/f'{provider}.{ext}'
                    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
                    return provider,{'file':f'providers/{provider}.{ext}','source_page':str(page.url),'source':str(result.url),
                        'sha256':hashlib.sha256(data).hexdigest(),'official':True,'dark_surface':dark,
                        'asset_kind':'declared_site_icon' if score in (0,2,3,10,12,13,20) else 'declared_logo'}
                except Exception:continue
        except Exception:pass
    for ext in ('svg','png'):
        path=ROOT/'static/brand-icons'/f'{provider}.{ext}'
        if path.exists():return provider,{'file':path.name,'official':False,'fallback':'existing_attributed_asset','dark_surface':False,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    return provider,{'file':None,'official':False,'fallback':'initials','dark_surface':False}

def main():
    with ThreadPoolExecutor(max_workers=6) as pool:items=dict(pool.map(lambda x:fetch(*x),SITES.items()))
    (ROOT/'static/brand-icons/provider-sources.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
    entries={id:{'src':'/brand-icons/'+v['file'] if v['file'] else '', 'darkSurface':v['dark_surface']} for id,v in items.items()}
    (ROOT/'src/lib/utils/providerIcons.ts').write_text('/** Public official assets; provenance in static/brand-icons/provider-sources.json. */\nexport const providerIcons: Record<string, { src: string; darkSurface: boolean }> = '+json.dumps(entries,indent=2)+';\n')
    print(json.dumps({'providers':len(items),'official':sum(v['official'] for v in items.values()),'fallbacks':[id for id,v in items.items() if not v['official']]}))

if __name__=='__main__':main()
