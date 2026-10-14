# LB-in-arreas

Programa para calcular intereses bajo la metodología de tasa **Lookback in Arreas**, con dos variantes:

| Pestaña | Tasa | Fuente | Calendario | Token |
|---|---|---|---|---|
| **TIIE** | TIIE diaria (serie `SF331451`) | [API de Banxico](https://www.banxico.org.mx/SieAPIRest/service/v1/token) | Días hábiles de la Comisión Nacional Bancaria y de Valores (sin fines de semana ni feriados de México) | Requerido |
| **SOFR** | SOFR diaria | [NY Fed Markets Data API](https://markets.newyorkfed.org/static/docs/markets-api.html) | Días inhábiles de la Reserva Federal (sin fines de semana ni feriados de EE. UU.) | No requiere |

## Características

- Periodo de intereses calculado solo con días hábiles del calendario correspondiente (CNBV para TIIE, FED para SOFR).
- Obtención de tasas vía APIs:
  - **TIIE**: `GET https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF331451/datos/{ini}/{fin}` (requiere el token que se genera en la [página oficial de la SIE-API de Banxico](https://www.banxico.org.mx/SieAPIRest/service/v1/token); fechas de respuesta en formato `dd/mm/aaaa`).
  - **SOFR**: `GET https://markets.newyorkfed.org/api/rates/secured/sofr/search.json?startDate=aaaa-mm-dd&endDate=aaaa-mm-dd` (sin token; fechas de respuesta en formato `aaaa-mm-dd`).
- Tasa compuesta capitalizando diariamente:

  $$\text{Tasa}=\left[\prod _{i=1}^{d_{b}}\left(1+\frac{R_{i}\times n_{i}}{N}\right)-1\right]\times \frac{N}{d_{c}}$$

- Redondeo configurable: decimales de cálculo (factores) y decimales de tasa, con valores por defecto 8/4 en TIIE y 9/5 en SOFR.
- Intereses con base 360 días (convención ACT/360).
- Interfaz gráfica en Tkinter con pestañas diferenciadas por color (TIIE rojo Santander, SOFR turquesa), calendarios desplegables (`tkcalendar`), tabla del desglose diario y fórmulas LaTeX de la tasa. Debajo del botón «Calcular» se resalta el resultado de los **intereses**, con botón «Copiar» para llevarlo al portapapeles.
- Desglose paso a paso del cálculo.

## Instalación

```bash
pip install -r requirements.txt
```

Al ejecutar, la consola pregunta primero por la metodología (`TIIE` o `SOFR`, por defecto TIIE). Solo en TIIE pide el token de Banxico (se genera una sola vez en la [página oficial del token](https://www.banxico.org.mx/SieAPIRest/service/v1/token); cada usuario ingresa el suyo). SOFR no requiere token.

## Uso

Consola:

```bash
python lb_in_arreas.py
```

Interfaz gráfica:

```bash
python lb_gui.py
```

La interfaz tiene dos pestañas —**TIIE** y **SOFR**— con los mismos campos (fecha inicio, fecha fin como día de pago, saldo insoluto, margen, lookback, decimales de cálculo y de tasa). La pestaña TIIE incluye además el campo de token; SOFR no lo necesita. A la derecha se muestra el «Detalle tasa» con las fórmulas del resultado y, debajo, el «Desglose diario» y el «Cálculo de intereses».

## Estructura

- `lb_in_arreas.py` — lógica de cálculo (consola).
- `lb_gui.py` — interfaz gráfica Tkinter.
- `requirements.txt` — dependencias.

## Licencia

Distribuido bajo la licencia [MIT](LICENSE).
