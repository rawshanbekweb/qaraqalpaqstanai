# Qaraqalpaqstan Iqtisodiy Monitoring — API Hujjati

**Base URL:** `http://localhost:8000`  
**Swagger UI:** `http://localhost:8000/docs`  
**Content-Type:** `application/json`

---

## Autentifikatsiya

Hozircha token talab qilinmaydi. Keyingi versiyada `Authorization: Bearer <token>` qo'shiladi.

---

## 1. Ko'rsatkichlar `/indicators`

### Yangi ko'rsatkich qo'shish
```http
POST /indicators/
```
**Body:**
```json
{
  "module": "industry",
  "region": "Nukus",
  "period": "2025",
  "period_type": "yearly",
  "year": 2025,
  "kpi_planned": 24323.5,
  "kpi_actual": 29094.0,
  "unit": "mlrd. som",
  "status": "completed",
  "comment": "Sanaat onimi rejadan 19.7% ortiq"
}
```
**`module` qiymatlari:** `industry` | `agriculture` | `export` | `import` | `investment` | `employment` | `services` | `construction`

**`status` qiymatlari:** `in_progress` | `completed` | `at_risk` | `critical`

**`period_type` qiymatlari:** `yearly` | `quarterly` | `monthly`

**Response:**
```json
{
  "id": 1,
  "module": "industry",
  "region": "Nukus",
  "kpi_planned": 24323.5,
  "kpi_actual": 29094.0,
  "status": "completed",
  "created_at": "2025-07-27T10:00:00"
}
```

---

### Ko'rsatkichlar ro'yhati
```http
GET /indicators/?module=export&region=QR+jami&year=2025&status=at_risk&limit=100
```
**Query params (hammasi ixtiyoriy):**

| Param | Tur | Misol |
|-------|-----|-------|
| `module` | string | `export` |
| `region` | string | `Nukus` |
| `year` | int | `2025` |
| `status` | string | `at_risk` |
| `limit` | int | `100` |

---

### Modul bo'yicha yig'ma statistika
```http
GET /indicators/summary/by-module?year=2025
```
**Response:**
```json
{
  "industry": {
    "ortasha_rejalan": 24323.5,
    "ortasha_amalda": 29094.0,
    "orindalish_pct": 119.6,
    "jami": 3,
    "qauipli": 0
  },
  "export": {
    "ortasha_rejalan": 500.0,
    "ortasha_amalda": 435.2,
    "orindalish_pct": 87.0,
    "jami": 2,
    "qauipli": 1
  }
}
```

---

### CSV / Excel bulk yuklash
```http
POST /indicators/bulk-upload
Content-Type: multipart/form-data
```
**Fayl:** `.xlsx` yoki `.csv`

**Jadval ustunlari:**
```
module | region | year | kpi_planned | kpi_actual | unit | status | comment
```

**JavaScript misoli:**
```javascript
const formData = new FormData();
formData.append('file', excelFile);
const res = await fetch('/indicators/bulk-upload', {
  method: 'POST',
  body: formData
});
```

---

### Ko'rsatkich yangilash / o'chirish
```http
PUT    /indicators/{id}
DELETE /indicators/{id}
```

---

## 2. AI Analitika `/analytics`

### Dashboard (Bosh sahifa uchun)
```http
GET /analytics/dashboard?year=2025
```
**Response:**
```json
{
  "jami_korsatkich": 22,
  "status_sanaq": {
    "completed": 12,
    "in_progress": 5,
    "at_risk": 4,
    "critical": 1
  },
  "modullar": {
    "export": { "planned": 500.0, "actual": 435.2, "pct": 87.0 }
  },
  "boljaniwlar": {
    "JAO": [
      { "Jıl": 2027, "Boljanıw": 61624.0, "TómenShegara": 60517.0, "JoqarıShegara": 62787.0 }
    ]
  },
  "ai_insight": "## Statistika\n2025-jılda ...",
  "qauipli_rayonlar": [
    { "region": "Bozataw", "orindalish": 87.0, "status": "at_risk" }
  ]
}
```

---

### Muammoli sohalar (Weak Spots)
```http
GET /analytics/weak-spots?year=2025
```
**Response:**
```json
{
  "ml_natiyjeler": [
    {
      "rayon": "Bozataw",
      "jil": 2025,
      "status": "Ortasha",
      "prob_qauipli": 0.007,
      "jumissizliq_pati": 5.54
    }
  ],
  "jami_qauipli": 0,
  "ai_tahlil": "## Statistika\n..."
}
```

---

### Prognoz (Forecast)
```http
GET /analytics/forecast?indicator=JAO&periods=5
```
**`indicator` qiymatlari:** `JAO` | `Sanaat` | `Eksport` | `Import` | `Investitsiya` | `Xızmetler` | `AwılXojalıǵı`

**Response:**
```json
{
  "boljaniwlar": {
    "JAO": [
      { "Jıl": 2027, "Boljanıw": 61624.0, "TómenShegara": 60517.8, "JoqarıShegara": 62787.8 },
      { "Jıl": 2028, "Boljanıw": 67234.4, "TómenShegara": 64738.0, "JoqarıShegara": 69821.1 }
    ]
  },
  "ai_tahlil": "Keleshek prognozları ...",
  "periods": 5
}
```

---

### Yillik hisobot
```http
GET /analytics/annual-report/2025
```
**Response:**
```json
{
  "jil": 2025,
  "statistika": {
    "modules": { "export": { "ortasha_amalda": 435.2, "orindalish": 87.0 } },
    "critical": [{ "region": "export", "orindalish": 87.0 }]
  },
  "ai_hisobot": "## Statistika\n2025-jıl juwmaqlawshı ...",
  "jami_qator": 22
}
```

---

### Erkin soraw (RAG)
```http
POST /analytics/ask
```
**Body:**
```json
{
  "soraw": "2025-jilda investitsiya korsatkishi qansha?",
  "year": 2025,
  "region": "QR jami",
  "module": "investment"
}
```
**Response:**
```json
{
  "soraw": "2025-jilda investitsiya korsatkishi qansha?",
  "juwap": "## Statistika\n**Investitsiya** (2025-jıl): **27,010.10** mlrd. som...",
  "kontekst_qator": 5
}
```

---

## 3. Topshiriqlar `/tasks`

### Yangi topshiriq
```http
POST /tasks/
```
**Body:**
```json
{
  "title": "Eksport hajmini 20% oshirish",
  "module": "export",
  "region": "QR jami",
  "description": "2025-2026 yillar rejasi",
  "deadline": "2025-12-31T00:00:00",
  "responsible": "Iqtisodiyot vazirligi",
  "status": "in_progress",
  "priority": "high"
}
```
**`priority`:** `low` | `medium` | `high` | `critical`

---

### Topshiriqlar ro'yhati
```http
GET /tasks/?module=export&status=in_progress&region=QR+jami
```

### Status yangilash
```http
PUT /tasks/{id}/status?status=completed
```

---

## 4. Ovozli Javob `/voice`

### Karakalpaqsha ovozli javob
```http
POST /voice/ask
```
**Body:**
```json
{
  "mavzu": "investitsiya",
  "ovoz": "ayol",
  "tezlik": "-5%",
  "year": 2025,
  "region": null
}
```
**`ovoz`:** `ayol` (Aigul) | `erkak` (Daulet)

**`tezlik`:** `-15%` (sekin) | `-5%` (normal) | `+10%` (tez)

**Response:**
```json
{
  "mavzu": "investitsiya",
  "kk_matn": "## Statistika\n**Investitsiya** (2025-jıl)...",
  "audio_url": "/voice/listen/abc123.mp3",
  "ovoz": "ayol",
  "format": "mp3"
}
```

### Audio tinglash
```http
GET /voice/listen/{fayl_nomi}.mp3
```
`audio_url` dagi qiymatni ishlatish kifoya.

**Frontend misoli:**
```javascript
const res = await fetch('/voice/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ mavzu: 'investitsiya', ovoz: 'ayol', year: 2025 })
});
const data = await res.json();
const audio = new Audio(data.audio_url);
audio.play();
```

---

## 5. Tizim

```http
GET /health
```
```json
{ "status": "ok", "gpu": true, "gpu_name": "NVIDIA GeForce RTX 4050 Laptop GPU" }
```

```http
GET /
```
```json
{
  "xizmat": "Qaraqalpaqstan Ekonomikalıq Monitoring API",
  "versiya": "1.0.0",
  "hujjat": "/docs"
}
```

---

## Frontend React misollari

```javascript
const API = 'http://localhost:8000';

// Dashboard ma'lumotlarini olish
const getDashboard = async (year = 2025) => {
  const res = await fetch(`${API}/analytics/dashboard?year=${year}`);
  return res.json();
};

// Ko'rsatkich qo'shish
const addIndicator = async (data) => {
  const res = await fetch(`${API}/indicators/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return res.json();
};

// AI soraw
const askAI = async (soraw, year) => {
  const res = await fetch(`${API}/analytics/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ soraw, year })
  });
  return res.json();
};

// Ovozli javob
const getVoice = async (mavzu, year) => {
  const res = await fetch(`${API}/voice/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mavzu, ovoz: 'ayol', year })
  });
  const data = await res.json();
  new Audio(data.audio_url).play();
};

// Excel yuklash
const uploadExcel = async (file) => {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API}/indicators/bulk-upload`, {
    method: 'POST',
    body: form
  });
  return res.json();
};
```

---

## Status kodlar

| Kod | Ma'no |
|-----|-------|
| 200 | Muvaffaqiyatli |
| 400 | Noto'g'ri so'rov |
| 404 | Topilmadi |
| 500 | Server xatosi |
