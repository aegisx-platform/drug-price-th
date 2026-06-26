# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo does

Static site ค้นหาราคากลางยาของไทย — ดึงข้อมูลจาก [NDI/FDA](https://ndi.fda.moph.go.th/drug_value) อัตโนมัติผ่าน GitHub Actions แล้ว deploy ขึ้น GitHub Pages ไม่มี backend

Flow:
```
GitHub Action → scripts/build.py → site/data.json + site/index.html (SEO injected) → GitHub Pages
```

## Commands

```bash
# ติดตั้ง dependencies
pip install -r scripts/requirements.txt

# รันแบบดึงสดจากเว็บ NDI (เหมือน Action)
python scripts/build.py --base-url http://localhost:8000

# รันจากไฟล์ .xls สำรอง (ต้องมี LibreOffice)
python scripts/build.py --file data/raw/<file>.xls --base-url http://localhost:8000

# รันจาก URL ตรง (เช่นไฟล์ DMSIC)
python scripts/build.py --url <url> --base-url http://localhost:8000

# Preview (ต้องเสิร์ฟผ่าน HTTP เพราะ fetch ถูกบล็อกบน file://)
cd site && python -m http.server 8000
```

## Architecture

### `scripts/build.py`
Script เดียวที่ทำทุกอย่าง — มี 3 โหมด (ตรวจจาก args):
- **NDI scrape** (default): ดึง HTML ทุกหน้าจาก `ndi.fda.moph.go.th/drug_value` ด้วย offset pagination (step 20) ใช้ BeautifulSoup parse ตาราง
- **`--file`**: อ่าน `.xls`/`.xlsx` ผ่าน pandas — auto-detect header row ด้วยการ scan 8 แถวแรกหาคำว่า "รายการยา"/"ชื่อยา" + "ราคากลาง"
- **`--url`**: download `.xls`/`.xlsx` จาก URL แล้วส่งต่อให้โหมด `--file`

**normalize pipeline** (`to_item`): แปลงทุก row เป็น dict มี fields: `g` (กลุ่มยา), `gen` (ชื่อสามัญ), `form`, `str` (strength), `pk` (pack), `price`, `st` (OK/REVIEW)

**SEO injection**: `inject()` เขียนทับ placeholders ใน `site/index.html`:
- `<!--SEO_LIST-->...<!--/SEO_LIST-->` → รายการยา crawlable (สูงสุด 1500 รายการ)
- `<!--SEO_JSONLD-->...<!--/SEO_JSONLD-->` → JSON-LD schema
- `__UPDATED__`, `__COUNT__`, `__BASEURL__` → string replace

### `site/`
- **`index.html`**: Template ถาวร มี SEO placeholder markers และ JS ค้นหาฝั่ง client — `build.py` inject เนื้อหาเข้าไปตอน build
- **`data.json`**: Output หลัก structure `{meta: {...}, items: [...]}` — UI โหลดไฟล์นี้ตอน runtime
- `sitemap.xml`, `robots.txt`: สร้างอัตโนมัติทุก build

### `.github/workflows/deploy.yml`
- Trigger: กดเอง (workflow_dispatch พร้อม optional `source_url`), ทุกวันอาทิตย์ 19:00 UTC, หรือ push ที่แก้ `site/index.html`/`scripts/`
- สร้าง GitHub Release tag `data-YYYYMMDD` พร้อมแนบ `data.json` ทุกรอบ build (เก็บประวัติราคาแต่ละรอบ)
- Deploy ขึ้น GitHub Pages จาก `site/` directory

## Data sources

| แหล่ง | CLI | หมายเหตุ |
|-------|-----|---------|
| NDI/FDA (auto) | `build.py` | ดีฟอลต์ — scrape HTML pagination |
| DMSIC/URL ตรง | `build.py --url <url>` | ดาวน์โหลด .xls/.xlsx |
| ไฟล์ในเครื่อง | `build.py --file <path>` | ต้องมี LibreOffice สำหรับ .xls |

`build.py` auto-detect layout ของทั้ง NDI export และไฟล์ประกาศ DMSIC จาก header row

## Important constraints

- `build.py` ยุติทันที (sys.exit) ถ้า parse ได้น้อยกว่า 100 รายการ — ป้องกัน deploy ข้อมูลพัง
- `site/index.html` ต้องมี placeholder markers ครบ ไม่งั้น SEO injection จะ silently ไม่ทำงาน
- Preview ต้องใช้ HTTP server เสมอ — `fetch('data.json')` ถูกบล็อกบน `file://`
- `.xls` (ไม่ใช่ `.xlsx`) ต้องมี LibreOffice ติดตั้งในเครื่องเพื่อ convert ก่อน pandas อ่าน
