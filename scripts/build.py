#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — ดึงราคากลางยาจาก NDI/FDA เองแล้วสร้าง rawdata + ฉีด SEO
ไม่ต้องวางไฟล์เอง ไม่ต้องรันที่เครื่อง — GitHub Action รันตัวนี้ได้เลย

ทำอะไรบ้าง:
  1) ดึง HTML ทุกหน้าจาก https://ndi.fda.moph.go.th/drug_value (offset 0,20,... )
  2) parse ตาราง + carry หัวข้อกลุ่มยา + normalize -> site/data.json
  3) ฉีดเนื้อหา crawlable + JSON-LD + meta ลง site/index.html
  4) เขียน site/sitemap.xml (lastmod)

โหมด:
  default  : ดึงจากเว็บ (ใช้ requests + beautifulsoup4)
  --file X : อ่านจากไฟล์ .xls/.xlsx แทน (fallback ออฟไลน์ ต้องมี LibreOffice/pandas)

usage:
  python scripts/build.py --base-url https://USER.github.io/REPO
  python scripts/build.py --file data/raw/xxx.xls --base-url https://...
"""
import os, re, sys, json, time, glob, hashlib, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
BASE_SRC = "https://ndi.fda.moph.go.th/drug_value"
PAGE_URL = "https://ndi.fda.moph.go.th/drug_value/index/public/0/{off}"
SOURCE_URL = "https://ndi.fda.moph.go.th/drug_value"

# ============ normalize (controlled vocabulary) ============
REL  = ['sr','er','pr','xr','mr','cr','ec','la','xl','delayed release','extended release',
        'modified release','sustained release','orodispersible','chewable','dispersible',
        'effervescent','enteric coated']
BASE = ['sterile sol','sterile pwdr','sterile susp','eye drops','eye oint','nasal spray',
        'dry syr','oral sol','oral susp','pre-filled pen injection','intravitreal implant',
        'lozenge','implant','tab','cap','syr','inj','pwdr','cream','oint','gel','lotion',
        'supp','patch','spray','drops','sol','susp']
FORM_TOKENS = sorted({b for b in BASE} | {f"{r} {b}" for r in REL for b in BASE}, key=len, reverse=True)
THAI_UNIT = {'เม็ด':'tablet','แคปซูล':'capsule','แคปซูล/เม็ด':'cap/tab','ขวด':'bottle','ด้าม':'prefilled_pen',
             'หลอด':'tube','ml':'ml','ซอง':'sachet','vial':'vial','แผง':'blister','ชิ้น':'piece',
             'กล่อง':'box','ถุง':'bag','ชุด':'set','อัน':'piece','ไซริงจ์':'syringe','ไซรินจ์':'syringe'}

def parse_form(s):
    low = str(s).lower().strip()
    for t in FORM_TOKENS:
        if low.startswith(t): return t
    m = re.match(r'^([a-zA-Z/\-\s]+?)\s*\d', str(s).strip())
    return m.group(1).strip().lower() if m else ''
def parse_strength(s):
    m = re.findall(r'([\d.]+(?:\s*[+/]\s*[\d.]+)*)\s*(mcg|mg|g|iu|unit|%|ml)', str(s), re.I)
    return ' '.join(f"{v.replace(' ','')}{u.lower()}" for v,u in m) if m else ''
def parse_pack(s):
    m = re.match(r'^([\d.]+)\s*(.*)$', str(s).strip())
    if m: return m.group(1), THAI_UNIT.get(m.group(2).strip(), m.group(2).strip())
    return '', str(s).strip()
def to_item(group, name, form_strength, pack, price_raw, note):
    form = parse_form(form_strength); strg = parse_strength(form_strength)
    pq, pu = parse_pack(pack)
    pm = re.search(r'[\d]+(?:\.\d+)?', str(price_raw).replace(',',''))
    price = float(pm.group()) if pm else None
    return dict(g=group, gen=re.sub(r'^\d+\.\s*','',str(name)).strip(),
                form=form, str=strg, pk=(pq+' '+pu).strip(), price=price, gp='',
                st='OK' if form and strg else 'REVIEW')

GROUP_RE = re.compile(r'^\s*\d+(\.\d+)*\.?\s*(กลุ่ม|กลุ่มนี้)')

# ============ MODE 1: scrape NDI ============
def scrape():
    import requests
    from bs4 import BeautifulSoup
    sess = requests.Session()
    sess.headers.update({'User-Agent':'Mozilla/5.0 (DrugPriceIndex build bot)'})
    # หาจำนวนรายการ/หน้าสุดท้ายจากหน้าแรก
    r = sess.get(PAGE_URL.format(off=0), timeout=60); r.raise_for_status()
    total = None
    mt = re.search(r'จำนวน\s*([\d,]+)\s*รายการ', r.text)
    if mt: total = int(mt.group(1).replace(',',''))
    last = 0
    for m in re.finditer(r'/drug_value/index/public/0/(\d+)', r.text):
        last = max(last, int(m.group(1)))
    if not last: last = (total or 2600)
    print(f"  พบ ~{total} รายการ, offset สุดท้าย {last}")

    items, cur_group, seen = [], '', set()
    for off in range(0, last+20, 20):
        html = r.text if off == 0 else sess.get(PAGE_URL.format(off=off), timeout=60).text
        soup = BeautifulSoup(html, 'html.parser')
        # เลือกตารางหลัก = ตารางที่มีจำนวน <tr> มากสุด (ตัด template ท้ายหน้าทิ้ง)
        tables = soup.find_all('table')
        if not tables:
            if off!=0: time.sleep(0.2)
            continue
        main = max(tables, key=lambda t: len(t.find_all('tr')))
        for tr in main.find_all('tr'):
            tds = tr.find_all('td')
            if not tds: continue
            cells = [c.get_text(' ', strip=True) for c in tds]
            name = cells[0] if cells else ''
            rest = cells[1:] if len(cells)>1 else []
            form = rest[0] if len(rest)>0 else ''
            pack = rest[1] if len(rest)>1 else ''
            price= rest[2] if len(rest)>2 else ''
            note = rest[3] if len(rest)>3 else ''
            # หัวข้อกลุ่ม: คอลัมน์ฟอร์ม/บรรจุ/ราคาว่าง และชื่อขึ้นต้นด้วยเลขกลุ่ม
            if (not form and not pack and not price):
                if name and GROUP_RE.match(name): cur_group = re.sub(r'\s+',' ',name).strip()
                continue
            if not name or not form: continue
            it = to_item(cur_group, name, form, pack, price, note)
            key = (it['gen'], it['form'], it['str'], it['pk'], it['price'])
            if key in seen: continue
            seen.add(key); items.append(it)
        if off and off % 400 == 0: print(f"  ...ดึงถึง offset {off} ({len(items)} รายการ)")
        if off != 0: time.sleep(0.15)   # สุภาพต่อเซิร์ฟเวอร์
    return items

# ============ MODE 2: local file / URL (auto-detect layout) ============
def _ensure_xlsx(path):
    import subprocess
    if path.lower().endswith('.xls'):
        subprocess.run(['libreoffice','--headless','--convert-to','xlsx',path,'--outdir','/tmp'],
                       check=True, capture_output=True)
        return '/tmp/' + os.path.splitext(os.path.basename(path))[0] + '.xlsx'
    return path

def _download(url):
    import requests
    r = requests.get(url, timeout=120, headers={'User-Agent':'Mozilla/5.0 (DrugPriceIndex)'} )
    r.raise_for_status()
    ext = '.xls' if url.lower().endswith('.xls') else '.xlsx'
    p = '/tmp/_dl' + ext
    open(p,'wb').write(r.content); return p

def from_file(path=None, url=None):
    """รองรับทั้ง layout NDI export และไฟล์ประกาศ DMSIC โดยตรวจจาก header เอง"""
    import pandas as pd
    if url: path = _download(url)
    path = _ensure_xlsx(path)
    # สแกนหา header row (แถวที่มีคำว่า รายการยา/ชื่อยา + ราคากลาง) ใน 8 แถวแรก
    raw = pd.read_excel(path, sheet_name=0, header=None, dtype=str)
    hdr = None
    for i in range(min(8, len(raw))):
        joined = ' '.join(str(x) for x in raw.iloc[i].tolist())
        if ('รายการยา' in joined or 'ชื่อยา' in joined or 'ชื่อสามัญ' in joined) and 'ราคากลาง' in joined:
            hdr = i; break
    if hdr is None: hdr = 0
    head = [str(x) for x in raw.iloc[hdr].tolist()]
    def find(*keys):
        for j,h in enumerate(head):
            if any(k in h for k in keys): return j
        return None
    c_gen   = find('รายการยา','ชื่อสามัญ','ชื่อยา')
    c_form  = find('รูปแบบ')
    c_pack  = find('หน่วย','ขนาดบรรจุ')
    c_price = find('ราคากลาง','ราคา')
    c_note  = find('หมายเหตุ')
    c_group = find('กลุ่มยา')                              # NDI export มีคอลัมน์กลุ่มในแต่ละแถว
    body = raw.iloc[hdr+1:]
    out, cur_group = [], ''
    for _, r in body.iterrows():
        def cell(c): return str(r[c]).strip() if c is not None and pd.notna(r[c]) else ''
        gen, form, pack = cell(c_gen), cell(c_form), cell(c_pack)
        price = r[c_price] if c_price is not None else None
        note  = r[c_note] if c_note is not None else ''
        if c_group is not None and cell(c_group):          # layout แบบมีคอลัมน์กลุ่ม (NDI)
            cur_group = re.sub(r'\s+',' ',cell(c_group)).strip()
        if not gen and not form: continue                  # แถวว่าง
        if gen and not form and (price is None or str(price).strip() in ('','nan')):
            if GROUP_RE.match(gen): cur_group = re.sub(r'\s+',' ',gen).strip()
            continue                                        # แถวหัวข้อกลุ่ม (DMSIC)
        if not gen: continue
        out.append(to_item(cur_group, gen, form, pack, price, note))
    return out

# ============ SEO + write ============
def esc(s): return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def seo_block(items):
    li=[f"<li>{esc(d['gen'])} {esc(d['form'])} {esc(d['str'])} — ราคากลาง "
        f"{(format(d['price'],'.2f') if d['price'] is not None else 'ตามประกาศ')} บาท</li>" for d in items[:1500]]
    return "<ul>\n"+"\n".join(li)+"\n</ul>"
def json_ld(items, base, updated, count):
    ex=[{"@type":"Drug","name":d['gen'],"description":f"{d['form']} {d['str']}".strip()} for d in items[:25]]
    g={"@context":"https://schema.org","@graph":[
       {"@type":"WebSite","name":"ค้นหาราคากลางยา (Drug Price Index)","url":base,"inLanguage":"th",
        "description":"ค้นหาราคากลางยาตามชื่อสามัญ รูปแบบ และความแรง",
        "potentialAction":{"@type":"SearchAction","target":base+"/?q={q}","query-input":"required name=q"}},
       {"@type":"Dataset","name":"ราคากลางยา (ประเทศไทย)","inLanguage":"th","url":base,
        "description":"ชุดข้อมูลราคากลางยาตามชื่อสามัญ รูปแบบยา ความแรง และขนาดบรรจุ",
        "dateModified":updated,"isAccessibleForFree":True,"variableMeasured":"ราคากลาง (บาท)",
        "size":f"{count} รายการ",
        "creator":{"@type":"Organization","name":"สำนักงานคณะกรรมการอาหารและยา (อย.)","url":SOURCE_URL},
        "exampleOfWork":ex}]}
    return json.dumps(g, ensure_ascii=False, indent=2)
def inject(items, base, updated, count):
    p=os.path.join(SITE,'index.html'); h=open(p,encoding='utf-8').read()
    h=re.sub(r'<!--SEO_LIST-->.*?<!--/SEO_LIST-->',f'<!--SEO_LIST-->\n{seo_block(items)}\n<!--/SEO_LIST-->',h,flags=re.S)
    h=re.sub(r'<!--SEO_JSONLD-->.*?<!--/SEO_JSONLD-->',
             f'<!--SEO_JSONLD--><script type="application/ld+json">\n{json_ld(items,base,updated,count)}\n</script><!--/SEO_JSONLD-->',h,flags=re.S)
    h=h.replace('__UPDATED__',updated).replace('__COUNT__',str(count)).replace('__BASEURL__',base)
    aliases_path=os.path.join(ROOT,'data','aliases.json')
    if os.path.exists(aliases_path):
        raw=open(aliases_path,encoding='utf-8').read()
        aliases={k.lower():v.lower() for k,v in json.loads(raw).items() if not k.startswith('_')}
        aliases_js=json.dumps(aliases,ensure_ascii=False)
        h=re.sub(r'/\*ALIASES_JSON\*/.*?/\*END_ALIASES\*/',f'/*ALIASES_JSON*/ {aliases_js} /*END_ALIASES*/',h,flags=re.S)
    open(p,'w',encoding='utf-8').write(h)
def sitemap(base, updated):
    open(os.path.join(SITE,'sitemap.xml'),'w',encoding='utf-8').write(
      f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
      f'  <url><loc>{base}/</loc><lastmod>{updated}</lastmod><changefreq>monthly</changefreq><priority>1.0</priority></url>\n</urlset>\n')
    open(os.path.join(SITE,'robots.txt'),'w',encoding='utf-8').write(
      f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")

def main():
    base='https://example.github.io/drug-price-index'; src_file=None; src_url=None
    a=sys.argv
    for i,x in enumerate(a):
        if x=='--base-url' and i+1<len(a): base=a[i+1].rstrip('/')
        if x=='--file' and i+1<len(a): src_file=a[i+1]
        if x=='--url'  and i+1<len(a): src_url=a[i+1]
    print("► ดึง/อ่านข้อมูล...")
    if src_url:    items = from_file(url=src_url)       # ดาวน์โหลด .xls/.xlsx ตรงจาก URL (เช่น DMSIC)
    elif src_file: items = from_file(path=src_file)     # อ่านไฟล์ในเครื่อง
    else:          items = scrape()                     # scrape หน้า NDI
    if len(items) < 100: sys.exit(f"❌ ได้ข้อมูลน้อยผิดปกติ ({len(items)}) — หยุดเพื่อกัน deploy ข้อมูลพัง")
    updated=dt.date.today().isoformat()
    digest=hashlib.sha256(json.dumps(items,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:12]
    payload={"meta":{"updated":updated,"count":len(items),"content_hash":digest,
                     "source":"scrape" if not src_file else os.path.basename(src_file),
                     "source_url":SOURCE_URL},"items":items}
    os.makedirs(SITE,exist_ok=True)
    json.dump(payload,open(os.path.join(SITE,'data.json'),'w',encoding='utf-8'),ensure_ascii=False)
    inject(items,base,updated,len(items)); sitemap(base,updated)
    print(f"✓ data.json: {len(items)} รายการ (hash {digest})")
    print(f"✓ index.html ฉีด SEO + sitemap lastmod={updated}, base={base}")

if __name__=='__main__': main()
