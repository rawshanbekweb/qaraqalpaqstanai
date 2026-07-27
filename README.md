# Qoraqalpog'iston — iqtisodiy monitoring va AI analitika

Qoraqalpog'iston Respublikasi tumanlari bo'yicha iqtisodiy ko'rsatkichlarni
kuzatish platformasi: interaktiv xarita, avtomatik grafiklar va ma'lumotlar
bazasidan kontekst oladigan AI yordamchisi (RAG).

**Sohalar:** inflyatsiya, sanoat, qishloq xo'jaligi, investitsiyalar, eksport,
bandlik, qurilish, xizmatlar.

## Tuzilishi

```
backend/    FastAPI + PostgreSQL + Claude API (RAG)
frontend/   Next.js 16 + React 19 + Tailwind 4 + Recharts
tools/      gen_districts.py — xarita SVG yo'llarini generatsiya qiladi
map.txt     manba xarita ma'lumotlari
```

Frontend backendsiz ham to'liq ishlaydi: `NEXT_PUBLIC_API_URL` berilmasa,
`src/lib/ai-engine.ts` ichidagi brauzer tomonidagi RAG dvigateli javob beradi.
Backend ulanganda interfeys o'zgarmaydi — faqat javob manbai almashadi.

## Ishga tushirish

### 1. Frontend (o'zi yetarli)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # ixtiyoriy — backend ulash uchun
npm run dev                        # http://localhost:3000
```

Demo hisoblar (`src/lib/session.ts`):

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
python -m app.seed               # jadvallar + demo ma'lumotlar + foydalanuvchilar
uvicorn app.main:app --reload    # http://localhost:8000
```

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
| `GET`  | `/api/indicators`                   | Ko'rsatkichlar (filtrlanadi)         |
| `POST` | `/api/indicators`                   | Yangi ko'rsatkich — **admin**        |
| `POST` | `/api/indicators/import`            | Excel/CSV yuklash — **admin**        |
| `GET`  | `/api/tasks`                        | Iqtisodiy topshiriqlar               |
| `POST` | `/api/tasks`, `PATCH /api/tasks/{id}` | Topshiriq boshqaruvi — **admin**   |
| `GET`  | `/api/analytics/overview`           | Umumiy holat + zaif nuqtalar         |
| `GET`  | `/api/analytics/districts/{id}`     | Tuman profili                        |
| `GET`  | `/api/analytics/series`             | Oylik / choraklik dinamika           |
| `GET`  | `/api/analytics/charts/{kind}`      | Tayyor `ChartSpec`                   |
| `POST` | `/api/ai/chat`                      | RAG chat (Claude → mahalliy fallback)|
| `GET`  | `/api/ai/insight`                   | Dashboard tepasidagi xulosa          |
| `GET`  | `/api/ai/status`                    | Claude yoqilganmi + mavjud yillar    |
| `GET`  | `/api/health`                       | Holat tekshiruvi                     |

## Tekshirish

```bash
cd frontend
npx tsc --noEmit    # tiplar
npx eslint          # lint
npm run build       # ishlab chiqarish yig'masi
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
```

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
uyg'onishi ~30–60 soniya oladi. Shuning uchun frontend backendni 12 soniya
kutadi, so'ng brauzerdagi mahalliy dvigatelga o'tadi — demo hech qachon
qotib qolmaydi. Sahifa ochilganda backendga "uyg'otuvchi" so'rov ham
yuboriladi (`warmUpApi`).
