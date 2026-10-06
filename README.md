# LB-in-arreas

Programa para calcular intereses bajo la metodología de tasa **Lookback in Arreas**, usando tasas del Banco de México (Banxico).

## Características

- Periodo de intereses calculado solo con **días hábiles de la CNBV** (sin fines de semana ni feriados de México).
- Obtención de tasas vía API de Banxico (serie `SF331451`, TIIE diaria).
- Tasa compuesta capitalizando diariamente:

  `Tasa = [ ∏ (1 + R_i · n_i / 360) − 1 ] × 360 / d_c`

- Redondeo a 8 decimales.
- Intereses con base 360 días.
- Interfaz gráfica en Tkinter con calendarios desplegables (`tkcalendar`).
- Desglose paso a paso del cálculo.

## Instalación

```bash
pip install -r requirements.txt
setx BANXICO_TOKEN "tu_token_de_banxico"
```

## Uso

Consola:

```bash
python lb_in_arreas.py
```

Interfaz gráfica:

```bash
python lb_gui.py
```

Datos solicitados: fecha inicio, fecha fin (día de pago; el periodo corre hasta el día anterior), saldo insoluto, margen (%) y lookback (días hábiles de desfase).

## Estructura

- `lb_in_arreas.py` — lógica de cálculo (consola).
- `lb_gui.py` — interfaz gráfica Tkinter.
- `requirements.txt` — dependencias.
