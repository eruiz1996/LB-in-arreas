import base64
import io
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

import holidays
from matplotlib.figure import Figure
from tkcalendar import Calendar

from lb_in_arreas import dias_habiles, obtener_tasas_banxico

FONDO = "#FFF9DF"
FONDO_CAMPO = "#FFFFFF"
FONDO_TEXTO = "#F7E9DF"
ROJO = "#FC0000"
ROJO_OSCURO = "#B20100"
MELOCOTON = "#FCD898"
TEXTO = "#000000"


def calcular(capital, inicio, final, margen, lookback, token, dec_calc, dec_tasa):
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
        factor = round(1 + R * n_i / 360.0, dec_calc)
        producto *= factor
        detalle.append((dia, fecha_tas, R, n_i, factor))

    tasa_pct = round((producto - 1) * 360.0 / d_c * 100, dec_tasa)
    tasa_final = round(tasa_pct + margen, dec_tasa)
    intereses = capital * (tasa_final / 100.0) * d_c / 360.0
    return d_b, d_c, tasa_pct, tasa_final, intereses, producto, detalle, final_periodo


def latex_photo(tex, dpi=150):
    fig = Figure(figsize=(2, 1))
    fig.text(0.5, 0.5, f"${tex}$", fontsize=15)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, transparent=True, bbox_inches="tight", pad_inches=0.08)
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()))


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


def leer_entero(valor, nombre):
    try:
        n = int(valor)
    except ValueError:
        raise ValueError(f"{nombre} debe ser un número entero.")
    if n < 0:
        raise ValueError(f"{nombre} debe ser un entero positivo.")
    return n


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lookback in Arreas")
        self.configure(bg=FONDO)
        try:
            self.state("zoomed")
        except tk.TclError:
            self.attributes("-zoomed", True)

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
        style.configure("TFrame", background=FONDO)
        style.configure(
            "Treeview",
            background=FONDO_CAMPO,
            fieldbackground=FONDO_CAMPO,
            foreground=TEXTO,
            font=("Consolas", 9),
            rowheight=20,
        )
        style.configure("Treeview.Heading", background=MELOCOTON, font=("Segoe UI", 9, "bold"))

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        izq = ttk.Frame(self)
        izq.grid(row=0, column=0, sticky="nw", padx=20, pady=10)
        der = ttk.Frame(self)
        der.grid(row=0, column=1, sticky="nsew", padx=20, pady=10)

        ttk.Label(izq, text="Lookback in Arreas", font=("Segoe UI", 14, "bold"), foreground=ROJO).grid(
            row=0, column=0, columnspan=3, pady=10
        )

        self.vars = {}
        self.entries = {}

        ttk.Label(izq, text="Fecha inicio:").grid(row=1, column=0, padx=10, pady=4, sticky="e")
        self.vars["inicio"] = tk.StringVar()
        e_inicio = ttk.Entry(izq, textvariable=self.vars["inicio"], width=20)
        e_inicio.grid(row=1, column=1, padx=5, pady=4, sticky="w")
        ttk.Button(izq, text="📅", width=4, command=lambda: abrir_calendario(e_inicio, "Fecha inicio")).grid(row=1, column=2, padx=5, pady=4)

        ttk.Label(izq, text="Fecha fin (día de pago):").grid(row=2, column=0, padx=10, pady=4, sticky="e")
        self.vars["final"] = tk.StringVar()
        e_final = ttk.Entry(izq, textvariable=self.vars["final"], width=20)
        e_final.grid(row=2, column=1, padx=5, pady=4, sticky="w")
        ttk.Button(izq, text="📅", width=4, command=lambda: abrir_calendario(e_final, "Fecha fin")).grid(row=2, column=2, padx=5, pady=4)

        campos = [
            ("Saldo Insoluto:", "capital"),
            ("Margen (%):", "margen"),
            ("Lookback (días):", "lookback"),
            ("Token Banxico:", "token"),
            ("Decimales cálculo:", "dec_calc"),
            ("Decimales tasa:", "dec_tasa"),
        ]
        for r, (label, key) in enumerate(campos, start=3):
            ttk.Label(izq, text=label).grid(row=r, column=0, padx=10, pady=4, sticky="e")
            v = tk.StringVar()
            self.vars[key] = v
            e = ttk.Entry(izq, textvariable=v, width=20, show="*" if key == "token" else "")
            e.grid(row=r, column=1, padx=5, pady=4, sticky="w")
            self.entries[key] = e
            if key == "capital":
                e.bind("<FocusOut>", lambda ev, e=e: formatear_capital(e))
        self.vars["dec_calc"].set("8")
        self.vars["dec_tasa"].set("4")

        ttk.Button(izq, text="Calcular", command=self.on_calcular).grid(row=9, column=0, columnspan=3, pady=12)

        ttk.Label(
            izq, text="Paso 1: Desglose diario (lookback in arreas)",
            font=("Segoe UI", 11, "bold"), foreground=ROJO,
        ).grid(row=10, column=0, columnspan=3, sticky="w", padx=5, pady=(6, 2))

        marco_tabla = ttk.Frame(izq)
        marco_tabla.grid(row=11, column=0, columnspan=3, sticky="w", padx=5)

        columnas = ("dia", "tasapub", "r", "ni", "factor")
        self.tabla = ttk.Treeview(marco_tabla, columns=columnas, show="headings", height=9)
        encabezados = [
            ("dia", "Día periodo", 110, "w"),
            ("tasapub", "Tasa pub. en", 110, "w"),
            ("r", "R (%)", 80, "e"),
            ("ni", "n_i", 55, "e"),
            ("factor", "Factor", 150, "e"),
        ]
        for col, titulo, ancho, alinear in encabezados:
            self.tabla.heading(col, text=titulo)
            self.tabla.column(col, width=ancho, anchor=alinear, stretch=False)
        scroll_tabla = ttk.Scrollbar(marco_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scroll_tabla.set)
        scroll_tabla.pack(side="right", fill="y")
        self.tabla.pack(side="left", fill="both", expand=True)
        self.tabla.tag_configure("par", background=FONDO_CAMPO)
        self.tabla.tag_configure("impar", background="#FFF3D6")

        marco_resumen = ttk.Frame(izq)
        marco_resumen.grid(row=12, column=0, columnspan=3, sticky="w", padx=5, pady=(10, 0))

        self.resumen = tk.Text(
            marco_resumen, width=72, height=8, bg=FONDO_TEXTO, fg=TEXTO,
            font=("Consolas", 9), relief="solid", borderwidth=1, padx=8, pady=6,
        )
        scroll_resumen = ttk.Scrollbar(marco_resumen, orient="vertical", command=self.resumen.yview)
        self.resumen.configure(yscrollcommand=scroll_resumen.set)
        scroll_resumen.pack(side="right", fill="y")
        self.resumen.pack(side="left", fill="both", expand=True)
        self.resumen.tag_configure("titulo", font=("Segoe UI", 9, "bold"), foreground=ROJO_OSCURO)
        self.resumen.tag_configure("dato", font=("Consolas", 9, "bold"))
        self.resumen.insert("end", "Sin cálculos. Pulsa «Calcular» para ver el detalle.")
        self.resumen.config(state="disabled")

        ttk.Label(der, text="Detalle tasa", font=("Segoe UI", 14, "bold"), foreground=ROJO).pack(
            anchor="w", pady=(10, 20)
        )
        self.panel_latex = ttk.Frame(der)
        self.panel_latex.pack(anchor="nw", fill="x")
        self.placeholder = ttk.Label(
            self.panel_latex,
            text="Aquí se mostrarán los cálculos de la tasa\ndespués de pulsar Calcular.",
            foreground="#B0B0B0",
        )
        self.placeholder.pack(anchor="w")
        self._fotos = []

    def mostrar_latex(self, formulas):
        for w in self.panel_latex.winfo_children():
            w.destroy()
        self._fotos = []
        max_w = self.panel_latex.winfo_width() or 800
        for tex in formulas:
            try:
                foto = latex_photo(tex, dpi=150)
                if foto.width() > max_w:
                    dpi = max(int(150 * max_w * 0.98 / foto.width()), 30)
                    foto = latex_photo(tex, dpi=dpi)
            except Exception as e:
                lbl = ttk.Label(self.panel_latex, text=f"[Error al renderizar: {e}]", foreground=ROJO_OSCURO)
                lbl.pack(anchor="w", pady=4)
                continue
            self._fotos.append(foto)
            lbl = ttk.Label(self.panel_latex, image=foto)
            lbl.pack(anchor="w", pady=8)

    def on_calcular(self):
        token = self.vars["token"].get().strip()
        if not token:
            messagebox.showerror("Error", "Ingresa tu token de Banxico.")
            return
        try:
            dec_calc = leer_entero(self.vars["dec_calc"].get().strip(), "Decimales cálculo")
            dec_tasa = leer_entero(self.vars["dec_tasa"].get().strip(), "Decimales tasa")
            inicio = datetime.strptime(self.vars["inicio"].get().strip(), "%Y-%m-%d").date()
            final = datetime.strptime(self.vars["final"].get().strip(), "%Y-%m-%d").date()
            capital = float(self.vars["capital"].get().replace(",", "").replace("$", ""))
            margen = float(self.vars["margen"].get())
            lookback = int(self.vars["lookback"].get())
            d_b, d_c, tasa, tasa_final, intereses, producto, detalle, final_periodo = calcular(
                capital, inicio, final, margen, lookback, token, dec_calc, dec_tasa
            )
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al consultar Banxico: {e}")
            return

        d = dec_tasa
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)
        for idx, (dia, fecha_tas, R, n_i, factor) in enumerate(detalle):
            self.tabla.insert(
                "", "end",
                tags=("par" if idx % 2 == 0 else "impar",),
                values=(dia, fecha_tas, f"{R * 100:.4f}", n_i, f"{factor:.{dec_calc}f}"),
            )

        resumen = self.resumen
        resumen.config(state="normal")
        resumen.delete("1.0", "end")

        def linea(texto, tag=None):
            resumen.insert("end", texto + "\n", tag)

        linea(f"Periodo de intereses: {inicio} a {final_periodo}  (pago: {final})")
        linea(f"Días hábiles: {d_b} | Días calendario: {d_c} | Lookback: {lookback}")
        linea(f"Decimales cálculo: {dec_calc} | Decimales tasa: {dec_tasa}")
        linea("")
        linea("--- Paso 2: Compuesto del periodo ---", "titulo")
        linea(f"Producto de factores: {producto:.{max(dec_calc, 8)}f}")
        linea(f"Tasa compuesta TIIE: {tasa:.{d}f} %", "dato")
        linea("")
        linea("--- Paso 3: Tasa Integrada ---", "titulo")
        linea(f"Tasa integrada: {tasa:.{d}f}% + {margen:.{d}f}% = {tasa_final:.{d}f}%", "dato")
        linea("")
        linea("--- Paso 4: Intereses (base 360) ---", "titulo")
        linea(f"Intereses = ${capital:,.2f} × {tasa_final:.{d}f}% × {d_c}/360 = ${intereses:,.2f}", "dato")
        resumen.yview_moveto(0)
        resumen.config(state="disabled")

        formulas = [
            r"\prod_{i=1}^{" + str(d_b) + r"}\left(1+\frac{R_i\,n_i}{360}\right)"
            + r" = " + f"{producto:.{max(dec_calc, 8)}f}",
            r"\text{Tasa} = \left[\prod_{i=1}^{" + str(d_b) + r"}\left(1+\frac{R_i\,n_i}{360}\right)-1\right]"
            + r"\times\frac{360}{" + str(d_c) + r"} = " + rf"{tasa:.{d}f}\%",
            r"\text{Tasa integrada} = " + rf"{tasa:.{d}f}\%" + r" + " + rf"{margen:.{d}f}\%"
            + r" = " + rf"{tasa_final:.{d}f}\%",
        ]
        self.mostrar_latex(formulas)


if __name__ == "__main__":
    App().mainloop()
