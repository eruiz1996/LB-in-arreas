import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, simpledialog, ttk

import holidays
from tkcalendar import Calendar

from lb_in_arreas import dias_habiles, obtener_tasas_banxico

FONDO = "#FFF9DF"
FONDO_CAMPO = "#FFFFFF"
FONDO_TEXTO = "#F7E9DF"
ROJO = "#FC0000"
ROJO_OSCURO = "#B20100"
MELOCOTON = "#FCD898"
TEXTO = "#000000"


def calcular(capital, inicio, final, margen, lookback, token):
    feriados = holidays.Mexico()
    final_periodo = final - timedelta(days=1)
    periodo = dias_habiles(inicio, final_periodo, feriados)
    if not periodo:
        raise ValueError("No hay días hábiles en el periodo.")

    d_c = (final - inicio).days
    d_b = len(periodo)

    ventana_ini = inicio - timedelta(days=max(60, lookback * 3))
    tasas_pub = obtener_tasas_banxico(ventana_ini, final_periodo, token)
    fechas_tasas = sorted(tasas_pub)
    indices = {f: i for i, f in enumerate(fechas_tasas)}

    producto = 1.0
    detalle = []
    for i, dia in enumerate(periodo):
        pos = indices.get(dia)
        if pos is None or pos - lookback < 0:
            raise ValueError("No se pudo desfasar con el lookback dado: faltan tasas.")
        fecha_tas = fechas_tasas[pos - lookback]
        R = tasas_pub[fecha_tas]
        siguiente = periodo[i + 1] if i + 1 < len(periodo) else final
        n_i = (siguiente - dia).days
        factor = 1 + R * n_i / 360.0
        producto *= factor
        detalle.append((dia, fecha_tas, R, n_i, factor))

    tasa_pct = round((producto - 1) * 360.0 / d_c * 100, 8)
    tasa_final = round(tasa_pct + margen, 8)
    intereses = capital * (tasa_final / 100.0) * d_c / 360.0
    return d_b, d_c, tasa_pct, tasa_final, intereses, producto, detalle, final_periodo


def abrir_calendario(entry, titulo):
    top = tk.Toplevel()
    top.title(titulo)
    top.grab_set()
    hoy = datetime.now()
    cal = Calendar(top, date_pattern="yyyy-mm-dd", year=hoy.year, month=hoy.month, day=hoy.day)
    cal.pack(padx=10, pady=10)

    def seleccionar():
        entry.delete(0, tk.END)
        entry.insert(0, cal.get_date())
        top.destroy()

    tk.Button(top, text="Aceptar", bg=ROJO, fg="white", command=seleccionar).pack(pady=5)


def formatear_capital(entry):
    try:
        v = float(entry.get().replace(",", "").replace("$", "").strip())
        entry.delete(0, tk.END)
        entry.insert(0, f"{v:,.2f}")
    except ValueError:
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lookback in Arreas")
        self.configure(bg=FONDO)
        self.token = None

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel", background=FONDO, foreground=TEXTO, font=("Segoe UI", 10))
        style.configure("TEntry", fieldbackground=FONDO_CAMPO, font=("Segoe UI", 10))
        style.configure(
            "TButton",
            background=ROJO,
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            padding=6,
        )
        style.map("TButton", background=[("active", ROJO_OSCURO)])
        style.configure("TFrame", background=MELOCOTON)

        ttk.Label(self, text="Lookback in Arreas", font=("Segoe UI", 14, "bold"), foreground=ROJO).grid(
            row=0, column=0, columnspan=3, pady=10
        )

        self.vars = {}
        self.entries = {}

        ttk.Label(self, text="Fecha inicio:").grid(row=1, column=0, padx=10, pady=6, sticky="e")
        self.vars["inicio"] = tk.StringVar()
        e_inicio = ttk.Entry(self, textvariable=self.vars["inicio"], width=20)
        e_inicio.grid(row=1, column=1, padx=5, pady=6, sticky="w")
        ttk.Button(self, text="📅", width=4, command=lambda: abrir_calendario(e_inicio, "Fecha inicio")).grid(row=1, column=2, padx=5)

        ttk.Label(self, text="Fecha fin (día de pago):").grid(row=2, column=0, padx=10, pady=6, sticky="e")
        self.vars["final"] = tk.StringVar()
        e_final = ttk.Entry(self, textvariable=self.vars["final"], width=20)
        e_final.grid(row=2, column=1, padx=5, pady=6, sticky="w")
        ttk.Button(self, text="📅", width=4, command=lambda: abrir_calendario(e_final, "Fecha fin")).grid(row=2, column=2, padx=5)

        campos = [
            ("Saldo Insoluto:", "capital"),
            ("Margen (%):", "margen"),
            ("Lookback (días):", "lookback"),
        ]
        for r, (label, key) in enumerate(campos, start=3):
            ttk.Label(self, text=label).grid(row=r, column=0, padx=10, pady=6, sticky="e")
            v = tk.StringVar()
            self.vars[key] = v
            e = ttk.Entry(self, textvariable=v, width=20)
            e.grid(row=r, column=1, padx=5, pady=6, sticky="w")
            self.entries[key] = e
            if key == "capital":
                e.bind("<FocusOut>", lambda ev, e=e: formatear_capital(e))

        ttk.Button(self, text="Calcular", command=self.on_calcular).grid(row=6, column=0, columnspan=3, pady=12)

        self.resultado = tk.Text(self, width=75, height=26, bg=FONDO_TEXTO, fg=TEXTO, font=("Consolas", 9))
        self.resultado.grid(row=7, column=0, columnspan=3, padx=10, pady=10)
        self.resultado.config(state="disabled")

    def on_calcular(self):
        if not self.token:
            self.token = simpledialog.askstring(
                "Token", "Token de Banxico:", show="*", parent=self
            )
            if not self.token:
                return
        try:
            inicio = datetime.strptime(self.vars["inicio"].get().strip(), "%Y-%m-%d").date()
            final = datetime.strptime(self.vars["final"].get().strip(), "%Y-%m-%d").date()
            capital = float(self.vars["capital"].get().replace(",", "").replace("$", ""))
            margen = float(self.vars["margen"].get())
            lookback = int(self.vars["lookback"].get())
            d_b, d_c, tasa, tasa_final, intereses, producto, detalle, final_periodo = calcular(
                capital, inicio, final, margen, lookback, self.token
            )
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al consultar Banxico: {e}")
            return

        lineas = [
            f"Periodo de intereses: {inicio} a {final_periodo}  (pago: {final})",
            f"Días hábiles: {d_b} | Días calendario: {d_c} | Lookback: {lookback}",
            "",
            "--- Paso 1: Desglose diario ---",
            f"{'Día':<12}{'Tasa pub.':<12}{'R (%)':>10}{'n_i':>5}{'Factor':>16}",
        ]
        for dia, fecha_tas, R, n_i, factor in detalle:
            lineas.append(f"{dia!s:<12}{fecha_tas!s:<12}{R*100:>10.4f}{n_i:>5}{factor:>16.8f}")
        lineas += [
            "",
            "--- Paso 2: Compuesto ---",
            f"Producto de factores: {producto:.10f}",
            f"Tasa compuesta TIIE:  {tasa:.8f} %",
            "",
            "--- Paso 3: Tasa Integrada ---",
            f"Tasa integrada: {tasa:.8f} + {margen:.8f} = {tasa_final:.8f} %",
            "",
            "--- Paso 4: Intereses (base 360) ---",
            f"Intereses = ${capital:,.2f} × {tasa_final}% × {d_c}/360 = ${intereses:,.2f}",
        ]
        texto = "\n".join(lineas)
        self.resultado.config(state="normal")
        self.resultado.delete("1.0", "end")
        self.resultado.insert("1.0", texto)
        self.resultado.config(state="disabled")


if __name__ == "__main__":
    App().mainloop()
