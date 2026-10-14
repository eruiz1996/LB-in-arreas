import sys
from datetime import datetime, date, timedelta

import holidays
import requests

SERIE = "SF331451"
URL = (
    "https://www.banxico.org.mx/SieAPIRest/service/v1/series/"
    + SERIE
    + "/datos/{ini}/{fin}"
)
URL_SOFR = "https://markets.newyorkfed.org/api/rates/secured/sofr/search.json"


def es_habil(d, feriados):
    return d.weekday() < 5 and d not in feriados


def dias_habiles(a, b, feriados):
    out = []
    d = a
    while d <= b:
        if es_habil(d, feriados):
            out.append(d)
        d += timedelta(days=1)
    return out


def obtener_tasas_banxico(ini, fin, token):
    r = requests.get(
        URL.format(ini=ini.strftime("%Y-%m-%d"), fin=fin.strftime("%Y-%m-%d")),
        headers={"Bmx-Token": token},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    tasas = {}
    for dato in data["bmx"]["series"][0]["datos"]:
        fecha = datetime.strptime(dato["fecha"], "%d/%m/%Y").date()
        tasas[fecha] = float(dato["dato"].replace(",", "")) / 100.0
    return tasas


def obtener_tasas_sofr(ini, fin):
    r = requests.get(
        URL_SOFR,
        params={"startDate": ini.strftime("%Y-%m-%d"), "endDate": fin.strftime("%Y-%m-%d")},
        timeout=30,
    )
    r.raise_for_status()
    tasas = {}
    for dato in r.json()["refRates"]:
        fecha = datetime.strptime(dato["effectiveDate"], "%Y-%m-%d").date()
        tasas[fecha] = float(dato["percentRate"]) / 100.0
    return tasas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    metodo = input("Metodología (TIIE/SOFR) [Enter=TIIE]: ").strip().upper() or "TIIE"
    if metodo not in ("TIIE", "SOFR"):
        print("Metodología no válida (usa TIIE o SOFR).")
        return
    es_tiie = metodo == "TIIE"
    token = input("Token de Banxico: ").strip() if es_tiie else None
    capital = float(input("Capital: "))
    inicio = datetime.strptime(input("Fecha inicio (AAAA-MM-DD): "), "%Y-%m-%d").date()
    final = datetime.strptime(input("Fecha fin (AAAA-MM-DD): "), "%Y-%m-%d").date()
    margen = float(input("Margen (%): "))
    lookback = int(input("Lookback (días hábiles): "))
    dec_calc_txt = input("Decimales cálculo (Enter=8): ").strip()
    dec_calc = int(dec_calc_txt) if dec_calc_txt else 8
    dec_tasa_txt = input("Decimales tasa (Enter=4): ").strip()
    dec_tasa = int(dec_tasa_txt) if dec_tasa_txt else 4
    if dec_calc < 0 or dec_tasa < 0:
        print("Los decimales deben ser enteros positivos.")
        return

    feriados = holidays.Mexico() if es_tiie else holidays.US()
    final_periodo = final - timedelta(days=1)
    periodo = dias_habiles(inicio, final_periodo, feriados)
    if not periodo:
        print("No hay días hábiles en el periodo.")
        return

    d_c = (final - inicio).days
    d_b = len(periodo)

    # Días hábiles con tasas (para desfase lookback se consulta antes del inicio)
    ventana_ini = inicio - timedelta(days=max(60, lookback * 3))
    if es_tiie:
        tasas_pub = obtener_tasas_banxico(ventana_ini, final_periodo, token)
    else:
        tasas_pub = obtener_tasas_sofr(ventana_ini, final_periodo)
    fechas_tasas = sorted(tasas_pub)

    # Para cada día hábil i del periodo, la tasa aplica es la publicada
    # L días hábiles antes (lookback in arreas).
    indices = {f: i for i, f in enumerate(fechas_tasas)}
    producto = 1.0
    detalle_ok = True
    detalle = []
    for i, dia in enumerate(periodo):
        # tasa: la publicada el día hábil 'dia - L posiciones' dentro de fechas_tasas
        pos = indices.get(dia)
        if pos is None or pos - lookback < 0:
            detalle_ok = False
            break
        fecha_tas = fechas_tasas[pos - lookback]
        R = tasas_pub[fecha_tas]
        siguiente = periodo[i + 1] if i + 1 < len(periodo) else final
        n_i = (siguiente - dia).days
        factor = round(1 + R * n_i / 360.0, dec_calc)
        producto *= factor
        detalle.append((dia, fecha_tas, R, n_i, factor))

    if not detalle_ok:
        print("No se pudo desfasar con el lookback dado: faltan tasas publicadas.")
        return

    tasa_compuesta = (producto - 1) * 360.0 / d_c
    tasa_compuesta_pct = round(tasa_compuesta * 100, dec_tasa)
    tasa_final_pct = round(tasa_compuesta_pct + margen, dec_tasa)
    intereses = capital * (tasa_final_pct / 100.0) * d_c / 360.0

    print("\n----- L O O K B A C K   I N   A R R E A S -----")
    print(f"Metodología:  {metodo} (calendario {'CNBV/México' if es_tiie else 'FED/EE. UU.'})")
    print(f"Capital:           ${capital:,.2f}")
    print(f"Periodo:           {inicio} a {final}")
    print(f"Días hábiles(d_b): {d_b} | Días calendario(d_c): {d_c} | Lookback: {lookback}")
    print(f"Decimales cálculo: {dec_calc} | Decimales tasa: {dec_tasa}")
    print("\n--- Paso 1: Desglose diario (lookback in arreas) ---")
    print(f"{'Día periodo':<12}{'Tasa pub. en':<14}{'R (%)':>8}{'n_i':>5}{'Factor (1+R·n/360)':>{20+max(dec_calc-8,0)}}")
    for dia, fecha_tas, R, n_i, factor in detalle:
        print(f"{dia!s:<12}{fecha_tas!s:<14}{R*100:>8.4f}{n_i:>5}{factor:>{20+max(dec_calc-8,0)}.{dec_calc}f}")
    print(f"\n--- Paso 2: Compuesto del periodo ---")
    print(f"Producto de factores:  {producto:.{max(dec_calc,10)}f}")
    print(f"Producto - 1:          {producto - 1:.{max(dec_calc,10)}f}")
    print(f"Tasa = (prod-1)×360/{d_c}: {tasa_compuesta*100:.{dec_tasa}f} %")
    print(f"Tasa compuesta (redondeo {dec_tasa} dec): {tasa_compuesta_pct:.{dec_tasa}f} %")
    print(f"\n--- Paso 3: Tasa Integrada ---")
    print(f"Tasa final = {tasa_compuesta_pct:.{dec_tasa}f}% + {margen:.{dec_tasa}f}% = {tasa_final_pct:.{dec_tasa}f}%")
    print(f"\n--- Paso 4: Intereses (base 360) ---")
    print(f"Intereses = ${capital:,.2f} × {tasa_final_pct:.{dec_tasa}f}% × {d_c}/360")
    print(f"          = ${capital * (tasa_final_pct/100.0):,.2f} × {d_c}/360")
    print(f"          = ${intereses:,.2f}")


if __name__ == "__main__":
    main()
