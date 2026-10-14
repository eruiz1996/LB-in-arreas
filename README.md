# LB-in-arreas

Programa para calcular intereses bajo la metodología de tasa **Lookback in Arreas**, usando tasas del Banco de México (Banxico).

## Características

- Periodo de intereses calculado solo con **días hábiles de la Comisión Nacional Bancaria y de Valores** (sin fines de semana ni feriados de México).
- Obtención de tasas vía API de Banxico (serie `SF331451`, TIIE diaria).
- Tasa compuesta capitalizando diariamente:

  $$\text{Tasa}=\left[\prod _{i=1}^{d_{b}}\left(1+\frac{R_{i}\times n_{i}}{N}\right)-1\right]\times \frac{N}{d_{c}}$$

- Redondeo a 8 decimales.
- Intereses con base 360 días.
- Interfaz gráfica en Tkinter con calendarios desplegables (`tkcalendar`).
- Desglose paso a paso del cálculo.

## Instalación

```bash
pip install -r requirements.txt
```

Al ejecutar, el programa pide el `BANXICO_TOKEN` (se solicita una sola vez; cada usuario ingresa el suyo).

## Uso

Consola:

```bash
python lb_in_arreas.py
```

Interfaz gráfica:

```bash
python lb_gui.py
```

Datos solicitados: fecha inicio, fecha fin (día de pago; el periodo corre hasta el día anterior), saldo insoluto, margen (%), lookback (días hábiles de desfase), token de Banxico, decimales de cálculo (factores, por defecto 8) y decimales de tasa (por defecto 4).

## Estructura

- `lb_in_arreas.py` — lógica de cálculo (consola).
- `lb_gui.py` — interfaz gráfica Tkinter.
- `requirements.txt` — dependencias.
