# Qoraqalpog'iston — iqtisodiy monitoring va AI analitika

Qoraqalpog'iston Respublikasi rayonlari bo'yicha rasmiy statistikani kuzatish
platformasi: interaktiv xarita, avtomatik grafiklar va ma'lumotlar bazasidan
kontekst oladigan AI yordamchisi (RAG). Interfeys tili — qoraqalpoqcha.

**Manba:** 109 ta Excel fayl (2010–2026) → 1084 ko'rsatkich, 24 199 o'lchov,
17 hudud. **Tayanch sohalar:** sanoat, qishloq xo'jaligi, investitsiyalar,
qurilish, xizmatlar, transport, savdo.

> Manbada **reja yo'q** — faqat o'lchangan qiymat. Shuning uchun platformada
> "reja bajarilishi" tushunchasi ham yo'q: hajm, o'tgan yilga nisbatan o'sish,
> respublikadagi ulush va o'rin bilan ishlanadi. Oylik/choraklik qator ham
> yo'q: to'liq yil va joriy yil uchun "yanvar–iyun" yig'indisi.

## Tuzilishi

```
backend/    FastAPI + PostgreSQL + Claude API (RAG)
frontend/   Next.js 16 + React 19 + Tailwind 4 + Recharts
model/      109 ta manba Excel (data/) va model kodi
tools/      gen_districts.py — xarita SVG yo'llarini generatsiya qiladi
map.txt     manba xarita ma'lumotlari
```

Frontend **backendsiz ishlamaydi**: barcha raqamlar bazadan keladi. Brauzerda
ma'lumot nusxasi ataylab yo'q — ikkinchi, soddalashtirilgan hisob-kitob
javoblarni bazadagidan ayirib qo'yardi. Backend ulanmasa interfeys buni ochiq
aytadi.

## Ishga tushirish

### 1. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL — majburiy
npm run dev                        # http://localhost:3000
```

Hisoblar backendda tekshiriladi (`/api/auth/login`); backend ulanmagan
bo'lsa `src/lib/session.ts` dagi demo hisoblar tokensiz ishlaydi — admin
paneli bunda ma'lumot ko'rsatmaydi:

| Login    | Parol       | Rol           |
| -------- | ----------- | ------------- |
| `admin`  | `admin123`  | administrator |
| `rahbar` | `rahbar123` | ko'ruvchi     |

Kirilmagan foydalanuvchi `src/proxy.ts` orqali `/login` sahifasiga
yo'naltiriladi (Next.js 16'da `middleware` → `proxy` deb nomlangan).

### 2. Backend (PostgreSQL + Claude)

PostgreSQL'da baza yarating:

```sql
CREATE DATABASE qoraqalpogiston;
```

So'ng:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows;  Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # DATABASE_URL va ANTHROPIC_API_KEY ni to'ldiring
python -m app.seed                        # jadvallar + hududlar + sohalar + foydalanuvchilar
python -m app.ingest.loader ../model/data # Excel'dan statistikani yuklash
uvicorn app.main:app --reload             # http://localhost:8000
```

`app.seed` ma'lumot GENERATSIYA QILMAYDI — u faqat ma'lumotnomalarni
sinxronlaydi. Statistika `app.ingest.loader` orqali Excel'dan keladi;
qayta ishga tushirish xavfsiz (ko'rsatkichlar `slug` bo'yicha yagona).

API hujjatlari: <http://localhost:8000/docs>

Backendni frontendga ulash uchun `frontend/.env.local` ichida:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Muhit o'zgaruvchilari

`backend/.env` (namuna — `.env.example`):

| O'zgaruvchi         | Vazifasi                                                    |
| ------------------- | ----------------------------------------------------------- |
| `DATABASE_URL`      | PostgreSQL ulanish satri                                    |
| `JWT_SECRET`        | Token imzosi — ishlab chiqarishda albatta almashtiring       |
| `ANTHROPIC_API_KEY` | Bo'sh bo'lsa AI mahalliy dvigatelga tushadi                  |
| `CLAUDE_MODEL`      | Standart: `claude-opus-5`                                    |
| `CORS_ORIGINS`      | Ruxsat etilgan frontend manzillari (vergul bilan)            |

## API

| Metod  | Yo'l                                | Izoh                                 |
| ------ | ----------------------------------- | ------------------------------------ |
| `POST` | `/api/auth/login`                   | JWT token oladi                      |
| `GET`  | `/api/auth/me`                      | Joriy foydalanuvchi                  |
| `GET`  | `/api/districts`, `/api/modules`    | Ma'lumotnomalar                      |
| `GET`  | `/api/stats/meta`                   | Yillar, sohalar, kategoriyalar, hududlar |
| `GET`  | `/api/stats/overview`               | Sohalar bo'yicha yakun               |
| `GET`  | `/api/stats/map`                    | Xarita qatlami (hudud kesimi)        |
| `GET`  | `/api/stats/series`                 | Yillar qatori (2010–2026)            |
| `GET`  | `/api/stats/districts/{id}`         | Hudud profili                        |
| `GET`  | `/api/stats/indicators`             | Ko'rsatkichlar ma'lumotnomasi (qidiruv) |
| `GET`  | `/api/stats/summary`                | Bazaning holati — **admin**          |
| `POST` | `/api/stats/upload`                 | Excel yuklash — **admin**            |
| `PATCH`| `/api/stats/indicators/{id}`        | Tayanch sohaga biriktirish — **admin** |
| `GET`  | `/api/tasks`                        | Iqtisodiy topshiriqlar               |
| `POST` | `/api/tasks`, `PATCH`/`DELETE /api/tasks/{id}` | Topshiriq boshqaruvi — **admin** |
| `POST` | `/api/ai/chat`                      | RAG chat (Claude → mahalliy fallback)|
| `GET`  | `/api/ai/insight`                   | Dashboard tepasidagi xulosa          |
| `GET`  | `/api/ai/status`                    | Claude yoqilganmi + mavjud yillar    |
| `GET`  | `/api/health`                       | Holat tekshiruvi                     |

## Tekshirish

```bash
cd frontend
npx tsc --noEmit         # tiplar
npx eslint src           # lint
npm run build            # ishlab chiqarish yig'masi
```

Eski demo modelidan qolgan yozuvlarni tozalash (topshiriqlar generatordan
chiqqan bo'lsa ham foydalanuvchi kiritgani bo'lishi mumkin, shuning uchun
faqat ochiq bayroq bilan):

```bash
cd backend
python -m app.seed --reset-demo
```

## Xarita

`frontend/src/data/districts.ts` fayli `tools/gen_districts.py` yordamida
`map.txt` dan generatsiya qilingan. Xarita geometriyasi o'zgarsa skriptni
qayta ishga tushiring.

## Deploy — Neon + Render + Vercel

Uchala xizmat ham shu GitHub repozitoriysidan ishlaydi. Tartib muhim:
avval baza, keyin backend, oxirida frontend — chunki har biri oldingisining
manzilini talab qiladi.

### 1. Neon — PostgreSQL

1. <https://neon.tech> da loyiha yarating (region: Frankfurt yoki eng yaqini).
2. **Connection string** ni nusxalang — `postgresql://...?sslmode=require`
   ko'rinishida bo'ladi. Drayver prefiksini o'zgartirish shart emas:
   `app/config.py` uni avtomatik `postgresql+psycopg://` ga aylantiradi.

### 2. Render — FastAPI backend

Repozitoriyda `render.yaml` tayyor, shuning uchun **New → Blueprint** orqali
repozitoriyni ulash kifoya. Render panelida quyidagilarni kiriting:

> **Python versiyasi 3.12 ga qadalgan** (`backend/.python-version`). Render'ning
> standart versiyasi yangiroq bo'lishi mumkin, u holda `pydantic-core` uchun
> tayyor wheel topilmay, pip uni Rust orqali qurishga urinadi va Render'ning
> read-only fayl tizimida yiqiladi. Faylni o'chirmang.

| O'zgaruvchi         | Qiymat                                              |
| ------------------- | --------------------------------------------------- |
| `DATABASE_URL`      | Neon'dan olingan satr                                |
| `CORS_ORIGINS`      | Vercel manzili (3-qadamdan keyin qo'shiladi)         |
| `ANTHROPIC_API_KEY` | Ixtiyoriy — bo'sh qolsa mahalliy AI dvigateli ishlaydi |

`JWT_SECRET` avtomatik generatsiya qilinadi.

Birinchi deploydan so'ng bazani to'ldiring — Render'ning **Shell** bo'limida:

```bash
python -m app.seed
python -m app.ingest.loader ../model/data
```

> `model/data` repozitoriyda bor (109 Excel, ~5 MB). Model og'irliklari esa
> `.gitignore` bilan to'silgan — demo ularsiz ishlaydi.

Tekshirish: `https://<render-manzil>/api/health` → `{"status":"ok"}`

### 3. Vercel — Next.js frontend

1. Repozitoriyni import qiling, **Root Directory** ni `frontend` qilib belgilang.
2. Muhit o'zgaruvchisi: `NEXT_PUBLIC_API_URL` = Render manzili
   (masalan `https://qaraqalpaqstan-api.onrender.com`, oxirida `/` yo'q).
3. Deploydan so'ng Vercel bergan manzilni Render'dagi `CORS_ORIGINS` ga
   qo'shing va backendni qayta ishga tushiring.

> `NEXT_PUBLIC_*` qiymatlari **build vaqtida** kodga o'rnatiladi — uni
> o'zgartirgach Vercel'da qayta deploy qilish shart.

### Bepul darajaning cheklovi

Render'ning bepul xizmati 15 daqiqa harakatsizlikdan keyin uxlaydi va
uyg'onishi ~30–60 soniya oladi. Shuning uchun sahifa ochilganda backendga
"uyg'otuvchi" so'rov yuboriladi (`warmUpApi`), chat esa 20 soniya kutadi va
kutish tugasa holatni ochiq aytadi.
