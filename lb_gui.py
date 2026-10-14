import base64
import io
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

import holidays
from matplotlib.figure import Figure
from tkcalendar import Calendar

from lb_in_arreas import dias_habiles, obtener_tasas_banxico, obtener_tasas_sofr

PALETA_TIIE = {
    "fondo": "#FFF9DF",
    "campo": "#FFFFFF",
    "caja": "#F7E9DF",
    "acento": "#FC0000",
    "acento_osc": "#B20100",
    "enc_tabla": "#FCD898",
    "fila_par": "#FFFFFF",
    "fila_imp": "#FFF3D6",
    "resaltado": "#FDE4E1",
    "tab": "#FC0000",
    "tab_txt": "#FFFFFF",
    "tab_sel": "#FF3320",
    "tab_unsel": "#E28C88",
    "tab_unsel_txt": "#FFF5F4",
    "nota": "Tasa TIIE diaria (Banxico, serie SF331451) · feriados CNBV · token requerido",
    "dec_calc": 8,
    "dec_tasa": 4,
}

PALETA_SOFR = {
    "fondo": "#EAF9FA",
    "campo": "#FFFFFF",
    "caja": "#DFF6F7",
    "acento": "#00B38D",
    "acento_osc": "#008E6B",
    "enc_tabla": "#9FE6E9",
    "fila_par": "#FFFFFF",
    "fila_imp": "#E3F7F4",
    "resaltado": "#DEF8F5",
    "tab": "#00C4CB",
    "tab_txt": "#00343A",
    "tab_sel": "#4FE0E4",
    "tab_unsel": "#9DDFE3",
    "tab_unsel_txt": "#004A4F",
    "nota": "Tasa SOFR diaria (New York Fed) · feriados FED · sin token · ACT/360",
    "dec_calc": 9,
    "dec_tasa": 5,
}


def calcular(capital, inicio, final, margen, lookback, dec_calc, dec_tasa, feriados, obtener_tasas):
    final_periodo = final - timedelta(days=1)
    periodo = dias_habiles(inicio, final_periodo, feriados)
    if not periodo:
        raise ValueError("No hay días hábiles en el periodo.")

    d_c = (final - inicio).days
    d_b = len(periodo)

    ventana_ini = inicio - timedelta(days=max(60, lookback * 3))
    tasas_pub = obtener_tasas(ventana_ini, final_periodo)
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

    tk.Button(top, text="Aceptar", bg="#333333", fg="white", command=seleccionar).pack(pady=5)


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


class Pestana(tk.Frame):
    def __init__(self, master, metodo, paleta, con_token, feriados):
        super().__init__(master, bg=paleta["fondo"])
        self.metodo = metodo
        self.p = paleta
        self.con_token = con_token
        self._feriados = feriados
        self._fotos = []
        self.intereses_texto = ""
        self._construir()

    def _construir(self):
        p = self.p
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        izq = tk.Frame(self, bg=p["fondo"])
        izq.grid(row=0, column=0, sticky="nw", padx=20, pady=10)
        der = tk.Frame(self, bg=p["fondo"])
        der.grid(row=0, column=1, sticky="nsew", padx=20, pady=10)
        der.grid_columnconfigure(0, weight=1)
        self.der = der

        tk.Label(
            izq, text=f"Lookback in Arreas — {self.metodo}",
            font=("Segoe UI", 14, "bold"), fg=p["acento"], bg=p["fondo"],
        ).grid(row=0, column=0, columnspan=3, pady=(10, 2))
        tk.Label(
            izq, text=p["nota"], font=("Segoe UI", 8), fg="#555555", bg=p["fondo"],
        ).grid(row=1, column=0, columnspan=3, pady=(0, 8))

        self.vars = {}

        tk.Label(izq, text="Fecha inicio:", bg=p["fondo"], font=("Segoe UI", 10)).grid(
            row=2, column=0, padx=10, pady=4, sticky="e"
        )
        self.vars["inicio"] = tk.StringVar()
        e_inicio = tk.Entry(izq, textvariable=self.vars["inicio"], width=20, bg=p["campo"], relief="solid", bd=1)
        e_inicio.grid(row=2, column=1, padx=5, pady=4, sticky="w")
        tk.Button(
            izq, text="📅", width=3, bg=p["acento"], fg="white", font=("Segoe UI", 8),
            activebackground=p["acento_osc"],
            command=lambda: abrir_calendario(e_inicio, f"{self.metodo} – Fecha inicio"),
        ).grid(row=2, column=2, padx=5, pady=4)

        tk.Label(izq, text="Fecha fin (día de pago):", bg=p["fondo"], font=("Segoe UI", 10)).grid(
            row=3, column=0, padx=10, pady=4, sticky="e"
        )
        self.vars["final"] = tk.StringVar()
        e_final = tk.Entry(izq, textvariable=self.vars["final"], width=20, bg=p["campo"], relief="solid", bd=1)
        e_final.grid(row=3, column=1, padx=5, pady=4, sticky="w")
        tk.Button(
            izq, text="📅", width=3, bg=p["acento"], fg="white", font=("Segoe UI", 8),
            activebackground=p["acento_osc"],
            command=lambda: abrir_calendario(e_final, f"{self.metodo} – Fecha fin"),
        ).grid(row=3, column=2, padx=5, pady=4)

        campos = [
            ("Saldo Insoluto:", "capital"),
            ("Margen (%):", "margen"),
            ("Lookback (días):", "lookback"),
        ]
        if self.con_token:
            campos.append(("Token Banxico:", "token"))
        campos += [
            ("Decimales cálculo:", "dec_calc"),
            ("Decimales tasa:", "dec_tasa"),
        ]
        fila = 4
        for label, key in campos:
            tk.Label(izq, text=label, bg=p["fondo"], font=("Segoe UI", 10)).grid(
                row=fila, column=0, padx=10, pady=4, sticky="e"
            )
            v = tk.StringVar()
            self.vars[key] = v
            e = tk.Entry(
                izq, textvariable=v, width=20, bg=p["campo"], relief="solid", bd=1,
                show="*" if key == "token" else "",
            )
            e.grid(row=fila, column=1, padx=5, pady=4, sticky="w")
            if key == "capital":
                e.bind("<FocusOut>", lambda ev, e=e: formatear_capital(e))
            fila += 1
        self.vars["dec_calc"].set(str(p["dec_calc"]))
        self.vars["dec_tasa"].set(str(p["dec_tasa"]))

        fila_boton = fila
        tk.Button(
            izq, text="Calcular", bg=p["acento"], fg="white", activebackground=p["acento_osc"],
            font=("Segoe UI", 10, "bold"), padx=14, pady=4, command=self.on_calcular,
        ).grid(row=fila_boton, column=0, columnspan=3, pady=(12, 8))

        resaltado = tk.Frame(izq, bg=p["resaltado"], highlightbackground=p["acento"],
                             highlightthickness=2, bd=0)
        resaltado.grid(row=fila_boton + 1, column=0, columnspan=3, sticky="we", padx=5, pady=(0, 6))
        tk.Label(
            resaltado, text="Intereses", font=("Segoe UI", 9, "bold"),
            fg=p["acento_osc"], bg=p["resaltado"],
        ).grid(row=0, column=0, padx=(10, 8), pady=6, sticky="w")
        self.lbl_intereses = tk.Label(
            resaltado, text="—", font=("Segoe UI", 16, "bold"), fg=p["acento_osc"],
            bg=p["resaltado"],
        )
        self.lbl_intereses.grid(row=0, column=1, padx=4, pady=6, sticky="w")
        self.btn_copiar = tk.Button(
            resaltado, text="Copiar", bg=p["acento"], fg="white", activebackground=p["acento_osc"],
            font=("Segoe UI", 9, "bold"), padx=8, pady=2, command=self.copiar_intereses,
        )
        self.btn_copiar.grid(row=0, column=2, padx=(8, 10), pady=6, sticky="e")
        resaltado.grid_columnconfigure(1, weight=1)

        tk.Label(
            der, text="Detalle tasa", font=("Segoe UI", 14, "bold"),
            fg=p["acento"], bg=p["fondo"],
        ).grid(row=0, column=0, sticky="w", pady=(6, 12))
        self.panel_latex = tk.Frame(der, bg=p["fondo"])
        self.panel_latex.grid(row=1, column=0, sticky="new")
        self.placeholder = tk.Label(
            self.panel_latex,
            text="Aquí se mostrarán los cálculos de la tasa\ndespués de pulsar Calcular.",
            fg="#909090", bg=p["fondo"],
        )
        self.placeholder.grid(row=0, column=0, sticky="w")

        marcos = tk.Frame(der, bg=p["fondo"])
        marcos.grid(row=2, column=0, sticky="new", pady=(14, 0))
        marcos.grid_columnconfigure(0, weight=1)
        marcos.grid_columnconfigure(1, weight=1)

        caja_1 = tk.Frame(marcos, bg=p["fondo"])
        caja_1.grid(row=0, column=0, sticky="new", padx=(0, 10))
        tk.Label(
            caja_1, text="Desglose diario", font=("Segoe UI", 11, "bold"),
            fg=p["acento"], bg=p["fondo"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        marco_tabla = tk.Frame(caja_1, bg=p["fondo"])
        marco_tabla.grid(row=1, column=0, sticky="new")

        columnas = ("dia", "tasapub", "r", "ni", "factor")
        self.tabla = ttk.Treeview(
            marco_tabla, columns=columnas, show="headings", height=10,
            style=f"{self.metodo}.Treeview",
        )
        encabezados = [
            ("dia", "Día periodo", 105, "w"),
            ("tasapub", "Tasa pub. en", 105, "w"),
            ("r", "R (%)", 75, "e"),
            ("ni", "n_i", 50, "e"),
            ("factor", "Factor", 145, "e"),
        ]
        for col, titulo, ancho, alinear in encabezados:
            self.tabla.heading(col, text=titulo)
            self.tabla.column(col, width=ancho, anchor=alinear, stretch=False)
        scroll_tabla = ttk.Scrollbar(marco_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scroll_tabla.set)
        scroll_tabla.pack(side="right", fill="y")
        self.tabla.pack(side="left", fill="both", expand=True)
        self.tabla.tag_configure("par", background=p["fila_par"])
        self.tabla.tag_configure("impar", background=p["fila_imp"])

        caja_2 = tk.Frame(marcos, bg=p["fondo"])
        caja_2.grid(row=0, column=1, sticky="new", padx=(10, 0))
        tk.Label(
            caja_2, text="Cálculo de intereses", font=("Segoe UI", 11, "bold"),
            fg=p["acento"], bg=p["fondo"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        marco_resumen = tk.Frame(caja_2, bg=p["fondo"])
        marco_resumen.grid(row=1, column=0, sticky="new")

        self.resumen = tk.Text(
            marco_resumen, width=64, height=14, bg=p["caja"], fg="#000000",
            font=("Consolas", 9), relief="solid", borderwidth=1, padx=8, pady=6,
        )
        scroll_resumen = ttk.Scrollbar(marco_resumen, orient="vertical", command=self.resumen.yview)
        self.resumen.configure(yscrollcommand=scroll_resumen.set)
        scroll_resumen.pack(side="right", fill="y")
        self.resumen.pack(side="left", fill="both", expand=True)
        self.resumen.tag_configure("titulo", font=("Segoe UI", 9, "bold"), foreground=p["acento_osc"])
        self.resumen.tag_configure("dato", font=("Consolas", 9, "bold"))
        self.resumen.insert("end", "Sin cálculos. Pulsa «Calcular» para ver el detalle.")
        self.resumen.config(state="disabled")

    def copiar_intereses(self):
        if not self.intereses_texto:
            return
        self.clipboard_clear()
        self.clipboard_append(self.intereses_texto)
        self.btn_copiar.config(text="¡Copiado!")
        self.after(1500, lambda: self.btn_copiar.config(text="Copiar"))

    def mostrar_latex(self, formulas):
        self._formulas = formulas
        self._render_latex()

    def _render_latex(self):
        formulas = getattr(self, "_formulas", None)
        if not formulas:
            return
        for w in self.panel_latex.winfo_children():
            w.destroy()
        self._fotos = []
        max_w = self.panel_latex.winfo_width()
        if max_w < 100:
            max_w = 900
        for tex in formulas:
            try:
                foto = latex_photo(tex, dpi=150)
                if foto.width() > max_w:
                    dpi = max(int(150 * max_w * 0.98 / foto.width()), 30)
                    foto = latex_photo(tex, dpi=dpi)
            except Exception as e:
                lbl = tk.Label(
                    self.panel_latex, text=f"[Error al renderizar: {e}]",
                    fg="#B20100", bg=self.p["fondo"],
                )
                lbl.grid(sticky="w", pady=4)
                continue
            self._fotos.append(foto)
            lbl = tk.Label(self.panel_latex, image=foto, bg=self.p["fondo"])
            lbl.grid(sticky="w", pady=8)

    def on_calcular(self):
        p = self.p
        token = None
        if self.con_token:
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
            obtener = (
                (lambda a, b: obtener_tasas_banxico(a, b, token))
                if self.con_token
                else obtener_tasas_sofr
            )
            d_b, d_c, tasa, tasa_final, intereses, producto, detalle, final_periodo = calcular(
                capital, inicio, final, margen, lookback, dec_calc, dec_tasa,
                self._feriados, obtener,
            )
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al consultar la API: {e}")
            return

        self.intereses_texto = f"{intereses:,.2f}"
        self.lbl_intereses.config(text=f"${self.intereses_texto}")

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
        calendario = "CNBV/México" if self.con_token else "FED/EE. UU."
        linea(f"Metodología: {self.metodo} (calendario {calendario})")
        linea(f"Decimales cálculo: {dec_calc} | Decimales tasa: {dec_tasa}")
        linea("")
        linea("--- Paso 2: Compuesto del periodo ---", "titulo")
        linea(f"Producto de factores: {producto:.{max(dec_calc, 8)}f}")
        linea(f"Tasa compuesta {self.metodo}: {tasa:.{d}f} %", "dato")
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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lookback in Arreas")
        self.configure(bg="#FFFFFF")
        try:
            self.state("zoomed")
        except tk.TclError:
            self.attributes("-zoomed", True)

        style = ttk.Style(self)
        style.theme_use("clam")
        for metodo, p in (("TIIE", PALETA_TIIE), ("SOFR", PALETA_SOFR)):
            style.configure(
                f"{metodo}.Treeview",
                background=p["campo"], fieldbackground=p["campo"], foreground="#000000",
                font=("Consolas", 9), rowheight=20,
            )
            style.configure(
                f"{metodo}.Treeview.Heading",
                background=p["enc_tabla"], foreground="#000000",
                font=("Segoe UI", 9, "bold"),
            )
        style.configure("TNotebook", background="#DDDDDD")

        barra = tk.Frame(self, bg="#333333")
        barra.pack(fill="x")
        self.contenido = tk.Frame(self, bg="#FFFFFF")
        self.contenido.pack(fill="both", expand=True)

        self.tab_tiie = Pestana(self.contenido, "TIIE", PALETA_TIIE, True, holidays.Mexico())
        self.tab_sofr = Pestana(self.contenido, "SOFR", PALETA_SOFR, False, holidays.US())

        self.btns = {}
        for metodo, texto in (("TIIE", "TIIE (Banxico)"), ("SOFR", "SOFR (FED)")):
            btn = tk.Button(
                barra, text=texto, bd=0, relief="flat", cursor="hand2",
                font=("Segoe UI", 9, "bold"), padx=10, pady=3,
                command=lambda m=metodo: self.mostrar(m),
            )
            btn.pack(side="left", padx=(8, 0), pady=4)
            self.btns[metodo] = btn

        self.actual = None
        self.mostrar("TIIE")

    def mostrar(self, metodo):
        if self.actual == metodo:
            return
        if self.actual == "TIIE":
            self.tab_tiie.pack_forget()
        elif self.actual == "SOFR":
            self.tab_sofr.pack_forget()
        if metodo == "TIIE":
            self.tab_tiie.pack(fill="both", expand=True)
            self.actual = metodo
            self.update_idletasks()
            self.tab_tiie._render_latex()
            return
        self.tab_sofr.pack(fill="both", expand=True)
        self.actual = metodo
        self.update_idletasks()
        self.tab_sofr._render_latex()

        for m, btn in self.btns.items():
            p = PALETA_TIIE if m == "TIIE" else PALETA_SOFR
            activo = m == metodo
            btn.configure(
                bg=p["tab"] if activo else p["tab_unsel"],
                fg=p["tab_txt"] if activo else p["tab_unsel_txt"],
                activebackground=p["tab_sel"] if activo else p["tab_unsel"],
                activeforeground=p["tab_txt"] if activo else p["tab_unsel_txt"],
            )


if __name__ == "__main__":
    App().mainloop()
