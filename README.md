# ค้นหาราคากลางยา · Drug Price Index

หน้าเว็บค้นหาราคากลางยา (ชื่อสามัญ / รูปแบบ / ความแรง) ที่ **ดึงข้อมูลจาก
[ระบบราคากลางยา อย.](https://ndi.fda.moph.go.th/drug_value) เองอัตโนมัติ** ผ่าน GitHub Actions
แล้ว deploy ขึ้น GitHub Pages — ไม่ต้องรันโค้ดที่เครื่อง ไม่ต้องวางไฟล์เอง

## ทำงานยังไง

```
GitHub Action (ตั้งเวลา/กดเอง)
   └─ scripts/build.py   ── ดึง HTML ทุกหน้าจาก ndi.fda.moph.go.th/drug_value
                         ── parse + normalize  ─► site/data.json   (rawdata)
                         ── ฉีด SEO (รายการ crawlable + JSON-LD + meta) ─► site/index.html
                         ── เขียน site/sitemap.xml + robots.txt
   └─ สร้าง Release "data-YYYYMMDD" แนบ data.json (เก็บเวอร์ชันราคาแต่ละรอบ)
   └─ deploy site/ ขึ้น GitHub Pages
```

หน้าเว็บ (`index.html`) โหลด `data.json` มาแสดง + ค้นหาฝั่ง client (เร็ว ไม่ต้องมี backend)

## วิธี deploy ครั้งแรก

1. สร้าง repo ใหม่บน GitHub แล้ว push โฟลเดอร์นี้ขึ้นไป (branch `main`)
2. ไปที่ **Settings → Pages → Build and deployment → Source = GitHub Actions**
3. ไปแท็บ **Actions → "Build & Deploy Drug Price Index" → Run workflow** (กดรันครั้งแรก)
4. เสร็จแล้วเปิดได้ที่ `https://<user>.github.io/<repo>/`

จากนั้นมันจะอัปเดตเอง **ทุกวันจันทร์** (ปรับ cron ใน `.github/workflows/deploy.yml` ได้)
หรือกด **Run workflow** เพื่อ release รอบใหม่ทันที — ทั้งหมดทำบน GitHub ไม่ต้องแตะเครื่อง

## โครงสร้าง

```
drug-price-index/
├─ site/
│  ├─ index.html        หน้าเว็บค้นหา (มี SEO markers, โหลด data.json)
│  ├─ data.json         rawdata (สร้างโดย build.py)  ← UI ใช้ไฟล์นี้
│  ├─ sitemap.xml       (สร้างอัตโนมัติ)
│  └─ robots.txt        (สร้างอัตโนมัติ)
├─ scripts/
│  ├─ build.py          ดึง+แปลง+ฉีด SEO  (โหมดเว็บ / --file)
│  └─ requirements.txt
├─ data/raw/            ไฟล์ .xls สำรอง (ใช้กับโหมด --file เท่านั้น)
└─ .github/workflows/deploy.yml
```

## รันเองในเครื่อง (ถ้าต้องการทดสอบ)

```bash
pip install -r scripts/requirements.txt

# โหมดดึงจากเว็บ (เหมือนที่ Action ทำ)
python scripts/build.py --base-url http://localhost:8000

# หรือโหมดไฟล์สำรอง (ไม่ต่อเน็ต ต้องมี LibreOffice)
python scripts/build.py --file data/raw/<ไฟล์>.xls --base-url http://localhost:8000

# พรีวิว (ต้องเสิร์ฟผ่าน http ไม่ใช่เปิดไฟล์ตรง ๆ เพราะ fetch ถูกบล็อกบน file://)
cd site && python -m http.server 8000   # เปิด http://localhost:8000
```

## SEO

- `<title>`, `description`, `keywords`, canonical, Open Graph, Twitter card
- **JSON-LD** `WebSite` (+ `SearchAction` รองรับ `?q=`) และ `Dataset`
- รายการยา **crawlable** ฝังใน DOM (ซ่อนสายตาแต่ search engine อ่านได้) สร้าง build-time
- `sitemap.xml` + `robots.txt` อัปเดต lastmod ทุกรอบ build

## แหล่งข้อมูล (เลือกได้)

build.py ตรวจ layout ไฟล์เองอัตโนมัติ (รองรับทั้ง export ของ NDI และไฟล์ประกาศ DMSIC)
มี 3 โหมด:

| โหมด | คำสั่ง | ใช้เมื่อ |
|------|--------|---------|
| NDI scrape (ดีฟอลต์) | `build.py` | ดึงสด ๆ จาก ndi.fda.moph.go.th อัตโนมัติทุกรอบ |
| DMSIC / URL ตรง | `build.py --url <ลิงก์ .xls>` | มีลิงก์ไฟล์ประกาศโดยตรง (เช่นจาก dmsic.moph.go.th) |
| ไฟล์ในเครื่อง | `build.py --file <ไฟล์>` | อัปไฟล์เอง / ทดสอบออฟไลน์ |

**บน GitHub Action:** กด *Run workflow* แล้ววางลิงก์ไฟล์ DMSIC ในช่อง `source_url`
จะดาวน์โหลด+build จากไฟล์นั้น (เว้นว่าง = ดึงจาก NDI อัตโนมัติ) — ทำบนคลาวด์ ไม่ต้องแตะเครื่อง

ที่มา:
- ระบบราคากลางยา อย. — <https://ndi.fda.moph.go.th/drug_value>
- ศูนย์ข้อมูลข่าวสารด้านเวชภัณฑ์ สธ. (DMSIC) — <https://dmsic.moph.go.th/index/dataservice/90/0>

ราคารวมภาษีมูลค่าเพิ่ม 7% แล้ว ตามประกาศคณะกรรมการพัฒนาระบบยาแห่งชาติ
