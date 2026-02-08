# -*- coding: utf-8 -*-
"""Genera el reporte (PNG + metadata) para GitHub Pages.

- Lee datos desde ./data/Encuestas_2025.xlsx
- Genera ./dist/assets/dashboard.png y ./dist/assets/latest.json

Este proyecto evita Google Drive/Colab y solo consume archivos locales del repo.
"""

import os, json, datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Rectangle
import yaml

EXCEL_EPOCH = pd.Timestamp('1899-12-30')

def excel_to_date(x):
    if pd.isna(x):
        return pd.NaT
    try:
        return EXCEL_EPOCH + pd.to_timedelta(float(x), unit='D')
    except Exception:
        return pd.to_datetime(x, errors='coerce')

NOMBRES_ULTRA = {
 'Keiko Fujimori':'Keiko',
 'Rafael López Aliaga':'López A.',
 'Carlos Álvarez':'Álvarez',
 'Mario Vizcarra':'Vizcarra',
 'César Acuña':'Acuña',
 'Alfonso López Chau':'López C.',
 'No precisa':'No precisa',
 'Blanco/viciado/ninguno':'Blanco/V.',
 'Blanco/viciado/Ninguno':'Blanco/V.',
 'Otros':'Otros'
}

COLORES = {
 'Keiko':'#FFA500',
 'López A.':'#00A0DF',
 'Álvarez':'#F7C501',
 'Vizcarra':'#F11818',
 'Acuña':'#0000FF',
 'López C.':'#2ECC71',
 'No precisa':'#7a7a7a',
 'Blanco/V.':'#65666C',
 'Otros':'#999999',
 'Empate':'#B2B2B2'
}


def load_config(path='generator/config.yaml'):
    with open(path,'r',encoding='utf-8') as f:
        return yaml.safe_load(f)


def make_dashboard(xlsx_path, pollster, out_png, out_meta):
    xl = pd.ExcelFile(xlsx_path, engine='openpyxl')
    sheets = xl.sheet_names

    nac = pd.read_excel(xlsx_path, sheet_name='ENCUESTA_PERU', engine='openpyxl')
    nac['Fecha'] = nac['Fecha'].apply(excel_to_date)
    nac['Encuestadora'] = nac['Encuestadora'].astype(str).str.strip().str.lower()

    # Eventos (opcional)
    try:
        ev = pd.read_excel(xlsx_path, sheet_name='Eventos', engine='openpyxl')
        ev['Fecha'] = ev['Fecha'].apply(excel_to_date)
        ev['Evento'] = ev['Evento'].astype(str).str.replace('\n',' ', regex=False).str.strip()
    except Exception:
        ev = pd.DataFrame(columns=['Fecha','Evento'])

    # Macro-regiones (opcional)
    try:
        zon = pd.read_excel(xlsx_path, sheet_name='zonificado', engine='openpyxl')
        zon['Fecha'] = zon['Fecha'].apply(excel_to_date)
    except Exception:
        zon = pd.DataFrame()

    # Renombrado de columnas de candidatos
    rename_cols = {k:v for k,v in NOMBRES_ULTRA.items() if k in nac.columns}
    nac = nac.rename(columns=rename_cols)

    df = nac[nac['Encuestadora']==pollster].sort_values('Fecha')
    if df.empty:
        raise SystemExit(f'No hay datos para encuestadora={pollster}. Disponibles: {sorted(nac.'Encuestadora'.dropna().unique())}')

    cand_cols = [c for c in ['Keiko','López A.','Álvarez','Vizcarra','Acuña','López C.'] if c in df.columns]
    for c in cand_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

    last_date = df['Fecha'].max()

    fig = plt.figure(figsize=(16, 10), dpi=160, facecolor='white')
    gs = GridSpec(2, 2, height_ratios=[0.62, 0.38], width_ratios=[0.62, 0.38], hspace=0.22, wspace=0.18)
    ax_lines = fig.add_subplot(gs[0, :])
    ax_table = fig.add_subplot(gs[1, 0])
    ax_macro = fig.add_subplot(gs[1, 1])

    ax_lines.set_title(f"INTENCIÓN DE VOTO (últimas mediciones) • {pollster.upper()}", loc='left', fontsize=16, fontweight='bold', pad=14, color='#222')

    for c in cand_cols:
        ax_lines.plot(df['Fecha'], df[c], lw=2.2, marker='o', ms=3.5, color=COLORES.get(c,'#888'), label=c)

    # Eventos
    if not ev.empty:
        ev2 = ev[(ev['Fecha']>=df['Fecha'].min()) & (ev['Fecha']<=df['Fecha'].max())].dropna(subset=['Fecha'])
        for _, r in ev2.iterrows():
            ax_lines.axvline(r['Fecha'], color='#F4AF02', ls='--', lw=1.6, alpha=0.6)
            ax_lines.text(r['Fecha'], ax_lines.get_ylim()[1]*0.95, str(r['Evento'])[:40], ha='center', va='top', fontsize=9, color='#3B4C75')

    ax_lines.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
    ax_lines.grid(True, axis='y', alpha=0.18)
    ax_lines.spines['top'].set_visible(False)
    ax_lines.spines['right'].set_visible(False)
    ax_lines.legend(ncol=3, frameon=False, loc='upper left')

    # Tabla
    show = df.sort_values('Fecha', ascending=False).head(8).copy()
    show = show[['Fecha'] + cand_cols]
    show['Fecha'] = show['Fecha'].dt.strftime('%d-%b-%Y')
    show_vals = show[cand_cols].apply(pd.to_numeric, errors='coerce')
    deltas = show_vals.diff(-1)

    ax_table.axis('off')
    ax_table.text(0, 1.05, 'TABLA (últimas 8 mediciones)', transform=ax_table.transAxes, fontsize=13, fontweight='bold', color='#222')

    cell_text = []
    for i in range(len(show)):
        row = [show.iloc[i]['Fecha']]
        for c in cand_cols:
            v = float(show_vals.iloc[i][c])
            d = deltas.iloc[i][c] if i < len(show)-1 else np.nan
            if pd.isna(d) or abs(d) < 1e-6:
                row.append(f"{v:.1%} →")
            elif d > 0:
                row.append(f"{v:.1%} (+{d:.1%} ↑)")
            else:
                row.append(f"{v:.1%} ({d:.1%} ↓)")
        cell_text.append(row)

    col_labels = ['Fecha'] + cand_cols
    tbl = ax_table.table(cellText=cell_text, colLabels=col_labels, loc='upper left', cellLoc='center', colLoc='center', bbox=[0,0,1,0.95])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9.5)

    for (r,c), cell in tbl.get_celld().items():
        cell.set_edgecolor('#dddddd')
        if r == 0:
            cell.set_facecolor('#f4f4f7')
            cell.set_text_props(weight='bold', color='#111')
        else:
            if c == 0:
                cell.set_text_props(weight='bold', color='#111')
            else:
                txt = cell.get_text().get_text()
                if '↑' in txt:
                    cell.set_facecolor('#E8F5E9')
                    cell.set_text_props(color='#2E7D32', weight='bold')
                elif '↓' in txt:
                    cell.set_facecolor('#FFEBEE')
                    cell.set_text_props(color='#C62828', weight='bold')
                else:
                    cell.set_facecolor('white')

    # Macro ganadores (si existe hoja zonificado)
    ax_macro.set_title('GANADOR POR MACROREGIÓN (última fecha)', loc='left', fontsize=13, fontweight='bold', color='#222', pad=8)
    ax_macro.axis('off')

    macro_cols = ['Lima (%)','Norte (%)','Centro (%)','Sur (%)','Oriente (%)']
    winners = []

    if not zon.empty:
        zlast = zon['Fecha'].max()
        zdf = zon[zon['Fecha']==zlast].copy()
        zdf['Candidato'] = zdf['Candidato'].map(NOMBRES_ULTRA).fillna(zdf['Candidato'])
        for mc in macro_cols:
            if mc in zdf.columns:
                zdf[mc] = pd.to_numeric(zdf[mc], errors='coerce').fillna(0) / 100.0
        zdf2 = zdf[~zdf['Candidato'].astype(str).str.contains('No precisa|Blanco|Viciado|Otros', case=False, regex=True)]
        for mc in macro_cols:
            if mc not in zdf2.columns:
                continue
            idx = zdf2[mc].idxmax()
            if pd.isna(idx):
                winners.append((mc.replace(' (%)',''), '—', 0.0))
            else:
                winners.append((mc.replace(' (%)',''), zdf2.loc[idx, 'Candidato'], float(zdf2.loc[idx, mc])))
        macro_date = zlast
    else:
        macro_date = last_date
        winners = [(r,'—',0.0) for r in ['Lima','Norte','Centro','Sur','Oriente']]

    ax_macro.text(0, 0.92, f"Fecha macro: {macro_date.strftime('%d-%b-%Y')}", transform=ax_macro.transAxes, fontsize=10, color='#555')
    y0, dy = 0.78, 0.14
    for i,(region,cand,val) in enumerate(winners):
        y = y0 - i*dy
        color = COLORES.get(cand,'#B2B2B2')
        ax_macro.add_patch(Rectangle((0, y-0.06), 1.0, 0.10, transform=ax_macro.transAxes, facecolor='#fafafa', edgecolor='#e0e0e0'))
        ax_macro.add_patch(Rectangle((0.02, y-0.035), 0.04, 0.05, transform=ax_macro.transAxes, facecolor=color, edgecolor='none'))
        ax_macro.text(0.08, y, region, transform=ax_macro.transAxes, va='center', fontsize=11, weight='bold', color='#222')
        ax_macro.text(0.42, y, cand, transform=ax_macro.transAxes, va='center', fontsize=11, color=color, weight='bold')
        ax_macro.text(0.92, y, f"{val:.0%}", transform=ax_macro.transAxes, va='center', ha='right', fontsize=11, color='#222', weight='bold')

    footer = f"Fuente: archivo Excel • Generado: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    fig.text(0.01, 0.01, footer, fontsize=9.5, color='#666')

    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    fig.savefig(out_png, bbox_inches='tight')
    plt.close(fig)

    meta = {
        'pollster': pollster,
        'last_poll_date': last_date.strftime('%Y-%m-%d'),
        'generated_utc': datetime.datetime.utcnow().isoformat() + 'Z',
        'has_macro': bool(not zon.empty),
        'sheets': sheets,
    }
    os.makedirs(os.path.dirname(out_meta), exist_ok=True)
    with open(out_meta, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def main():
    cfg = load_config()
    xlsx_path = cfg.get('xlsx_path', 'data/Encuestas_2025.xlsx')
    pollster = cfg.get('pollster', 'ipsos').strip().lower()
    out_png = cfg.get('out_png', 'dist/assets/dashboard.png')
    out_meta = cfg.get('out_meta', 'dist/assets/latest.json')

    make_dashboard(xlsx_path, pollster, out_png, out_meta)

    # Copiar HTML base a dist (para Pages)
    site_index = cfg.get('site_index', 'site/index.html')
    dist_index = cfg.get('dist_index', 'dist/index.html')
    os.makedirs(os.path.dirname(dist_index), exist_ok=True)
    with open(site_index,'r',encoding='utf-8') as f:
        html = f.read()

    # Cache-busting usando timestamp del build
    ts = int(datetime.datetime.utcnow().timestamp())
    html = html.replace('__CACHE_BUST__', str(ts))

    with open(dist_index,'w',encoding='utf-8') as f:
        f.write(html)

if __name__ == '__main__':
    main()
