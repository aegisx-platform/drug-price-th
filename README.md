# ค้นหาราคากลางยา · Drug Price Index

> เว็บค้นหาราคากลางยาตามชื่อสามัญ รูปแบบ และความแรง — ดึงข้อมูลจากระบบราคากลางยา อย. โดยอัตโนมัติ ไม่ต้องรันโค้ดที่เครื่อง

**🌐 เว็บไซต์:** https://aegisx-platform.github.io/drug-price-th

> **หมายเหตุ:** เว็บไซต์นี้ไม่ใช่เว็บไซต์ทางการของหน่วยงานรัฐ จัดทำขึ้นเพื่ออำนวยความสะดวกในการค้นหาราคากลางยาเท่านั้น

---

## Features

- **ค้นหาหลายคำ** — พิมพ์ `paracetamol 325` หรือ `insulin tab 100mg` ได้เลย ทุก token ต้อง match (AND logic)
- **ชื่อการค้าและชื่อไทย** — `panadol`, `ซาร่า`, `norflox`, `lasix` ฯลฯ แปลงเป็น INN อัตโนมัติ พร้อมแสดง hint
- **ค้นชื่อกลุ่มยา** — พิมพ์ `penicillin`, `opioid` ฯลฯ ได้เลย
- **Highlight คำที่เจอ** — ทุก token ที่ match จะ highlight สีเหลืองในผลลัพธ์
- **กรองและเรียง** — กลุ่มยา / สถานะ / ราคา / ชื่อ A→Z พร้อมปุ่มล้างทั้งหมด
- **ราคาต่อหน่วย** — แสดง "X บาท / 1 tablet" ชัดเจน
- **คัดลอก** — ปุ่ม copy ทุกการ์ด คัดลอกชื่อยา + ราคาได้ทันที
- **Mobile-first** — รองรับ iPhone / Android / iPad filter panel ซ่อนได้บนมือถือ
- **อัปเดตอัตโนมัติ** — GitHub Actions ดึงข้อมูลจาก NDI ใหม่ทุกวันจันทร์ 02:00 น.

---

## วิธีการทำงาน

```
GitHub Actions (ตั้งเวลา / กดเอง)
   └─ scripts/build.py
         ├─ scrape HTML ทุกหน้าจาก ndi.fda.moph.go.th/drug_value
         ├─ parse + normalize → site/data.json
         ├─ inject aliases (data/aliases.json) → site/index.html
         ├─ inject SEO (JSON-LD, crawlable list, meta) → site/index.html
         └─ เขียน site/sitemap.xml + robots.txt
   └─ สร้าง GitHub Release "data-YYYYMMDD" แนบ data.json (เก็บประวัติทุกรอบ)
   └─ deploy site/ → GitHub Pages
```

`index.html` โหลด `data.json` แล้วค้นหาฝั่ง client ทั้งหมด — ไม่มี backend

---

## Deploy ครั้งแรก

1. Fork / สร้าง repo ใหม่แล้ว push โฟลเดอร์นี้ขึ้น branch `main`
2. **Settings → Pages → Source = GitHub Actions**
3. **Actions → "Build & Deploy Drug Price Index" → Run workflow**
4. เปิดที่ `https://<user>.github.io/<repo>/`

หลังจากนั้นอัปเดตเองทุกวันจันทร์ หรือกด **Run workflow** ได้ตลอดเวลา

---

## โครงสร้างไฟล์

```
drug-price-th/
├─ site/
│  ├─ index.html        หน้าเว็บ (template — build.py inject เนื้อหาเข้าไป)
│  ├─ data.json         rawdata ราคายา (สร้างโดย build.py)
│  ├─ sitemap.xml       (สร้างอัตโนมัติ)
│  └─ robots.txt        (สร้างอัตโนมัติ)
├─ scripts/
│  ├─ build.py          scraper + SEO injector + alias injector
│  └─ requirements.txt
├─ data/
│  ├─ aliases.json      ชื่อการค้า / ชื่อไทย → INN (แก้ได้โดยไม่ต้องแตะโค้ด)
│  └─ raw/              ไฟล์ .xls สำรอง (ใช้กับ --file เท่านั้น)
└─ .github/workflows/deploy.yml
```

---

## รันในเครื่อง (สำหรับทดสอบ)

```bash
pip install -r scripts/requirements.txt

# scrape สดจาก NDI (เหมือน Action)
python scripts/build.py --base-url http://localhost:8000

# อ่านจากไฟล์ .xls สำรอง (ต้องมี LibreOffice)
python scripts/build.py --file data/raw/<file>.xls --base-url http://localhost:8000

# อ่านจาก URL ตรง (เช่น ไฟล์ประกาศ DMSIC)
python scripts/build.py --url <url> --base-url http://localhost:8000

# Preview (ต้องเสิร์ฟผ่าน HTTP — fetch ถูกบล็อกบน file://)
cd site && python -m http.server 8000
```

---

## เพิ่ม/แก้ชื่อการค้า (Aliases)

แก้ไฟล์ `data/aliases.json` แล้ว commit ขึ้น — `build.py` inject เข้า HTML อัตโนมัติตอน build ไม่ต้องแตะโค้ด JS

```json
{
  "panadol": "paracetamol",
  "ซาร่า": "paracetamol",
  "norflox": "norfloxacin"
}
```

> ควรให้เภสัชกรหรือบุคลากรทางการแพทย์ตรวจสอบก่อน deploy จริง

---

## แหล่งข้อมูลทางการ

| แหล่งข้อมูล | ลิงก์ |
|-------------|-------|
| ระบบราคากลางยา สำนักงานคณะกรรมการอาหารและยา (อย.) | https://ndi.fda.moph.go.th/drug_value |
| ศูนย์ข้อมูลข่าวสารด้านเวชภัณฑ์ กระทรวงสาธารณสุข (DMSIC) | https://dmsic.moph.go.th/index/dataservice/90/0 |

ราคารวมภาษีมูลค่าเพิ่ม 7% ตามประกาศคณะกรรมการพัฒนาระบบยาแห่งชาติ

---

## GitHub Actions Triggers

| Trigger | เงื่อนไข |
|---------|---------|
| อัตโนมัติ | ทุกวันอาทิตย์ 19:00 UTC (จันทร์ 02:00 น. ไทย) |
| Push | เมื่อแก้ `site/index.html`, `scripts/**`, `.github/workflows/**` |
| Manual | กด **Run workflow** — ใส่ `source_url` (URL ไฟล์ .xls จาก DMSIC) หรือเว้นว่างเพื่อ scrape NDI |
