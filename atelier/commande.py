"""Atelier JLF D'ICE — à partir d'une commande (photo originale du client + code atelier de la fiche),
génère : photo originale HD recadrée, version en dés HD, grille CSV et plan de fabrication PDF.
Usage : python3 commande.py --photo client.jpg --code JLFD-C61-R82-D10-Z8KX [--client "Prénom"] [--out dossier]"""
import argparse, csv, math, os, re, datetime
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFilter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, Color
from reportlab.lib.utils import ImageReader

ap = argparse.ArgumentParser()
ap.add_argument('--photo', required=True); ap.add_argument('--code', required=True)
ap.add_argument('--client', default=''); ap.add_argument('--out', default='')
A = ap.parse_args()
m = re.match(r'JLFD-C(\d+)-R(\d+)-D(\d+)-([A-Z0-9]+)$', A.code.strip().upper())
if not m: raise SystemExit('Code atelier illisible : ' + A.code)
C, R, DIE, REF = int(m[1]), int(m[2]), int(m[3]), m[4]
OUT = A.out or f'commande_{REF}'; os.makedirs(OUT, exist_ok=True)
N = C * R

# ---------- same conversion as the app ----------
src = ImageOps.exif_transpose(Image.open(A.photo)).convert('RGB')
iw, ih = src.size; ar = C / R
sw, sh = iw, iw / ar
if sh > ih: sh, sw = ih, ih * ar
sx, sy = (iw - sw) / 2, max(0, (ih - sh) / 2 - sh * .04)
crop = src.crop((round(sx), round(sy), round(sx + sw), round(sy + sh)))
crop.save(f'{OUT}/photo_originale_HD_{REF}.jpg', quality=95)
small = np.asarray(crop.resize((C, R), Image.BOX), dtype=np.float32) / 255
L = (.2126 * small[..., 0] + .7152 * small[..., 1] + .0722 * small[..., 2]).ravel()
srt = np.sort(L); lo, hi = srt[int(len(srt) * .02)], srt[int(len(srt) * .98)]
v = np.clip((L - lo) / max(.05, hi - lo), 0, 1) ** .85
G = np.where(v < .05, 0, np.minimum(6, 1 + np.floor(v * 6))).astype(int).reshape(R, C)
with open(f'{OUT}/grille_{REF}.csv', 'w', newline='') as f: csv.writer(f, delimiter=';').writerows(G.tolist())
CNT = {k: int((G == k).sum()) for k in range(7)}

# ---------- HD dice render ----------
PIPS = {0: [], 1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)], 4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
        5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)], 6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}
PX = max(28, min(48, 4200 // max(C, R)))
def tile(vv, s=PX, ss=4):
    S = s * ss; im = Image.new('RGB', (S, S), (6, 6, 8)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([S * .04, S * .04, S * .96, S * .96], radius=S * .16, fill=(20, 20, 23))
    d.rounded_rectangle([S * .07, S * .07, S * .93, S * .93], radius=S * .13, fill=(26, 26, 30))
    for px, py in PIPS[vv]:
        cx, cy, r = S / 2 + px * S * .26, S / 2 + py * S * .26, S * .095
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(240, 239, 232))
    return np.asarray(im.resize((s, s), Image.LANCZOS))
TILES = [tile(k) for k in range(7)]
big = np.zeros((R * PX, C * PX, 3), np.uint8)
for y in range(R):
    for x in range(C): big[y * PX:(y + 1) * PX, x * PX:(x + 1) * PX] = TILES[G[y, x]]
dice = Image.fromarray(big); dice.save(f'{OUT}/version_des_HD_{REF}.png', optimize=True)
dist = dice.resize((C * 8, R * 8), Image.LANCZOS)

# ---------- PDF plan ----------
INK = HexColor('#111316'); GREY = HexColor('#6b7078'); LINE = HexColor('#c9d3e3'); ACC = HexColor('#b8913f'); BLUE = HexColor('#14306b')
W, H = A4; pdf = f'{OUT}/Plan_fabrication_{REF}.pdf'
c = canvas.Canvas(pdf, pagesize=A4); c.setTitle(f'Plan de fabrication {REF}'); c.setAuthor("JLF D'ICE")
fmt = lambda n: f'{n:,}'.replace(',', ' ')
title = 'Portrait sur mesure' + (f' · {A.client}' if A.client else '')
def footer(label):
    c.setFont('Helvetica', 7.5); c.setFillColor(GREY)
    c.drawString(15 * mm, 9 * mm, f"JLF D'ICE · Plan de fabrication · réf. #{REF}"); c.drawRightString(W - 15 * mm, 9 * mm, label)
def die_icon(x, y, s, vv):
    c.setFillColor(INK); c.roundRect(x, y, s, s, s * .17, fill=1, stroke=0); c.setFillColor(white)
    for px, py in PIPS[vv]: c.circle(x + s / 2 + px * s * .26, y + s / 2 - py * s * .26, s * .09, fill=1, stroke=0)

SC, SR = 20, 25; NSC, NSR = math.ceil(C / SC), math.ceil(R / SR)
LET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
pages = 2 + NSC * NSR
# page 1 — overview
c.setFillColor(INK); c.setFont('Helvetica-Bold', 22); c.drawString(15 * mm, H - 24 * mm, 'Plan de fabrication')
c.setFont('Helvetica-Bold', 13); c.drawString(15 * mm, H - 32 * mm, title)
c.setFont('Helvetica', 9); c.setFillColor(GREY); c.drawString(15 * mm, H - 38 * mm, f'Réf. #{REF} · code atelier {A.code.upper()} · {datetime.date.today().strftime("%d/%m/%Y")}')
iwmm = 85 * mm; ihmm = iwmm * R / C
if ihmm > 115 * mm: ihmm = 115 * mm; iwmm = ihmm * C / R
c.drawImage(ImageReader(crop), 15 * mm, H - 46 * mm - ihmm, iwmm, ihmm); c.drawImage(ImageReader(dist), W - 15 * mm - iwmm, H - 46 * mm - ihmm, iwmm, ihmm)
c.setFont('Helvetica', 7.5); c.drawString(15 * mm, H - 50 * mm - ihmm, 'Photo originale (recadrée)'); c.drawString(W - 15 * mm - iwmm, H - 50 * mm - ihmm, 'Rendu en dés')
y = H - 62 * mm - ihmm
def row(k, val, bold=False):
    global y
    c.setFont('Helvetica', 9); c.setFillColor(GREY); c.drawString(15 * mm, y, k)
    c.setFont('Helvetica-Bold' if bold else 'Helvetica', 9.5); c.setFillColor(INK); c.drawString(70 * mm, y, val); y -= 5.6 * mm
c.setFont('Helvetica-Bold', 11); c.setFillColor(INK); c.drawString(15 * mm, y, 'Caractéristiques'); y -= 7 * mm
row('Nombre de dés', fmt(N), True); row('Grille', f'{C} colonnes × {R} lignes')
row('Taille des dés', f'{DIE} × {DIE} × {DIE} mm, noirs à points blancs')
row('Format final (dés seuls)', f'{C * DIE / 10:.1f} × {R * DIE / 10:.1f} cm'.replace('.', ','), True)
row('Sections', f'{NSC} × {NSR} sections de {SC} × {SR} dés max.')
y -= 3 * mm; c.setFont('Helvetica-Bold', 11); c.drawString(15 * mm, y, 'Liste de dés (face visible)'); y -= 8 * mm
spare = lambda n: math.ceil(n * 1.03)
for k in [1, 2, 3, 4, 5, 6, 0]:
    if CNT[k] == 0: continue
    die_icon(15 * mm, y - 1.5 * mm, 5 * mm, k)
    c.setFont('Helvetica', 9); c.setFillColor(INK)
    c.drawString(23 * mm, y, ('Face vide (dé entièrement noir)' if k == 0 else f'Face {k}'))
    c.drawRightString(110 * mm, y, fmt(CNT[k])); c.setFillColor(GREY); c.drawRightString(150 * mm, y, f'avec 3 % de marge : {fmt(spare(CNT[k]))}'); y -= 6.5 * mm
c.setFillColor(INK); c.setFont('Helvetica-Bold', 9.5); c.drawString(23 * mm, y, 'Total'); c.drawRightString(110 * mm, y, fmt(N)); c.setFillColor(GREY); c.setFont('Helvetica', 9); c.drawRightString(150 * mm, y, f'à commander : {fmt(sum(spare(CNT[k]) for k in CNT if CNT[k]))}')
footer(f'1 / {pages}'); c.showPage()
# page 2 — section map
c.setFillColor(INK); c.setFont('Helvetica-Bold', 16); c.drawString(15 * mm, H - 22 * mm, 'Carte des sections')
c.setFont('Helvetica', 9); c.setFillColor(GREY)
c.drawString(15 * mm, H - 29 * mm, 'Lignes numérotées de haut en bas, colonnes de gauche à droite. Chaque page suivante = une section, vue de face.')
mw = 180 * mm; mh = mw * R / C
if mh > 230 * mm: mh = 230 * mm; mw = mh * C / R
mx, my = (W - mw) / 2, H - 38 * mm - mh
c.drawImage(ImageReader(dist), mx, my, mw, mh); cw, rh = mw / C, mh / R
c.setStrokeColor(HexColor('#ffb347')); c.setLineWidth(1.2)
for i in range(NSC):
    for j in range(NSR):
        x0, x1 = i * SC, min(C, (i + 1) * SC); y0, y1 = j * SR, min(R, (j + 1) * SR)
        c.rect(mx + x0 * cw, my + mh - y1 * rh, (x1 - x0) * cw, (y1 - y0) * rh, fill=0, stroke=1)
        c.setFillColor(HexColor('#ffb347')); c.setFont('Helvetica-Bold', 9); c.drawCentredString(mx + (x0 + x1) / 2 * cw, my + mh - (y0 + y1) / 2 * rh - 3, f'{LET[i]}{j + 1}')
footer(f'2 / {pages}'); c.showPage()
# section pages
pg = 3
for j in range(NSR):
    for i in range(NSC):
        x0, x1 = i * SC, min(C, (i + 1) * SC); y0, y1 = j * SR, min(R, (j + 1) * SR)
        sc, sr = x1 - x0, y1 - y0
        cell = min(176 * mm / SC, 232 * mm / SR)
        gx, gy = 22 * mm, H - 34 * mm
        c.setFillColor(INK); c.setFont('Helvetica-Bold', 15); c.drawString(15 * mm, H - 18 * mm, f'Section {LET[i]}{j + 1}')
        c.setFont('Helvetica', 8.5); c.setFillColor(GREY); c.drawString(15 * mm, H - 24 * mm, f'Colonnes {x0 + 1}–{x1} · lignes {y0 + 1}–{y1} · {sc * sr} dés')
        # mini map
        mmw = 28 * mm; mmh = mmw * R / C; ox, oy = W - 15 * mm - mmw, H - 12 * mm - mmh
        c.setStrokeColor(LINE); c.setFillColor(HexColor('#eef1f5')); c.rect(ox, oy, mmw, mmh, fill=1, stroke=1)
        c.setFillColor(HexColor('#ffb347')); c.rect(ox + x0 / C * mmw, oy + mmh - y1 / R * mmh, sc / C * mmw, sr / R * mmh, fill=1, stroke=0)
        c.setFont('Helvetica', 6)
        for xx in range(sc):
            c.setFillColor(GREY); c.drawCentredString(gx + (xx + .5) * cell, gy + 1.2 * mm, str(x0 + xx + 1))
        for yy in range(sr):
            c.setFillColor(GREY); c.drawRightString(gx - 1.2 * mm, gy - (yy + 1) * cell + cell * .35, str(y0 + yy + 1))
            for xx in range(sc):
                die_icon(gx + xx * cell + cell * .06, gy - (yy + 1) * cell + cell * .06, cell * .88, int(G[y0 + yy, x0 + xx]))
        c.setStrokeColor(LINE); c.setLineWidth(.3)
        for xx in range(0, sc + 1, 5): c.line(gx + xx * cell, gy, gx + xx * cell, gy - sr * cell)
        for yy in range(0, sr + 1, 5): c.line(gx, gy - yy * cell, gx + sc * cell, gy - yy * cell)
        footer(f'{pg} / {pages}'); pg += 1; c.showPage()
c.save()
print('OK', OUT, f'{C}x{R}', N, 'dés', CNT, 'pages', pages)
