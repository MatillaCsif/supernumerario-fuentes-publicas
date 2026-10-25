"""Public-source byte capture on standard GitHub runners. No keys or AI APIs."""
import json,hashlib,gzip,re,time,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit,urljoin
from portable_bocyl import parse_summary,selected,latest_summary_url

HOSTS={'empleopublico.jcyl.es','www.empleopublico.jcyl.es','bocyl.jcyl.es','analisis.datosabiertos.jcyl.es'}
def now():return datetime.now(timezone.utc).isoformat()
def allowed(url):
    p=urlsplit(url);return p.scheme=='https' and p.hostname in HOSTS and not p.username and p.port in (None,443)
def write(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
class Links(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a' and dict(attrs).get('href'):self.urls.append(dict(attrs)['href'])
class Watch:
    def __init__(self,root):
        self.root=Path(root);p=self.root/'catalog.json';self.catalog=json.loads(p.read_bytes()) if p.exists() else {'schema':1,'sources':{},'versions':{},'bocyl_days':{},'bocyl_cursor':None}
        self.size=sum(p.stat().st_size for p in (self.root/'objects').glob('*.gz'));self.errors=[];self.warnings=[];self.changed=0
        self.failures=self.catalog.setdefault('source_failures',{})
    def acquire(self,url,role):
        for attempt in range(3):
            try:return self.acquire_once(url,role)
            except urllib.error.HTTPError as exc:
                if exc.code<500 or attempt==2:raise
            except Exception:
                if attempt==2:raise
            time.sleep(.25*(attempt+1))
    def acquire_once(self,url,role):
        if not allowed(url):raise ValueError('Outside approved public hosts')
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'SUPERNUMERARIO-public-source-monitor/1.0','Accept-Encoding':'identity','Cache-Control':'no-cache'}),timeout=45) as r:
            if not allowed(r.url):raise ValueError('Redirect outside public source hosts')
            raw=r.read(50_000_001)
            if r.headers.get('Content-Length') and len(raw)!=int(r.headers['Content-Length']):raise ValueError('Truncated HTTP response: byte count differs')
        if len(raw)>50_000_000:raise ValueError('Original exceeds 50 MB capture bound')
        if urlsplit(url).path.lower().endswith('.pdf') and (not raw.lstrip().startswith(b'%PDF-') or b'%%EOF' not in raw[-8192:]):raise ValueError('Invalid or truncated PDF response')
        if role=='statistics.export' and not isinstance(json.loads(raw),list):raise ValueError('Invalid statistical export')
        digest=hashlib.sha256(raw).hexdigest();target=self.root/'objects'/(digest+'.gz');compressed=gzip.compress(raw,mtime=0)
        if not target.exists():
            if self.size+len(compressed)>256*1024*1024:raise ValueError('256 MB evidence cap reached; capture stopped without paid storage')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(compressed);self.size+=len(compressed)
        previous=self.catalog['sources'].get(url,{})
        if previous.get('sha256')!=digest:
            entry={'url':url,'role':role,'sha256':digest,'object':'objects/'+digest+'.gz','captured_at':now(),'size_bytes':len(raw)}
            self.catalog['sources'][url]=entry;self.catalog['versions'].setdefault(url,[]).append(entry);self.changed+=1
        self.failures.pop(url,None)
        return raw
    def commissions(self,seeds):
        queue=list(seeds);seen=set()
        while queue and len(seen)<300:
            item=queue.pop(0);url=item['url']
            if url in seen:continue
            seen.add(url)
            try:
                raw=self.acquire(url,item['role'])
                if item['role']=='commission.page':
                    links=Links();links.feed(raw.decode('utf-8',errors='replace'))
                    for href in links.urls:
                        target=urljoin(url,href)
                        if not allowed(target):continue
                        if re.search(r'\.(?:pdf|xlsx?|docx?|csv)(?:\?|$)',target,re.I):queue.append({'url':target,'role':'commission.document'})
                        elif any(s in target for s in ('PlantillaSimpleDetalle','SEDescargarTablaCombinada')):queue.append({'url':target,'role':'commission.page'})
            except Exception as exc:
                previous=self.catalog['sources'].get(url)
                retained=previous and (self.root/previous['object']).is_file()
                if retained:
                    try:
                        with gzip.open(self.root/previous['object'],'rb') as stream:cached=stream.read(50_000_001)
                        retained=len(cached)<=50_000_000 and hashlib.sha256(cached).hexdigest()==previous['sha256'] and len(cached)==previous['size_bytes']
                    except (OSError,EOFError):retained=False
                timeout=isinstance(exc,TimeoutError) or isinstance(exc,urllib.error.URLError) and not isinstance(exc,urllib.error.HTTPError) and 'timed out' in str(exc).lower()
                if timeout:self.failures[url]=self.failures.get(url,0)+1
                if isinstance(exc,urllib.error.HTTPError) and exc.code==404 and retained:
                    self.warnings.append({'url':url,'role':item['role'],'error':'HTTP 404; retained original is available, not a current successful fetch','retained_sha256':previous['sha256']})
                elif timeout and retained and self.failures[url]<3:
                    self.warnings.append({'url':url,'role':item['role'],'error':'Download timed out after retries; verified historical original retained. Current bytes were not checked.','retained_sha256':previous['sha256'],'last_successful_capture_at':previous['captured_at'],'current_fetch_verified':False,'consecutive_failed_runs':self.failures[url]})
                else:self.errors.append({'url':url,'role':item['role'],'error':str(exc)})
        if queue:self.errors.append({'scope':'commission','error':'Public-source discovery bound reached; pending URLs retained for review'})
    def bocyl(self):
        cursor=self.catalog['bocyl_cursor'];url=latest_summary_url(self.acquire('https://bocyl.jcyl.es/','bocyl.portal'));chain=[];seen=set();reached=False
        while url and len(chain)<62:
            if url in seen:raise ValueError('Archive navigation loop')
            seen.add(url);raw=self.acquire(url,'bocyl.summary');p=parse_summary(raw,url)
            if cursor and p.day<cursor:reached=True;break
            if not cursor and p.day<'2026-10-01':reached=True;break
            chain.append(p)
            if p.day==cursor or p.day=='2026-10-01':reached=True;break
            url=p.previous
        for p in reversed(chain):
            success=True
            for notice in p.rows.values():
                if not selected(notice):continue
                try:
                    self.acquire(notice['source_url'],'bocyl.notice.html');self.acquire(notice['pdf_url'],'bocyl.notice.pdf')
                except Exception as exc:success=False;self.errors.append({'url':notice['pdf_url'],'error':str(exc)})
            if p.edition_links:success=False;self.errors.append({'day':p.day,'error':'Additional editions require explicit archive check; cursor held'})
            self.catalog['bocyl_days'][p.day]={'capture_complete':success,'checked_at':now(),'previous_url':p.previous}
        if not reached:self.errors.append({'scope':'bocyl','error':'Earlier checkpoint not reached; no cursor advance'})
        if reached:
            for p in reversed(chain):
                if not self.catalog['bocyl_days'][p.day]['capture_complete']:break
                self.catalog['bocyl_cursor']=p.day
    def finish(self):
        stamp=now();write(self.root/'catalog.json',self.catalog)
        report={'checked_at':stamp,'changed_public_sources':self.changed,'status':'PARTIAL_ERROR' if self.errors else ('COMPLETE_WITH_WARNINGS' if self.warnings else 'COMPLETE'),'errors':self.errors,'warnings':self.warnings,'bocyl_capture_cursor':self.catalog['bocyl_cursor'],
            'public_source_urls':len(self.catalog['sources']),'stored_compressed_bytes':self.size,'capture_is_not_legal_validation':True,'paid_services_used':False}
        write(self.root/'status.json',report);write(self.root/'reports'/(stamp[:10]+'.json'),report)
        print(json.dumps({k:v for k,v in report.items() if k!='errors'}));return 1 if self.errors else 0
def main():
    w=Watch('data');seeds=json.loads(Path('sources.json').read_bytes());w.commissions(seeds)
    try:w.bocyl()
    except Exception as exc:w.errors.append({'scope':'bocyl','error':str(exc)})
    return w.finish()
if __name__=='__main__':raise SystemExit(main())
