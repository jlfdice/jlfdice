"""Atelier JLF D'ICE — à partir d'une commande (photo originale du client + code atelier de la fiche),
génère : photo originale HD recadrée, version en dés HD, grille CSV et plan de fabrication PDF.
Usage : python3 commande.py --photo client.jpg --code JLFD-C61-R82-D10-X50Y50Z100-Z8KX [--client "Prénom"] [--out dossier]"""
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
m = re.match(r'JLFD-C(\d+)-R(\d+)-D(\d+)(?:-X(\d+)Y(\d+)Z(\d+)(?:A\d+)?)?-([A-Z0-9]+)$', A.code.strip().upper())
if not m: raise SystemExit('Code atelier illisible : ' + A.code)
C, R, DIE, REF = int(m[1]), int(m[2]), int(m[3]), m[7]
# framing chosen by the client in the app (X/Y = position in %, Z = zoom in %); older codes have none
CROP = (int(m[4]) / 100, int(m[5]) / 100, max(.2, int(m[6]) / 100)) if m[4] else None
OUT = A.out or f'commande_{REF}'; os.makedirs(OUT, exist_ok=True)
N = C * R

# ---------- same conversion as the app ----------
src = ImageOps.exif_transpose(Image.open(A.photo)).convert('RGB')
iw, ih = src.size; ar = C / R
sw, sh = iw, iw / ar
if sh > ih: sh, sw = ih, ih * ar
if CROP:
    px, py, z = CROP; sw, sh = sw / z, sh / z
    sx, sy = px * (iw - sw), py * (ih - sh)
else:
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

# ---------- PDF plan : 2 pages A3 paysage, code couleur ----------
from reportlab.lib.pagesizes import A3, landscape
INK = HexColor('#111316'); GREY = HexColor('#6b7078'); RED = HexColor('#e2483d')
COL = {0: ('#000000', '#ffffff'), 1: ('#3d1c6e', '#ffffff'), 2: ('#1f5fc4', '#ffffff'), 3: ('#14a39a', '#ffffff'),
       4: ('#74c24a', '#111111'), 5: ('#f3c623', '#111111'), 6: ('#f7f7f5', '#111111')}
PW, PH = landscape(A3); pdf = f'{OUT}/Plan_fabrication_{REF}.pdf'
c = canvas.Canvas(pdf, pagesize=(PW, PH)); c.setTitle(f'Plan de fabrication {REF}'); c.setAuthor("JLF D'ICE")
fmt = lambda n: f'{n:,}'.replace(',', ' ')
GS = 10                                   # guide every 10 dice
title = 'Portrait sur mesure' + (f' · {A.client}' if A.client else '')
def die_icon(x, y, s, vv, stroke=None):
    c.setFillColor(INK)
    if stroke: c.setStrokeColor(stroke); c.setLineWidth(.4)
    c.roundRect(x, y, s, s, s * .17, fill=1, stroke=1 if stroke else 0); c.setFillColor(white)
    for px, py in PIPS[vv]: c.circle(x + s / 2 + px * s * .26, y + s / 2 - py * s * .26, s * .09, fill=1, stroke=0)
def page(r0, r1, part):
    rows = r1 - r0
    left, right, top, bottom = 16 * mm, 16 * mm, 34 * mm, 30 * mm
    cell = min((PW - left - right - 12 * mm) / C, (PH - top - bottom) / rows)
    gw, gh = cell * C, cell * rows; gx = (PW - gw) / 2; gyT = PH - top
    # header
    c.setFillColor(INK); c.setFont('Helvetica-Bold', 16); c.drawString(16 * mm, PH - 14 * mm, f"Plan de fabrication {part}/2 · {title}")
    c.setFont('Helvetica', 8.5); c.setFillColor(GREY)
    c.drawString(16 * mm, PH - 20 * mm, f"Réf. #{REF} · {A.code.upper()} · {fmt(N)} dés de {DIE} mm · grille {C} × {R} · format {f'{C * DIE / 10:.1f}'.replace('.', ',')} × {f'{R * DIE / 10:.1f}'.replace('.', ',')} cm · {datetime.date.today().strftime('%d/%m/%Y')}")
    c.drawString(16 * mm, PH - 25 * mm, f"Rangées {r0 + 1} à {r1} · 1 case = 1 dé · vue de face, coin haut-gauche = colonne 1, rangée 1 · traits rouges = repères tous les {GS} dés")
    th = 24 * mm; tw = th * C / R
    c.drawImage(ImageReader(crop), PW - 16 * mm - 2 * tw - 3 * mm, PH - 8 * mm - th, tw, th); c.drawImage(ImageReader(dist), PW - 16 * mm - tw, PH - 8 * mm - th, tw, th)
    c.setStrokeColor(RED); c.setLineWidth(.8)   # where this page sits on the piece
    c.rect(PW - 16 * mm - tw, PH - 8 * mm - th + th * (1 - r1 / R), tw, th * rows / R, fill=0, stroke=1)
    # legend + shopping list
    y = 15 * mm; c.setFillColor(INK); c.setFont('Helvetica-Bold', 9); c.drawString(gx, y + 7.5 * mm, 'Légende et quantités (avec 3 % de marge)')
    for k in range(7):
        bg, fg = COL[k]; x = gx + k * 40 * mm
        c.setFillColor(HexColor(bg)); c.setStrokeColor(HexColor('#999999')); c.setLineWidth(.4); c.rect(x, y, 6 * mm, 6 * mm, fill=1, stroke=1)
        c.setFillColor(HexColor(fg)); c.setFont('Helvetica-Bold', 8); c.drawCentredString(x + 3 * mm, y + 1.8 * mm, str(k))
        die_icon(x + 7 * mm, y, 6 * mm, k, stroke=GREY if k == 0 else None)
        c.setFillColor(INK); c.setFont('Helvetica', 7.5); c.drawString(x + 14.5 * mm, y + 3.4 * mm, 'face vide' if k == 0 else f'face {k}')
        c.setFont('Helvetica-Bold', 7.5); c.drawString(x + 14.5 * mm, y + .3 * mm, f'{fmt(CNT[k])}  →  {fmt(math.ceil(CNT[k] * 1.03))}')
    # cells
    fs = cell * .6
    for r in range(r0, r1):
        for col in range(C):
            vv = int(G[r, col]); bg, fg = COL[vv]; x = gx + col * cell; yy = gyT - (r - r0 + 1) * cell
            c.setFillColor(HexColor(bg)); c.rect(x, yy, cell, cell, fill=1, stroke=0)
            c.setFillColor(HexColor(fg)); c.setFont('Helvetica-Bold', fs); c.drawCentredString(x + cell / 2, yy + cell * .28, str(vv))
    c.setStrokeColor(HexColor('#ffffff')); c.setLineWidth(.2)
    for col in range(C + 1): c.line(gx + col * cell, gyT, gx + col * cell, gyT - gh)
    for r in range(rows + 1): c.line(gx, gyT - r * cell, gx + gw, gyT - r * cell)
    c.setStrokeColor(RED); c.setLineWidth(1.1)
    for col in range(0, C + 1, GS): c.line(gx + col * cell, gyT, gx + col * cell, gyT - gh)
    for r in range(r0, r1 + 1):
        if r % GS == 0: c.line(gx, gyT - (r - r0) * cell, gx + gw, gyT - (r - r0) * cell)
    c.setStrokeColor(INK); c.setLineWidth(1.2); c.rect(gx, gyT - gh, gw, gh, fill=0, stroke=1)
    c.setFillColor(INK); fsn = min(5.5, cell / mm * 1.2)
    c.setFont('Helvetica', fsn)
    for col in range(C):
        if (col + 1) % 5 == 0 or col == 0 or col == C - 1:
            c.drawCentredString(gx + col * cell + cell / 2, gyT + 1.3 * mm, str(col + 1)); c.drawCentredString(gx + col * cell + cell / 2, gyT - gh - 3 * mm, str(col + 1))
    for r in range(r0, r1):
        yy = gyT - (r - r0 + 1) * cell + cell * .3
        c.drawRightString(gx - 1.2 * mm, yy, str(r + 1)); c.drawString(gx + gw + 1.2 * mm, yy, str(r + 1))
    c.setFont('Helvetica', 7.5); c.setFillColor(GREY); c.drawString(16 * mm, 7 * mm, "JLF D'ICE · Plan de fabrication · réf. #" + REF); c.drawRightString(PW - 16 * mm, 7 * mm, f'{part} / 2')
    c.showPage()
mid = math.ceil(R / 2)
page(0, mid, 1); page(mid, R, 2)
c.save()
print('OK', OUT, f'{C}x{R}', N, 'dés', CNT)
