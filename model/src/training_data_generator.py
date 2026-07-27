"""
Karakalpak Training Data Generator
====================================
Ekonomikalıq maǵlıwmatlardan Qwen3 ushın
Karakalpaksha Q&A juftliklar jaratıw.

Formatı: ShareGPT  →  {"conversations": [{"from":"human","value":...},{"from":"gpt","value":...}]}
"""

import os, json, re, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR    = os.path.join(os.path.dirname(__file__), "..", "data")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

SYSTEM_PROMPT = """Sen Qaraqalpaqstan Respublikasınıń ekonomika ekspertisen.
Senden soralan barlıq sorawlarga tek Qaraqalpaq tilinde, anıq statistikalıq maǵlıwmatlarǵa
tiykarlanıp professional ekonomikalıq stilde juwap beriw kerek.
Juwap strukturası: Statistika → Analiz → Muammo → Usınıs → Juwmaq."""


# ─────────────────────────────────────────────────────────────
#  MAǴLÍWMAT JÚKLEW
# ─────────────────────────────────────────────────────────────
def _find(keyword):
    for root, _, files in os.walk(DATA_DIR):
        for f in files:
            if keyword.lower() in f.lower() and f.endswith(".xlsx"):
                return os.path.join(root, f)
    return None

def _safe(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    s = str(v).strip().replace(",", ".").replace(" ", "")
    if s in ("nan","NaN","x","х","-","","None"):
        return None
    try:
        return float(s)
    except:
        return None

def load_macro_dict():
    path = _find("Makroekonomikalıq")
    if not path: return {}
    raw = pd.read_excel(path, header=None)

    years = {}
    for ci, v in enumerate(raw.iloc[2]):
        s = str(v).strip() if pd.notna(v) else ""
        if s.startswith("20"):
            try: years[ci] = int(s[:4])
            except: pass

    KOR = {
        "Jalpı aymaqlıq ónim":           "JAO",
        "Sanaat ónimi":                   "Sanaat",
        "Awıl, toğay hám balıqshilıq":   "AwılXojalıǵı",
        "Tiykarǵı kapitalǵa investitsiyalar": "Investitsiya",
        "Qurılıs jumısları":             "Qurılıs",
        "Eksport":                        "Eksport",
        "Import":                         "Import",
        "Xızmetler, jámi":               "Xızmetler",
        "Usaqlap satıw sawda tovar":     "SawdaAylanbası",
        "Saldo":                          "Saldo",
    }
    data = {}; cur = None
    for _, row in raw.iterrows():
        cell = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        unit = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        for key, short in KOR.items():
            if key in cell:
                cur = short; break
        if cur and ("mlrd" in unit.lower() or "mln" in unit.lower()):
            if cur not in data:
                vals = {}
                for ci, y in years.items():
                    fv = _safe(row.iloc[ci])
                    if fv: vals[y] = fv
                if vals: data[cur] = vals
    return data

def load_unemp_dict():
    path = _find("Ekonomikalıq aktiv")
    if not path: return {}
    raw = pd.read_excel(path, header=None)
    yr_cols = {}
    for ci, v in enumerate(raw.iloc[2]):
        s = str(v).strip() if pd.notna(v) else ""
        if s.startswith("20"):
            try: yr_cols[ci] = int(s[:4])
            except: pass
    CHUNK = 4
    RAYON = {
        "Qoraqalpog'iston Respublikasi": "QR jámi",
        "Nukus sh.": "Nukus qalası", "Amudaryo": "Amudarya",
        "Beruniy": "Beruniy", "Kegeyli": "Kegeyli",
        "Qo'ng'irot": "Qońırat", "Mo'ynoq": "Mójnak",
        "Chimboy": "Shımbay", "Taxiatosh": "Taxiatash",
        "Taxtako'pir": "Taxtakópir", "Ellikqal'a": "Ellikqala",
    }
    data = {}
    for _, row in raw.iterrows():
        c0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        for orig, kk in RAYON.items():
            if orig in c0:
                for ci, y in yr_cols.items():
                    vals = [_safe(row.iloc[ci+i]) for i in range(CHUNK)]
                    if all(v is not None for v in vals):
                        data.setdefault(kk, {})[y] = {
                            "aktiv": vals[0], "bant": vals[1],
                            "jumissiz": vals[2], "pati": vals[3]
                        }
                break
    return data


# ─────────────────────────────────────────────────────────────
#  Q&A JARATIWSHÍ FUNKSIYALAR
# ─────────────────────────────────────────────────────────────
def make_qa(q: str, a: str) -> dict:
    return {"conversations": [
        {"from": "system",  "value": SYSTEM_PROMPT},
        {"from": "human",   "value": q},
        {"from": "gpt",     "value": a},
    ]}


def gen_jao_qa(macro: dict) -> list:
    samples = []
    jao = macro.get("JAO", {})
    if not jao: return []
    yrs = sorted(jao.keys())
    last, prev = yrs[-1], yrs[-2]
    osim = (jao[last] - jao[prev]) / jao[prev] * 100

    samples.append(make_qa(
        f"Qaraqalpaqstan Respublikasında {last}-jılǵı JAÓ kórsetkishi qansha?",
        f"""## Statistika
{last}-jılda Qaraqalpaqstan Respublikasınıń Jalpı Aymaqlıq Ónimi **{jao[last]:,.1f} mlrd. som** bolıp, {prev}-jılǵa salıstırǵanda **+{osim:.1f}%** ósim kórsetti ({prev}-jıl: {jao[prev]:,.1f} mlrd. som).

## Analiz
JAÓ dinamikasın salıstırsaq:
- {yrs[-3]}-jıl: {jao.get(yrs[-3],0):,.1f} mlrd. som
- {prev}-jıl: {jao[prev]:,.1f} mlrd. som
- {last}-jıl: {jao[last]:,.1f} mlrd. som

## Muammo
Ósim tempi beqarar — sırtqı sawda saldosınıń kemeyiwi hám investitsiya aktivliginiń pasayıwı jalpı ósimdi tómenletiwi múmkin.

## Usınıs
**Qısqa múddet:** Eksport kólemini artırıw, import almashtırıw siyasatın kúsheytiw.
**Orta múddet:** Sanaat hám xızmetler sektorının úlesi kóbeytilsin.
**Uzaq múddet:** Jan basına JAÓ kórsetkishin Ózbekstan ortasha dáreyesine jetkertiw.

## Juwmaq
{last}-jılda JAÓ {jao[last]:,.1f} mlrd. somǵa jetti — bul on jılda eń joqarı kórsetkish."""
    ))

    # Dinamika sorawi
    yrs5 = yrs[-5:]
    table = "\n".join([f"- {y}: {jao[y]:,.1f} mlrd. som" for y in yrs5])
    samples.append(make_qa(
        "JAÓ sońǵı 5 jıldaǵı ósim dinamikasın kórset",
        f"""## Statistika
Sońǵı 5 jılda Jalpı Aymaqlıq Ónimi:

{table}

## Analiz
{yrs5[-1]}-jılda JAÓ {yrs5[0]}-jılǵa salıstırǵanda **{(jao[yrs5[-1]]-jao[yrs5[0]])/jao[yrs5[0]]*100:.1f}%** artıp, {jao[yrs5[-1]]/jao[yrs5[0]]:.1f} ese ósken.

## Juwmaq
Respublika ekonomikası barqarar ósim trayektoriyasında turiptı."""
    ))
    return samples


def gen_sanaat_qa(macro: dict) -> list:
    samples = []
    san = macro.get("Sanaat", {})
    if not san: return []
    yrs = sorted(san.keys())
    last = yrs[-1]
    samples.append(make_qa(
        f"{last}-jılda Qaraqalpaqstan Respublikasında sanaat ónimi kólemi qansha bolǵan?",
        f"""## Statistika
{last}-jılda sanaat ónimi kólemi **{san[last]:,.1f} mlrd. som** bolıp, sońǵı jıllar dinamikası:
- {yrs[-3]}: {san.get(yrs[-3],0):,.1f} mlrd. som
- {yrs[-2]}: {san.get(yrs[-2],0):,.1f} mlrd. som
- {last}: {san[last]:,.1f} mlrd. som

## Analiz
Sanaattıń tiykarǵı tarmaqları: ximiya ónimleri, azıq-awqat, toqımashılıq, elektr-energetika.

## Muammo
Ximiya sanaatı ósimi 2019-jıldan bastawlap baylawsızlasqan. Basqa tarmaqlar rawajlanıwı zárúr.

## Usınıs
**Qısqa múddet:** Ximiya zavodlarının quwatin arttırıw.
**Orta múddet:** Toqımashılıq hám azıq-awqat tarmaqların kengeytiw.

## Juwmaq
Sanaat sektori respublika JAÓnıń tiykarǵı bólegini quraydı hám dawamlı investitsiyalardı talap etedi."""
    ))
    return samples


def gen_unemp_qa(unemp: dict) -> list:
    samples = []
    qr = unemp.get("QR jámi", {})
    if not qr: return []
    yrs = sorted(qr.keys())
    last, prev = yrs[-1], yrs[-2]
    cur  = qr[last]
    prv  = qr[prev]

    samples.append(make_qa(
        f"Qaraqalpaqstan Respublikasında {last}-jılda jumıssızlıq dárejesi qansha?",
        f"""## Statistika
{last}-jılda Qaraqalpaqstan Respublikasında:
- Ekonomikalıq aktiv xalıq: **{cur['aktiv']:,.1f} mıń adam**
- Bántler: **{cur['bant']:,.1f} mıń adam**
- Jumıssızlar: **{cur['jumissiz']:,.1f} mıń adam**
- Jumıssızlıq dárejesi: **{cur['pati']:.2f}%**

{prev}-jılǵa salıstırǵanda: {prv['pati']:.2f}% → {cur['pati']:.2f}% ({'+' if cur['pati']>prv['pati'] else ''}{cur['pati']-prv['pati']:.2f}%)

## Analiz
Jumıssızlıq dárejesi {max(qr,key=lambda y: qr[y]['pati'])}-jılǵı {max(qr[y]['pati'] for y in qr):.1f}% dıń ústinen kemeyip atır.

## Muammo
Rayon arasındaǵı ten-teńsizlik saqlanbaqta. Shóllestirip ketken rayonlarda jumıssızlıq joqarı.

## Usınıs
**Qısqa múddet:** Kásip-óner oqıtıw markazların ashıw.
**Orta múddet:** Kishi biznes hám fermer xojalıqlarına qollap-quwatlaw.

## Juwmaq
Jumıssızlıq dárejesi azayıp atır, biraq rayon arasındaǵı ten-teńsizlik máselesi qalaqlı turiptı."""
    ))

    # Rayon salistirmasi
    rayon_last = {r: unemp[r][last]["pati"]
                  for r in unemp if last in unemp[r] and r != "QR jámi"}
    if rayon_last:
        sorted_r = sorted(rayon_last.items(), key=lambda x: x[1], reverse=True)
        top3 = sorted_r[:3]; bot3 = sorted_r[-3:]
        samples.append(make_qa(
            f"{last}-jılda qaysı rayonlarda jumıssızlıq eń joqarı hám eń tómen?",
            f"""## Statistika
**Eń joqarı jumıssızlıq rayonları ({last}-jıl):**
""" + "\n".join([f"{i+1}. {r}: **{v:.2f}%**" for i,(r,v) in enumerate(top3)]) + """

**Eń tómen jumıssızlıq rayonları:**
""" + "\n".join([f"{i+1}. {r}: **{v:.2f}%**" for i,(r,v) in enumerate(bot3)]) + f"""

## Analiz
Rayonlar arasında {sorted_r[0][1]-sorted_r[-1][1]:.2f}% ten-teńsizlik bar.

## Muammo
Geografiyalıq ten-teńsizlik ekonomikalıq ósimdi tósenletip atır.

## Usınıs
Álsiz rayonlarda arnawlı ekonomikalıq rawajlandırıw joybarlarin islep shıǵıw zárúr.

## Juwmaq
Rayon arasındaǵı ten-teńsizlikti joq etiw — respublikanıń tiykarǵı prioriteti bolıwı kerek."""
        ))
    return samples


def gen_trade_qa(macro: dict) -> list:
    samples = []
    exp = macro.get("Eksport", {}); imp = macro.get("Import", {})
    sal = macro.get("Saldo", {})
    if not exp: return []
    yrs = sorted(set(exp) & set(imp))
    if len(yrs) < 2: return []
    last = yrs[-1]
    samples.append(make_qa(
        f"Qaraqalpaqstan Respublikasınıń {last}-jıldaǵı sırtqı sawda kórsetkishlerini ayting",
        f"""## Statistika
{last}-jılda Qaraqalpaqstan Respublikasınıń sırtqı sawdası:
- **Eksport:** {exp[last]:,.1f} mln. AQSh. dollar
- **Import:** {imp[last]:,.1f} mln. AQSh. dollar
- **Saldo:** {sal.get(last,0):+,.1f} mln. AQSh. dollar

## Analiz
{'Eksport import dan asqın — sawda balansi musbat.' if sal.get(last,0) > 0 else 'Import eksporttı artqan — sawda balansi mánfiy. Bul valuta tańshılıǵına alıp keliwi múmkin.'}

## Muammo
{'Eksport beqarar — ximiya ónimleri bahalarınıń ózgeriwine táweldi.' if exp[last] < 500 else 'Eksport dúzilimi diversifikatsiya talap etedi.'}

## Usınıs
**Qısqa múddet:** Toqımashılıq hám azıq-awqat eksportın artırıw.
**Orta múddet:** Jańa sherik mámleketler tabıw.

## Juwmaq
Sırtqı sawda balansin musbat saqlawda sistemalı jumıs zárúr."""
    ))
    return samples


def gen_invest_qa(macro: dict) -> list:
    samples = []
    inv = macro.get("Investitsiya", {})
    if not inv: return []
    yrs = sorted(inv.keys())
    last = yrs[-1]
    osim = (inv[last] - inv[yrs[-2]]) / inv[yrs[-2]] * 100
    samples.append(make_qa(
        f"Qaraqalpaqstanda {last}-jılda tiykarǵı kapitalǵa investitsiyalar ósim dinánikası qalay?",
        f"""## Statistika
{last}-jılda tiykarǵı kapitalǵa investitsiyalar: **{inv[last]:,.1f} mlrd. som**
Ósim: **{osim:+.1f}%** ({yrs[-2]}-jıl: {inv[yrs[-2]]:,.1f} mlrd. som)

## Analiz
{yrs[0]}-jıldan {last}-jılǵa shekem investitsiyalar {inv[last]/inv[yrs[0]]:.0f} esege artqan.

## Muammo
Investitsiya aktivligi beqarar — 2016-2017-jıllarda keskin kemeydi. Tısqarıdan kelgen investitsiyalar úlesi az.

## Usınıs
**Qısqa múddet:** Erkin ekonomikalıq zonalar jaratıw.
**Orta múddet:** PPP (mámleketlik-járdem sherigestigi) joybarlarin kóbeytıw.
**Uzaq múddet:** 2030-jılǵa shekem jan basına investitsiya {inv[last]/inv[yrs[0]]:.0f} ese artırıw.

## Juwmaq
Investitsiya aktivligi ósip atır, biraq tısqarı investorlarǵa qulayshılıqlar jaratıw zárúr."""
    ))
    return samples


def gen_xizmet_qa(macro: dict) -> list:
    samples = []
    xiz = macro.get("Xızmetler", {})
    if not xiz: return []
    yrs = sorted(xiz.keys())
    last = yrs[-1]
    osim = (xiz[last] - xiz[yrs[-2]]) / xiz[yrs[-2]] * 100
    samples.append(make_qa(
        f"Qaraqalpaqstanda xızmetler sektori qanday rawajlanıwda?",
        f"""## Statistika
{last}-jılda xızmetler kólemi: **{xiz[last]:,.1f} mlrd. som**
Ósim: **{osim:+.1f}%** ({yrs[-2]}-jıl: {xiz[yrs[-2]]:,.1f} mlrd. som)

## Analiz
Xızmetler sektori tarmaqları:
- Transport xızmeti — tiykarǵı bólim
- Finanslıq xızmetler — tez ósip atır
- Sawda, jasaw, awqatlanıw — turizmde potensial bar

## Muammo
Sanaat qalaqlı sektorgatan xızmetler ekonomikası suwısha barmaǵan.

## Usınıs
**Qısqa múddet:** Turizm infrastrukturasın rawajlandırıw (Moynaq, Sudochi kólı).
**Orta múddet:** IT xızmetler hám raqamlashtırıw sektorın kúsheytiw.

## Juwmaq
Xızmetler sektori barǵan sayın ósip atır hám keleshekde tiykarǵı ósim dáregine aylanıwı múmkin."""
    ))
    return samples


def gen_awil_qa(macro: dict) -> list:
    samples = []
    awil = macro.get("AwılXojalıǵı", {})
    if not awil: return []
    yrs = sorted(awil.keys())
    last = yrs[-1]
    samples.append(make_qa(
        f"Qaraqalpaqstanda awıl xojalıǵınıń jaqında jıllardaǵı rawajlanıwı haqqında aytıp bering",
        f"""## Statistika
{last}-jılda awıl xojalıǵı ónimleri: **{awil[last]:,.1f} mlrd. som**

Sońǵı jıllar dinamikası:
""" + "\n".join([f"- {y}: {awil[y]:,.1f} mlrd. som" for y in yrs[-4:]]) + """

## Analiz
Awıl xojalıǵı eki tarmaqtan ibarat:
- **Dıyqanshılıq** — paxta, bugday, sabzawatlar
- **Sharwashılıq** — qara mal, qoy, echki

## Muammo
- Aral teńiziniń qurıwı nátiyjesinde topıraq sho'rlanıwı artqan
- Suw tańshılıǵı hám Amúdárya suwının azayıwı
- Egin maydanı kemeyip atır (2010: 265 750 ga → 2025: 261 965 ga)

## Usınıs
**Qısqa múddet:** Tomshılap suwlaw texnologiyaların engiziw.
**Orta múddet:** Organikalıq ónimler eksportın rawajlandırıw.
**Uzaq múddet:** Aral atırapında ekologiyalıq qalıpqa keltiriw.

## Juwmaq
Awıl xojalıǵı sektori ósip atır, biraq ekologiyalıq máseleler tósenlet bolıp atır."""
    ))
    return samples


def gen_isbilermenlik_qa() -> list:
    return [make_qa(
        "Qaraqalpaqstanda kishi isbilermenlik rawajlanıwı haqqında neler aytıw múmkin?",
        """## Statistika
Kishi isbilermenlik subyektleri sanı jıldan-jılǵa ósip atır. Tiykarǵı tarmaqlar:
- Sawda hám xızmet kórsetiw
- Awıl xojalıǵı hám ishki islerge xizmet
- Qurilish hám kóshpes múlk

## Analiz
Kishi isbilermenlik respublika bántilik strukturasında mazmunlı úlesh aladı hám jańa jumıs orinlari jaratyatir.

## Muammo
- Finanslawǵa qolayshılıq kem
- Administrativ tosqınlıqlar kóp
- Bazar infrastrukturasınıń rawajlanıwı jetispeywdi

## Usınıs
**Qısqa múddet:** Mikrokreditler hám grantlar beриw dasturların kengeytiw.
**Orta múddet:** Inkubatorlar hám texnoparklar ashıw.

## Juwmaq
Kishi isbilermenlik respublika ekonomikasınıń tiykarǵı ósim dáregine aylanıwı ushın sistemalı qollap-quwatlaw zárúr."""
    )]


def gen_general_qa(macro: dict) -> list:
    """Ulıwma ekonomikalıq sorawlar."""
    samples = []

    # Sektor salistirmasi
    jao  = macro.get("JAO",  {})
    san  = macro.get("Sanaat", {})
    awil = macro.get("AwılXojalıǵı", {})
    xiz  = macro.get("Xızmetler", {})

    common = set(jao) & set(san) & set(awil) & set(xiz)
    if common:
        last = max(common)
        san_ul  = san[last]  / jao[last] * 100
        awil_ul = awil[last] / jao[last] * 100
        xiz_ul  = xiz[last]  / jao[last] * 100
        samples.append(make_qa(
            f"{last}-jılda Qaraqalpaqstan ekonomikasınıń sektor quramı qanday?",
            f"""## Statistika
{last}-jılda JAÓ quramı:
- Sanaat:        **{san_ul:.1f}%** ({san[last]:,.1f} mlrd. som)
- Awıl xojalıǵı: **{awil_ul:.1f}%** ({awil[last]:,.1f} mlrd. som)
- Xızmetler:     **{xiz_ul:.1f}%** ({xiz[last]:,.1f} mlrd. som)

## Analiz
{'Sanaat tiykarǵı sektor bolıp qalaqlı.' if san_ul > awil_ul else 'Awıl xojalıǵı hám xızmetler sektori birgelikte sanaatqa teng keldi.'}

## Muammo
Sektor diversifikatsiyası jetispeywdi — bir sektordıń pasayıwı ulıwma ekonomikaǵa kúshli tásir etedi.

## Usınıs
IT, turizm hám qayta tikleniwshi energetika sektorların rawajlandırıw arqalı diversifikatsiyalanıw kerek.

## Juwmaq
Ekonomika quramı salmaqlı rawajlanıw ushın diversifikatsiya talap etedi."""
        ))

    samples.append(make_qa(
        "Qaraqalpaqstan Respublikasınıń ekonomikasında eń úlken muammolar qaysilar?",
        """## Statistika
Tiykarǵı muammolar maǵlıwmatlarǵa tiykarlanıp:
1. Aral teńiziniń qurıwı — awıl xojalıǵı maydanı azayıwda
2. Sırtqı sawda saldosınıń 2026-jılda mánfiy bolıwı (-14 mln.$)
3. Rayon arasındaǵı ten-teńsizlik — jumıssızlıq 4.6-5.5% arasında
4. Eksport beqararlıǵı — ximiya bahalarına táweldilik

## Analiz
Bul muammolar bir-biri menen baylanısqan:
- Ekologiyalıq máseleler → awıl xojalıǵı → eksport → saldo

## Muammo
Strukturalıq ózgeriwler bolmasa, ulıwma ósim dárejesi sekinlasıwı múmkin.

## Usınıs
**Qısqa múddet:** Import almashtırıw hám eksport artırıw.
**Orta múddet:** Ekologiyalıq rekultivatsiya, suw tásirshenligi.
**Uzaq múddet:** Diversifikatsiya hám jańa ósim bólimlerin rawajlandırıw.

## Juwmaq
Sistemalı, koordinatsiyalanǵan siyasat arqalı bul muammolardı sheshiw múmkin."""
    ))

    return samples


# ─────────────────────────────────────────────────────────────
#  TOLÍQ DATASET JARATIW
# ─────────────────────────────────────────────────────────────
def generate_all(output_path: str = None) -> list:
    if output_path is None:
        output_path = os.path.join(RESULTS_DIR, "karakalpak_training_data.json")

    print("Maǵlıwmatlar júkleniwde...")
    macro = load_macro_dict()
    unemp = load_unemp_dict()
    print(f"  Makro: {len(macro)} kórsetkish  |  Unemp: {len(unemp)} rayon")

    all_samples = []
    all_samples += gen_jao_qa(macro)
    all_samples += gen_sanaat_qa(macro)
    all_samples += gen_unemp_qa(unemp)
    all_samples += gen_trade_qa(macro)
    all_samples += gen_invest_qa(macro)
    all_samples += gen_xizmet_qa(macro)
    all_samples += gen_awil_qa(macro)
    all_samples += gen_isbilermenlik_qa()
    all_samples += gen_general_qa(macro)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_samples, f, ensure_ascii=False, indent=2)

    print(f"\nJámi: {len(all_samples)} Q&A juftlik saqlandı → {output_path}")
    for i, s in enumerate(all_samples, 1):
        q = s["conversations"][1]["value"][:60]
        print(f"  {i:2d}. {q}...")
    return all_samples


def gen_extra_qa(macro: dict, unemp: dict) -> list:
    """Qosimsha Q&A — rayonlar, taqqoslash, muammolar."""
    samples = []
    jao  = macro.get("JAO",  {})
    inv  = macro.get("Investitsiya", {})
    exp  = macro.get("Eksport", {})
    imp  = macro.get("Import", {})
    san  = macro.get("Sanaat", {})
    awil = macro.get("AwılXojalıǵı", {})
    xiz  = macro.get("Xızmetler", {})
    qur  = macro.get("Qurılıs", {})

    yrs = sorted(jao.keys()) if jao else []

    # ── Investitsiya dinamikasi ──
    if inv and len(sorted(inv)) >= 3:
        iv = sorted(inv.keys())
        samples.append(make_qa(
            "Investitsiya kórsatkishi sońǵı jıllarda qanday ózgerdi?",
            f"""## Statistika
Tiykarǵı kapitalǵa investitsiyalar dinamikası:
- {iv[-4]}: {inv.get(iv[-4],0):,.1f} mlrd. som
- {iv[-3]}: {inv.get(iv[-3],0):,.1f} mlrd. som
- {iv[-2]}: {inv.get(iv[-2],0):,.1f} mlrd. som
- {iv[-1]}: {inv.get(iv[-1],0):,.1f} mlrd. som

## Analiz
{iv[-1]}-jılda investitsiyalar {iv[-4]}-jılǵa salıstırǵanda {inv.get(iv[-1],1)/max(inv.get(iv[-4],1),1)*100:.0f}% ne jetti. Ósim tempi barqarar.

## Muammo
Tısqarıdan keliwshi investitsiyalar úlesi hám az. Investitsiya strukturası kengeyiwi kerek.

## Usınıs
**Qısqa múddet:** Erkin ekonomikalıq zonalar arqalı tısqarı investorlar tartıw.
**Orta múddet:** Qurılıs hám infrastruktura joybarlarina qarjılandırıwdı artırıw.
**Uzaq múddet:** Jan basına investitsiya kórsetkishin 3 ese artırıw.

## Juwmaq
Investitsiya ósimi barqarar, biraq tísqarı investorlarga qulayshılıqlar jaratıw zárúr."""
        ))

    # ── Qurılıs ──
    if qur:
        qv = sorted(qur.keys())
        last = qv[-1]
        samples.append(make_qa(
            f"Qaraqalpaqstanda {last}-jılda qurılıs jumısları kólemi qansha?",
            f"""## Statistika
{last}-jılda qurılıs jumısları kólemi: **{qur[last]:,.1f} mlrd. som**
Ósim: {qur[last]/qur.get(qv[-2],1)*100-100:+.1f}% ({qv[-2]}-jılǵa salıstırǵanda)

## Analiz
Qurılıs sektori investitsiya aktivliginiń kórsetkishi bolıp esaplanadı.
Bul kórsetkish JAÓ nıń {qur[last]/jao.get(last,1)*100:.1f}% in quraydı.

## Muammo
Qurılıs materialları importqa táweldi, bul bahalar ósimshıligine alıp keliwi múmkin.

## Usınıs
**Qısqa múddet:** Jergilikli qurılıs materialları ishlab shıǵarıwdı rawajlandırıw.
**Orta múddet:** Turaq-jay qurılısına sociallıq grantlar beriw.

## Juwmaq
Qurılıs sektori aktiv ósip atır — bul infrastruktura rawajlanıwınıń belgisi."""
        ))

    # ── Eksport vs Import saldo ──
    if exp and imp:
        common = sorted(set(exp) & set(imp))
        if common:
            last = common[-1]
            saldo = exp[last] - imp[last]
            samples.append(make_qa(
                "Eksport hám importtıń saldo kórsetkishi qanday?",
                f"""## Statistika
{last}-jılda sırtqı sawda:
- Eksport: {exp[last]:,.1f} mln. $
- Import: {imp[last]:,.1f} mln. $
- Saldo: **{saldo:+,.1f} mln. $** ({'artıqsha' if saldo > 0 else 'kemshilik'})

## Analiz
{'Eksport artıqsha — bul valuta tusiminin yaqshi korsatkichi.' if saldo > 0 else 'Import eksporttı artqan — bul valuta tusimiga salbiy tasir korsetadi.'}

## Muammo
Eksport strukturası ximiya onimleriga taweldi (beqarar). Import uchun sanoat jihozlari ulushi katta.

## Usınıs
**Qısqa múddet:** Eksport diversifikatsiyasini kuchaytirish — togimashilik, oziq-ovqat.
**Orta múddet:** Import almashtirish siyosatini joriy etish.

## Juwmaq
Sawda balansın musbat saqlawda sistemalı jumıs zárúr."""
            ))

    # ── Rayonlar jumissizligi ──
    rayonlar = [r for r in unemp.keys() if r != "QR jámi"]
    yils_unemp = set()
    for r in rayonlar:
        yils_unemp.update(unemp[r].keys())
    if yils_unemp:
        last_y = max(yils_unemp)
        ray_data = {r: unemp[r][last_y] for r in rayonlar if last_y in unemp[r]}
        if ray_data:
            best_r  = min(ray_data, key=lambda x: ray_data[x]["pati"])
            worst_r = max(ray_data, key=lambda x: ray_data[x]["pati"])

            for rayon in list(rayonlar)[:6]:
                if last_y not in unemp.get(rayon, {}):
                    continue
                rd = unemp[rayon][last_y]
                samples.append(make_qa(
                    f"{rayon} rayonında {last_y}-jılda jumıssızlıq dárejesi qansha?",
                    f"""## Statistika
{last_y}-jılda {rayon} rayonında:
- Ekonomikalıq aktiv xalıq: **{rd['aktiv']:,.1f} mıń adam**
- Bántler: **{rd['bant']:,.1f} mıń adam**
- Jumıssızlar: **{rd['jumissiz']:,.1f} mıń adam**
- Jumıssızlıq: **{rd['pati']:.2f}%**

## Analiz
{rayon} rayonı respublika ortasha ({unemp.get('QR jámi',{}).get(last_y,{}).get('pati',5):.2f}%) {'astında' if rd['pati'] < unemp.get('QR jámi',{}).get(last_y,{}).get('pati',5) else 'ústinde'} turıptı.

## Muammo
{'Jumıssızlıq ortasha dárejedey — qosimsha kuzatuv zarur emas.' if rd['pati'] < 7 else 'Jumıssızlıq joqarı — múddetli chara ko\'rish zarur.'}

## Usınıs
**Qısqa múddet:** Kásip-óner oqıtıw kursları.
**Orta múddet:** Kishi biznes rawajlandırıw qorı.

## Juwmaq
{rayon} jumıssızlıq kórsetkishi {'qonıqlı' if rd['pati'] < 7 else 'názerden ótkeriwdi talap etedi'}."""
                ))

            # Salistirma
            samples.append(make_qa(
                f"{last_y}-jılda rayonlar arasında jumıssızlıq salistirmasi",
                f"""## Statistika
{last_y}-jılda rayonlar arasında jumıssızlıq dárejesiniń salistirmasi:

Eń az jumıssızlıq:
- **{best_r}**: {ray_data[best_r]['pati']:.2f}%

Eń kóp jumıssızlıq:
- **{worst_r}**: {ray_data[worst_r]['pati']:.2f}%

Respublika ortasha: {unemp.get('QR jámi',{}).get(last_y,{}).get('pati',5):.2f}%

## Analiz
Rayonlar arasında {ray_data[worst_r]['pati'] - ray_data[best_r]['pati']:.2f}% ten-teńsizlik bar.

## Muammo
Geografiyalıq ten-teńsizlik — shóllestirip ketken rayonlarda isbilermenlilk infrastrukturası kem rawajlanǵan.

## Usınıs
**Orta múddet:** Álsiz rayonlarda arnawlı ekonomikalıq rawajlandırıw joybarlari.
**Uzaq múddet:** Barlamlıq jollar, sanaat kárxanalar, elektr energiya quwatı arttırıw.

## Juwmaq
Rayon arası ten-teńsizlikti kemeytiw — respublikanıń uzaq múddeetli ustuvorliği."""
            ))

    # ── Sanaat tarmaqları ──
    samples.append(make_qa(
        "Sanaattıń qaysı tarmaqları eń tez rawajlanıwda?",
        """## Statistika
Sanaat tarmaqlarınıń 2025-jıldaǵı tiykarǵı kórsetkishleri (mlrd. som):
- Ximiya ónimleri: 7 520 mlrd.
- Azıq-awqat ónimleri: 6 553 mlrd.
- Toqımashılıq ónimleri: 6 203 mlrd.
- Elektr, gaz, puw: 3 775 mlrd.

## Analiz
Toqımashılıq hám azıq-awqat sektorları eń tez ósip atır. Ximiya sanaatı dógerekli dárejede turiptı.

## Muammo
Ximiya sektori tásirshirek bolıwı múmkin — neft hám gaz bahalarına táweldiligi yuqori.

## Usınıs
**Qısqa múddet:** Toqımashılıq eksportını 20% ga artırıw.
**Orta múddet:** Farmatsevtika hám metallurgiya sektorların rawajlandırıw.
**Uzaq múddet:** Jańa texnologiyalıq tarmaqlar — IT, elektronika.

## Juwmaq
Toqımashılıq hám azıq-awqat sektorları Qaraqalpaqstanniń keleshek ósim ózelieri bolıwı múmkin."""
    ))

    # ── Awil xojaligi muammolari ──
    samples.append(make_qa(
        "Awıl xojalıǵında suw tańshılıǵı máselesi haqqında ne deyisiz?",
        """## Statistika
- Egin maydanı 2010: 265 750 gektar
- Egin maydanı 2025: 261 965 gektar (kemeydi: −3 785 ga)
- Amúdárya suwı: jıldan-jılǵa azayıp atır

## Analiz
Aral teńiziniń qurıwı awıl xojalıǵına kúshli tásir etip atır.
Topıraq sho'rlanıwı 30-40% egin maydanını paydalanıwǵa yaroqsız qılgan.

## Muammo
1. Suw tańshılıǵı — suv taksimi qayta kóriliwi zarur
2. Topıraq sho'rlanıwı — drenaj sistemasini yaxshilash kerak
3. Klimat ózgeriwi — quraqlıq dawam etip atır

## Usınıs
**Qısqa múddet:** Tomshılap suwlaw texnologiyaların barliqlashtirib engiziw.
**Orta múddet:** Duzlanǵan topıraqtı rekultivatsiya etiw joybarlari.
**Uzaq múddet:** Suw tásirshenligi strategiyasın islep shıǵıw (2040-jılǵa shekem).

## Juwmaq
Suw máselesi — Qaraqalpaqstan awıl xojalıǵı ushın birlemshi máselelerden biri. Sistemalı yondasuv zarur."""
    ))

    # ── JAO o'sish strategiyasi ──
    if jao and len(yrs) >= 3:
        samples.append(make_qa(
            "Qaraqalpaqstan JAÓ ni artırıw ushın qanday strategiya kerek?",
            f"""## Statistika
JAÓ dinamikası:
- {yrs[-3]}: {jao.get(yrs[-3],0):,.1f} mlrd. som
- {yrs[-2]}: {jao.get(yrs[-2],0):,.1f} mlrd. som
- {yrs[-1]}: {jao.get(yrs[-1],0):,.1f} mlrd. som

## Analiz
Sońǵı jılda ósim tempi: {(jao.get(yrs[-1],1)/jao.get(yrs[-2],1)-1)*100:.1f}%
Tiykarǵı ósim dárekleri: sanaat, xızmetler, awıl xojalıǵı.

## Muammo
- Eksport beqararlıǵı JAÓ ósimige tásir etip atır
- Jan basına JAÓ Ózbekstan ortashasından tómen
- Investitsiya aktivligi beqarar

## Usınıs
**Qısqa múddet:** Eksport hám sırtqı investitsiyalardı artırıw.
**Orta múddet:** Xızmetler sektori, turizma, IT rawajlandırıw.
**Uzaq múddet:** 2035-jılǵa shekem JAÓ ni 2 ese artırıw nısaw qoyıw.

## Juwmaq
JAÓ ósimi ushın diversifikatsiya hám investitsiya aktivligi tiykarǵı sharıt."""
        ))

    # ── Xizmatlar sektori ──
    if xiz:
        xv = sorted(xiz.keys())
        samples.append(make_qa(
            "Xızmetler sektorınıń qaysı tarmaqları eń joqarı ósim kórsetti?",
            f"""## Statistika
{xv[-1]}-jılda xızmetler kólemi: {xiz[xv[-1]]:,.1f} mlrd. som

Tiykarǵı tarmaqlar:
- Finanslıq xızmetler — eń tez ósiwde
- Transport xızmeti — úlken bólim
- Sawda hám jasaw xızmeti — barqarar ósim
- Bilimlendiriw xızmeti — ósip atır

## Analiz
Finanslıq xızmetler digitallashtırıw esabınan 2-ese artqan.
Transport xızmeti qurılıs aktivligi menen baylanıslı ósip atır.

## Muammo
IT xızmetler hám turizm sektorları kem rawajlanǵan — potensial bar.

## Usınıs
**Qısqa múddet:** Turizm infrastrukturasın rawajlandırıw (Mójnak kólı, Sudochi).
**Orta múddet:** IT park hám startap ekosistemasin qalaw.
**Uzaq múddet:** Xızmetler sektori úleshin JAÓ nıń 50% ına jetkiziw.

## Juwmaq
Xızmetler sektori barǵan sayın kúsheyip atır — IT hám turizma eń úlken potensial."""
        ))

    # ── Inflyatsiya ──
    samples.append(make_qa(
        "Qaraqalpaqstanda inflyatsiya dárejesi qanday kórsetkishlerde turıptı?",
        """## Statistika
Inflyatsiya kórsetkishleri jıldan-jılǵa ózgerip turıptı.
Tiykarǵı tásir etetuǵın faktorlar: import bahaları, energiya narxları, suw tanshiligi.

## Analiz
Sońǵı jıllarda inflyatsiya pressiasi tovarlar importına taweldilikten kelip shıǵıptı.
Azıq-awqat, energiya hám transport segmentlerinde baha osimi ko'zga tashlanadi.

## Muammo
- Import bahaları artıwı — import almashtırıw siyasatı zárúr
- Energiya bahası ósimi — jergilikli ishlab shıǵarıwdı artırıw kerek
- Sırtqı valuta kursı ózgeriwi

## Usınıs
**Qısqa múddet:** Strategik tovarlar zaxira fondi jaratıw.
**Orta múddet:** Jergilikli ishlab shıǵarıwdı qollap-quwatlaw.
**Uzaq múddet:** Energiya mustaqilligi uchun qayta tiklenuvchi manbalar.

## Juwmaq
Inflyatsiyani nazorat qilish uchun import almashtirish va mahalliy ishlab chiqarishni rivojlantirish zarur."""
    ))

    return samples


def generate_all(output_path: str = None) -> list:
    if output_path is None:
        output_path = os.path.join(RESULTS_DIR, "karakalpak_training_data.json")

    print("Maǵlıwmatlar júkleniwde...")
    macro = load_macro_dict()
    unemp = load_unemp_dict()
    print(f"  Makro: {len(macro)} kórsetkish  |  Unemp: {len(unemp)} rayon")

    all_samples = []
    all_samples += gen_jao_qa(macro)
    all_samples += gen_sanaat_qa(macro)
    all_samples += gen_unemp_qa(unemp)
    all_samples += gen_trade_qa(macro)
    all_samples += gen_invest_qa(macro)
    all_samples += gen_xizmet_qa(macro)
    all_samples += gen_awil_qa(macro)
    all_samples += gen_isbilermenlik_qa()
    all_samples += gen_general_qa(macro)
    all_samples += gen_extra_qa(macro, unemp)   # ← yangi

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_samples, f, ensure_ascii=False, indent=2)

    print(f"\nJámi: {len(all_samples)} Q&A juftlik → {output_path}")
    for i, s in enumerate(all_samples, 1):
        q = s["conversations"][1]["value"][:65]
        print(f"  {i:2d}. {q}...")
    return all_samples


if __name__ == "__main__":
    generate_all()
