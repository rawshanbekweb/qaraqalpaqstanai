# -*- coding: utf-8 -*-
"""
map.txt (Qoraqalpog'iston SVG) -> frontend/src/data/districts.ts

SVG ichidagi 17 ta <path> hech qanday id/nom tutmaydi. Ular geometriya
(maydon, markaz, qo'shnichilik) asosida aniqlangan va quyidagi PATH_ORDER
ro'yxatida qat'iy tartibda saqlanadi. Agar biror tuman noto'g'ri belgilangan
bo'lsa - faqat shu ro'yxatdagi indeksni almashtiring va skriptni qayta ishga
tushiring.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "map.txt")
OUT = os.path.join(ROOT, "frontend", "src", "data", "districts.ts")

# path indeksi -> tuman
PATH_ORDER = {
    6: ("qongirot", "Qo'ng'irot", "Кунград", "Qo'ng'irot", 78700, 130.4),
    11: ("moynoq", "Mo'ynoq", "Муйнак", "Mo'ynoq", 37600, 30.2),
    2: ("taxtakopir", "Taxtako'pir", "Тахтакупыр", "Taxtako'pir", 20100, 40.7),
    1: ("tortkol", "To'rtko'l", "Турткуль", "To'rtko'l", 7900, 220.6),
    7: ("karaozak", "Qorao'zak", "Караузяк", "Qorao'zak", 5800, 60.3),
    13: ("ellikqala", "Ellikqal'a", "Элликкала", "Bo'ston", 4900, 155.8),
    15: ("beruniy", "Beruniy", "Беруни", "Beruniy", 4000, 205.1),
    14: ("bozatov", "Bo'zatov", "Бозатау", "Bo'zatov", 3000, 20.4),
    5: ("chimboy", "Chimboy", "Чимбай", "Chimboy", 3000, 120.9),
    16: ("amudaryo", "Amudaryo", "Амударья", "Mang'it", 2300, 200.3),
    12: ("kegeyli", "Kegeyli", "Кегейли", "Kegeyli", 2200, 90.5),
    10: ("nukus-tumani", "Nukus tumani", "Нукусский район", "Oqmang'it", 2000, 55.7),
    0: ("xojayli", "Xo'jayli", "Ходжейли", "Xo'jayli", 1300, 165.2),
    8: ("qanlikol", "Qanliko'l", "Канлыкуль", "Qanliko'l", 900, 45.6),
    4: ("shumanay", "Shumanay", "Шуманай", "Shumanay", 800, 55.1),
    9: ("nukus-shahri", "Nukus shahri", "город Нукус", "Nukus", 220, 335.8),
    3: ("taxiatosh", "Taxiatosh", "Тахиаташ", "Taxiatosh", 200, 45.9),
}

TOKEN = re.compile(r"([MLHVZmlhvz])|(-?\d*\.?\d+(?:e-?\d+)?)")


def path_points(d):
    """M/L/H/V/Z (absolute) path -> subpath ro'yxati."""
    subs, cur = [], []
    cmd = None
    buf = []
    x = y = 0.0
    for m in TOKEN.finditer(d):
        if m.group(1):
            c = m.group(1)
            if c in "Zz":
                if cur:
                    subs.append(cur)
                    cur = []
            elif c in "Mm" and cur:
                subs.append(cur)
                cur = []
            cmd = c
            buf = []
            continue
        buf.append(float(m.group(2)))
        if cmd in ("M", "L") and len(buf) == 2:
            x, y = buf
            cur.append((x, y))
            buf = []
            if cmd == "M":
                cmd = "L"
        elif cmd == "H" and len(buf) == 1:
            x = buf[0]
            cur.append((x, y))
            buf = []
        elif cmd == "V" and len(buf) == 1:
            y = buf[0]
            cur.append((x, y))
            buf = []
    if cur:
        subs.append(cur)
    return subs


def signed_area(p):
    a = 0.0
    for i in range(len(p)):
        x0, y0 = p[i]
        x1, y1 = p[(i + 1) % len(p)]
        a += x0 * y1 - x1 * y0
    return a / 2.0


def inside(p, px, py):
    c = False
    n = len(p)
    j = n - 1
    for i in range(n):
        xi, yi = p[i]
        xj, yj = p[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi:
            c = not c
        j = i
    return c


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    ex, ey = ax + t * dx, ay + t * dy
    return ((px - ex) ** 2 + (py - ey) ** 2) ** 0.5


def pole_of_inaccessibility(p, steps=48):
    """Yorliq uchun ko'rinadigan markaz - poligon ichidagi eng 'chuqur' nuqta."""
    xs = [a for a, _ in p]
    ys = [b for _, b in p]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    best, bx, by = -1.0, (x0 + x1) / 2, (y0 + y1) / 2
    for i in range(steps + 1):
        for j in range(steps + 1):
            px = x0 + (x1 - x0) * i / steps
            py = y0 + (y1 - y0) * j / steps
            if not inside(p, px, py):
                continue
            d = min(
                seg_dist(px, py, p[k][0], p[k][1], p[(k + 1) % len(p)][0], p[(k + 1) % len(p)][1])
                for k in range(len(p))
            )
            if d > best:
                best, bx, by = d, px, py
    return round(bx, 1), round(by, 1)


def main():
    svg = open(SRC, encoding="utf-8").read()
    view = re.search(r'viewBox="([^"]+)"', svg).group(1)
    paths = re.findall(r'<path d="([^"]+)"', svg)
    assert len(paths) == 17, f"kutilgan 17 ta path, topildi {len(paths)}"

    rows = []
    for idx in sorted(PATH_ORDER, key=lambda k: PATH_ORDER[k][1]):
        slug, name, name_ru, center, area_km2, pop = PATH_ORDER[idx]
        d = paths[idx]
        subs = [s for s in path_points(d) if len(s) >= 3]
        main_poly = max(subs, key=lambda s: abs(signed_area(s)))
        lx, ly = pole_of_inaccessibility(main_poly)
        xs = [a for a, _ in main_poly]
        ys = [b for _, b in main_poly]
        rows.append(
            {
                "id": slug,
                "name": name,
                "nameRu": name_ru,
                "center": center,
                "areaKm2": area_km2,
                "population": pop,
                "labelX": lx,
                "labelY": ly,
                "bbox": [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)],
                "d": d,
            }
        )

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// AUTO-GENERATED — tools/gen_districts.py (manba: map.txt). Qo'lda tahrirlamang.\n")
        f.write("export interface District {\n")
        f.write("  id: string;\n  name: string;\n  nameRu: string;\n  center: string;\n")
        f.write("  areaKm2: number;\n  population: number;\n")
        f.write("  labelX: number;\n  labelY: number;\n")
        f.write("  bbox: [number, number, number, number];\n  d: string;\n}\n\n")
        f.write(f'export const MAP_VIEWBOX = "{view}";\n\n')
        f.write("export const DISTRICTS: District[] = [\n")
        for r in rows:
            f.write("  {\n")
            for k in ("id", "name", "nameRu", "center"):
                f.write(f'    {k}: {json.dumps(r[k], ensure_ascii=False)},\n')
            f.write(f'    areaKm2: {r["areaKm2"]},\n')
            f.write(f'    population: {r["population"]},\n')
            f.write(f'    labelX: {r["labelX"]},\n    labelY: {r["labelY"]},\n')
            f.write(f'    bbox: {json.dumps(r["bbox"])},\n')
            f.write(f'    d: {json.dumps(r["d"])},\n')
            f.write("  },\n")
        f.write("];\n\n")
        f.write("export const DISTRICT_BY_ID = Object.fromEntries(\n")
        f.write("  DISTRICTS.map((d) => [d.id, d]),\n) as Record<string, District>;\n")

    print(f"yozildi: {OUT}  ({len(rows)} tuman)")
    for r in rows:
        print(f'  {r["id"]:14s} {r["name"]:14s} label=({r["labelX"]},{r["labelY"]})')


if __name__ == "__main__":
    main()
