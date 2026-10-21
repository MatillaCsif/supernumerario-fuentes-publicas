import re
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit,parse_qs
from scope_policy import exclusion_reason,fold
BASE="https://bocyl.jcyl.es/"

class Summary(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.tag=None;self.buf=[];self.issuer='';self.major='';self.section='';self.title='';self.rows={};self.previous=None;self.heading='';self.day=None;self.edition_links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('h2','h3','h4','h5','p'):self.tag=tag;self.buf=[]
        if tag=='a':
            url=urljoin(BASE,a.get('href',''));p=urlsplit(url)
            if p.scheme!='https' or p.hostname!='bocyl.jcyl.es':return
            if a.get('class')=='anterior':self.previous=url
            if 'edicion=' in p.query and 'fechaBoletin=' in p.query:self.edition_links.append(url)
            m=re.fullmatch(r'/boletines/(\d{4})/(\d{2})/(\d{2})/pdf/(BOCYL-[A-Z]-\d{8}-\d+(?:-\d+)*)\.pdf',p.path)
            if m and self.title and re.match(r'(?:ORDEN|RESOLUCI[ÓO]N|DECRETO|ACUERDO|CORRECCI[ÓO]N|EXTRACTO|LEY|ANUNCIO)\b',self.title,re.I):
                y,mo,d,bid=m.groups();day=f'{y}-{mo}-{d}'
                if self.day and day!=self.day:return
                self.rows[bid]={'id':bid,'title':self.title,'issuer':self.issuer,'major':self.major,'section':self.section,'pdf_url':url,'day':day,
                    'source_url':BASE+f'html/{y}/{mo}/{d}/html/{bid}.do'}
            if re.fullmatch(r'/boletines/\d{4}/\d{2}/\d{2}/pdf/BOCYL-S-.*\.pdf',p.path):
                self.day='/'.join(p.path.split('/')[2:5]).replace('/','-')
    def handle_data(self,data):
        if self.tag:self.buf.append(data)
    def handle_endtag(self,tag):
        if tag!=self.tag:return
        value=' '.join(' '.join(self.buf).split());self.tag=None
        if tag=='h2':self.heading=value
        elif tag=='h3':self.major=value
        elif tag=='h4':self.section=value
        elif tag=='h5':self.issuer=value
        elif tag=='p':self.title=value

def latest_summary_url(raw):
    # The bare boletin.do endpoint is an error page. The official portal's
    # accesskey=u link identifies the last published edition, also on holidays.
    class Latest(HTMLParser):
        def __init__(self):super().__init__();self.urls=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='a' and a.get('accesskey')=='u':self.urls.append(urljoin(BASE,a.get('href','')))
    p=Latest();p.feed(raw.decode('utf-8-sig'))
    urls=[u for u in p.urls if urlsplit(u).hostname=='bocyl.jcyl.es' and urlsplit(u).scheme=='https' and urlsplit(u).path=='/boletin.do' and parse_qs(urlsplit(u).query).get('fechaBoletin')]
    if len(set(urls))!=1:raise ValueError('Official portal lacks an unambiguous latest-edition link')
    return urls[0]

def parse_summary(raw,url):
    p=Summary();p.feed(raw.decode('utf-8-sig'))
    if not p.day or 'sumario bocyl' not in fold(p.heading):raise ValueError('BOCYL summary unavailable or identity unverified; never infer no edition from an error page')
    requested=parse_qs(urlsplit(url).query).get('fechaBoletin')
    if requested:
        d,m,y=requested[0].split('/')
        if p.day!=f'{y}-{m.zfill(2)}-{d.zfill(2)}':raise ValueError('BOCYL returned a different date')
    if any(r['day']!=p.day for r in p.rows.values()):raise ValueError('Foreign-date notice in official summary')
    return p

def selected(row):
    if not row['major'].startswith('I. '):return False
    topic=fold(row['title'])
    if re.search(r'consejo social de la universidad|miembro.{0,90}consejo de administracion',topic):return False
    employment=('b.1.' in fold(row['section']) or 'b.2.' in fold(row['section']))
    structural=bool(re.search(r'oferta de empleo publico|relacion de puestos de trabajo|plantilla organica',topic))
    return (employment or structural) and not exclusion_reason(row['title'],row['issuer'],True)
