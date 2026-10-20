"""Interfaz HD para el agente de laptops. Ubicar junto a main.py, .env y data/."""
import ctypes
import json
import os
import queue
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
DATA = BASE / 'data'
load_dotenv(BASE / '.env')

# Mejor nitidez en pantallas Windows de alta resolución.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except (AttributeError, OSError):
    pass

NAVY = '#101f39'
BLUE = '#2563eb'
PALE = '#eff5ff'
BG = '#eef2f8'
INK = '#15253d'
MUTED = '#60718a'
GREEN = '#13875c'

class Tienda:
    def __init__(self, root):
        self.root = root
        root.title('Agente IA | Tienda de laptops — Interfaz HD')
        root.geometry('1280x820')
        root.minsize(940, 660)
        root.configure(bg=BG)
        self.cola = queue.Queue()
        self.ocupado = False
        self.agente = None
        self.config = {'configurable': {'thread_id': 'cliente-interfaz-hd'}}
        self.productos = {}
        self.codigo = tk.StringVar()
        self.cantidad = tk.StringVar(value='1')
        self.total = tk.StringVar(value='Total: $0.00')
        self.saldo = tk.StringVar(value='Saldo disponible: ...')
        self.estado = tk.StringVar(value='Listo para conversar')
        self._crear()
        self.refrescar()
        self.root.after(100, self._procesar)

    def _boton(self, padre, texto, accion, bg=PALE, fg=INK):
        b = tk.Button(padre, text=texto, command=accion, bg=bg, fg=fg,
                      activebackground='#d9e9ff', activeforeground=INK,
                      font=('Segoe UI', 10, 'bold'), relief='flat', bd=0,
                      cursor='hand2', pady=11)
        b.pack(fill='x', pady=4)
        return b

    def _crear(self):
        top = tk.Frame(self.root, bg=NAVY, padx=30, pady=20)
        top.pack(fill='x')
        tk.Label(top, text='AGENTE IA   •   TIENDA DE LAPTOPS', bg=NAVY,
                 fg='white', font=('Segoe UI', 23, 'bold')).pack(anchor='w')
        tk.Label(top, text='Catálogo inteligente  ·  Compras simuladas  ·  Historial JSON',
                 bg=NAVY, fg='#c9dcfa', font=('Segoe UI', 11)).pack(anchor='w', pady=(5, 0))

        body = tk.Frame(self.root, bg=BG, padx=18, pady=18)
        body.pack(fill='both', expand=True)
        left = tk.Frame(body, bg='white', padx=20, pady=18, width=420)
        left.pack(side='left', fill='y', padx=(0, 14))
        left.pack_propagate(False)
        right = tk.Frame(body, bg='white', padx=20, pady=18)
        right.pack(side='left', fill='both', expand=True)

        tk.Label(left, text='CATÁLOGO DE LAPTOPS', bg='white', fg=INK,
                 font=('Segoe UI', 15, 'bold')).pack(anchor='w', pady=(0, 8))
        tk.Label(left, text='Selecciona un modelo para cotizar o comprar', bg='white',
                 fg=MUTED, font=('Segoe UI', 9)).pack(anchor='w', pady=(0, 12))
        self.catalogo = tk.Listbox(left, font=('Segoe UI', 11), height=10,
                                   bg='#f6f9fe', fg=INK, selectbackground='#d7e7ff',
                                   selectforeground=NAVY, relief='flat', bd=0,
                                   highlightthickness=1, highlightbackground='#dce5f2',
                                   activestyle='none', exportselection=False)
        self.catalogo.pack(fill='x', pady=(0, 12))
        self.catalogo.bind('<<ListboxSelect>>', lambda _: self._actualizar_total())
        self.catalogo.bind('<Double-Button-1>', lambda _: self.cotizar())
        self.codigos = []
        self._boton(left, 'Consultar precio y disponibilidad', self.cotizar, BLUE, 'white')

        compra = tk.Frame(left, bg='#f6f9fe', padx=13, pady=12)
        compra.pack(fill='x', pady=(10, 10))
        tk.Label(compra, text='CANTIDAD', bg='#f6f9fe', fg=INK,
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        fila = tk.Frame(compra, bg='#f6f9fe')
        fila.pack(fill='x', pady=(7, 8))
        tk.Button(fila, text='−', width=4, command=lambda: self._paso(-1),
                  bg='#e2eafa', relief='flat', font=('Segoe UI', 13, 'bold')).pack(side='left')
        campo = ttk.Entry(fila, textvariable=self.cantidad, width=7, justify='center',
                          font=('Segoe UI', 12))
        campo.pack(side='left', padx=8, ipady=5)
        tk.Button(fila, text='+', width=4, command=lambda: self._paso(1),
                  bg='#e2eafa', relief='flat', font=('Segoe UI', 13, 'bold')).pack(side='left')
        self.cantidad.trace_add('write', lambda *_: self._actualizar_total())
        tk.Label(compra, textvariable=self.total, bg='#f6f9fe', fg=NAVY,
                 font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        self.comprar_boton = self._boton(left, '🛒  COMPRAR LAPTOP', self.comprar, GREEN, 'white')
        self._boton(left, 'Consultar saldo', lambda: self.enviar_auto('¿Cuál es mi saldo disponible?'))
        self._boton(left, 'Ver movimientos y comprobantes', lambda: self.enviar_auto('Muéstrame mis movimientos y comprobantes.'))
        self._boton(left, 'Actualizar catálogo JSON', self.refrescar)
        tk.Label(left, textvariable=self.saldo, bg='white', fg=GREEN,
                 font=('Segoe UI', 13, 'bold')).pack(anchor='w', pady=(13, 4))
        tk.Label(left, text='Simulación educativa: no se realizan pagos reales.',
                 bg='white', fg=MUTED, font=('Segoe UI', 9), wraplength=360).pack(anchor='w')

        tk.Label(right, text='CHAT CON TU AGENTE DE IA', bg='white', fg=INK,
                 font=('Segoe UI', 15, 'bold')).pack(anchor='w', pady=(0, 4))
        tk.Label(right, text='Escribe preguntas, cotiza modelos o solicita compras',
                 bg='white', fg=MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 14))
        # Reservar la franja inferior ANTES de expandir el chat.
        # Así el campo de teclado siempre permanece visible.
        entrada_panel = tk.Frame(right, bg='white', pady=8)
        entrada_panel.pack(side='bottom', fill='x')
        tk.Label(entrada_panel, text='ESCRIBE TU MENSAJE  •  ENTER PARA ENVIAR',
                 bg='white', fg=MUTED, font=('Segoe UI', 9, 'bold')).pack(side='top', anchor='w', pady=(0, 6))
        enviar_fila = tk.Frame(entrada_panel, bg='white')
        enviar_fila.pack(fill='x')
        self.entrada = tk.Entry(enviar_fila, font=('Segoe UI', 12), bg='#f6f9fe',
                                fg=INK, insertbackground=INK, relief='solid', bd=1)
        self.entrada.pack(side='left', fill='x', expand=True, ipady=12, padx=(0, 10))
        self.entrada.bind('<Return>', lambda _: (self.enviar(), 'break')[1])
        self.enviar_boton = tk.Button(enviar_fila, text='Enviar  ➜', command=self.enviar,
                                      bg=BLUE, fg='white', font=('Segoe UI', 11, 'bold'),
                                      relief='flat', bd=0, padx=23, cursor='hand2')
        self.enviar_boton.pack(side='right', fill='y')
        tk.Label(entrada_panel, textvariable=self.estado, bg='white', fg=MUTED,
                 font=('Segoe UI', 9)).pack(anchor='w', pady=(8, 0))

        # El chat ocupa únicamente el espacio restante.
        chat_frame = tk.Frame(right, bg='#f6f9fe', highlightthickness=1,
                              highlightbackground='#e0e8f5')
        chat_frame.pack(side='top', fill='both', expand=True)
        self.chat = tk.Text(chat_frame, state='disabled', wrap='word',
                            font=('Segoe UI', 11), bg='#f6f9fe', fg=INK,
                            relief='flat', padx=17, pady=16, spacing3=8)
        barra = ttk.Scrollbar(chat_frame, command=self.chat.yview)
        self.chat.configure(yscrollcommand=barra.set)
        barra.pack(side='right', fill='y')
        self.chat.pack(side='left', fill='both', expand=True)
        self.chat.tag_configure('usuario', foreground=BLUE, font=('Segoe UI', 11, 'bold'))
        self.chat.tag_configure('agente', foreground=INK)
        self.chat.tag_configure('sistema', foreground='#9a6518')
        self.mensaje('sistema', '¡Bienvenido! Selecciona una laptop o escribe un mensaje. Para comprar, confirma con: Confirmo CODIGO CANTIDAD.')
        self.entrada.focus_set()

    def mensaje(self, tipo, texto):
        texto = re.sub(r'\*\*(.*?)\*\*', r'\1', str(texto))
        nombres = {'usuario': 'Tú', 'agente': 'Agente IA', 'sistema': 'Sistema'}
        self.chat.configure(state='normal')
        self.chat.insert('end', f'{nombres[tipo]}: ', tipo)
        self.chat.insert('end', texto + '\n\n')
        self.chat.configure(state='disabled')
        self.chat.see('end')

    def refrescar(self):
        try:
            anterior = self.codigo.get()
            self.productos = json.loads((DATA / 'laptops.json').read_text(encoding='utf-8'))
            cuenta = json.loads((DATA / 'account.json').read_text(encoding='utf-8'))
            self.codigos = list(self.productos)
            self.catalogo.delete(0, 'end')
            for cod, p in self.productos.items():
                self.catalogo.insert('end', f"{p['nombre']}  ·  ${float(p['precio']):,.2f}  ·  Stock {p['stock']}")
            if self.codigos:
                idx = self.codigos.index(anterior) if anterior in self.codigos else 0
                self.catalogo.selection_set(idx)
                self.catalogo.activate(idx)
                self.codigo.set(self.codigos[idx])
            self.saldo.set(f"Saldo disponible: ${float(cuenta['saldo']):,.2f}")
            self._actualizar_total()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror('Problema con JSON', str(exc))

    def _seleccion(self):
        sel = self.catalogo.curselection()
        if not sel:
            return None
        return self.codigos[sel[0]]

    def _actualizar_total(self):
        cod = self._seleccion()
        if cod:
            self.codigo.set(cod)
        try:
            cantidad = int(self.cantidad.get())
            precio = float(self.productos[self.codigo.get()]['precio'])
            self.total.set(f'Total: ${precio * cantidad:,.2f}' if cantidad > 0 else 'Cantidad inválida')
        except (ValueError, KeyError, TypeError):
            self.total.set('Total: —')

    def _paso(self, delta):
        try:
            n = int(self.cantidad.get())
        except ValueError:
            n = 1
        self.cantidad.set(str(max(1, min(999, n + delta))))

    def cotizar(self):
        cod = self._seleccion()
        if cod:
            self.enviar_auto(f'Cotiza la laptop {cod}, incluyendo precio y stock.')
        else:
            messagebox.showinfo('Selecciona una laptop', 'Selecciona una laptop primero.')

    def comprar(self):
        if self.ocupado:
            messagebox.showinfo('Espera', 'El agente está respondiendo.')
            return
        cod = self._seleccion()
        if not cod:
            messagebox.showinfo('Selecciona una laptop', 'Selecciona una laptop primero.')
            return
        try:
            n = int(self.cantidad.get())
            if n < 1 or n > 999:
                raise ValueError('Cantidad fuera de rango')
            productos = json.loads((DATA / 'laptops.json').read_text(encoding='utf-8'))
            cuenta = json.loads((DATA / 'account.json').read_text(encoding='utf-8'))
            p = productos[cod]
            total = float(p['precio']) * n
            if n > int(p['stock']):
                messagebox.showwarning('Stock insuficiente', f"Solo hay {p['stock']} unidades disponibles.")
                return
            if total > float(cuenta['saldo']):
                messagebox.showwarning('Saldo insuficiente', f"Total: ${total:,.2f}\nSaldo: ${float(cuenta['saldo']):,.2f}")
                return
        except (ValueError, OSError, KeyError, TypeError) as exc:
            messagebox.showerror('No se puede comprar', f'Revisa cantidad y archivos JSON.\n{exc}')
            return
        if messagebox.askyesno('Confirmar compra simulada',
                               f"Producto: {p['nombre']}\nCantidad: {n}\nTotal: ${total:,.2f}\n\n¿Confirmas la compra simulada?"):
            self.enviar_auto(f'Confirmo {cod} {n}')

    def enviar_auto(self, texto):
        if self.ocupado:
            return
        self.entrada.delete(0, 'end')
        self.entrada.insert(0, texto)
        self.enviar()

    def enviar(self):
        if self.ocupado:
            return
        texto = self.entrada.get().strip()
        if not texto:
            return
        self.entrada.delete(0, 'end')
        self.mensaje('usuario', texto)
        self.ocupado = True
        self.enviar_boton.configure(state='disabled')
        self.comprar_boton.configure(state='disabled')
        self.estado.set('El agente está respondiendo...')
        threading.Thread(target=self._consultar, args=(texto,), daemon=True).start()

    def _consultar(self, texto):
        try:
            if not os.getenv('OPENAI_API_KEY'):
                raise RuntimeError('Falta OPENAI_API_KEY en .env')
            if self.agente is None:
                from main import app
                self.agente = app
            from langchain_core.messages import HumanMessage
            resultado = self.agente.invoke({'messages': [HumanMessage(content=texto)]}, config=self.config)
            self.cola.put(('agente', str(resultado['messages'][-1].content)))
        except Exception as exc:
            self.cola.put(('sistema', f'Error: {exc}'))
        finally:
            self.cola.put(('terminado', ''))

    def _procesar(self):
        try:
            while True:
                tipo, contenido = self.cola.get_nowait()
                if tipo == 'terminado':
                    self.ocupado = False
                    self.enviar_boton.configure(state='normal')
                    self.comprar_boton.configure(state='normal')
                    self.estado.set('Listo para conversar')
                    self.refrescar()
                    self.entrada.focus_set()
                else:
                    self.mensaje(tipo, contenido)
        except queue.Empty:
            pass
        self.root.after(100, self._procesar)

if __name__ == '__main__':
    ventana = tk.Tk()
    Tienda(ventana)
    ventana.mainloop()
