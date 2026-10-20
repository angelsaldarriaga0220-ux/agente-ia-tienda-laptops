"""Agente de compra de laptops: LangGraph + ChatOpenAI + JSON local."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()
BASE = Path(__file__).resolve().parent / "data"
LOCK = Lock()


def leer(nombre):
    return json.loads((BASE / nombre).read_text(encoding="utf-8"))


def guardar(nombre, datos):
    ruta = BASE / nombre
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporal, ruta)


@tool
def cotizar(simbolo: str) -> str:
    """Cotiza una laptop por código, por ejemplo LENOVO-I5; usa LISTA para ver todas."""
    productos = leer("laptops.json")
    if simbolo.upper() == "LISTA":
        return json.dumps(productos, ensure_ascii=False)
    item = productos.get(simbolo.upper())
    return json.dumps(item, ensure_ascii=False) if item else "Modelo no encontrado. Usa LISTA."


@tool
def consultar_saldo() -> str:
    """Devuelve el saldo disponible para comprar laptops."""
    return f"Saldo disponible: ${leer('account.json')['saldo']:.2f}"


@tool
def comprar(simbolo: str, cantidad: int) -> str:
    """Compra laptops SOLO cuando el usuario haya confirmado explícitamente el modelo y cantidad."""
    if cantidad <= 0:
        return "Error: cantidad debe ser positiva."
    with LOCK:
        productos = leer("laptops.json")
        codigo = simbolo.upper()
        item = productos.get(codigo)
        if not item:
            return "Error: modelo no encontrado."
        if item["stock"] < cantidad:
            return "Error: stock insuficiente."
        cuenta = leer("account.json")
        total = round(item["precio"] * cantidad, 2)
        if cuenta["saldo"] < total:
            return f"Saldo insuficiente: necesitas ${total:.2f}, tienes ${cuenta['saldo']:.2f}."
        cuenta["saldo"] = round(cuenta["saldo"] - total, 2)
        item["stock"] -= cantidad
        movimientos = leer("movements.json")
        movimiento = {"id": len(movimientos) + 1, "fecha": datetime.now(timezone.utc).isoformat(),
                      "modelo": codigo, "cantidad": cantidad, "total": total}
        movimientos.append(movimiento)
        guardar("account.json", cuenta)
        guardar("laptops.json", productos)
        guardar("movements.json", movimientos)
        return f"Compra registrada: {movimiento}. Saldo restante: ${cuenta['saldo']:.2f}"


@tool
def ver_movimientos() -> str:
    """Muestra los comprobantes e historial de compras de laptops."""
    return json.dumps(leer("movements.json"), ensure_ascii=False)


HERRAMIENTAS = [cotizar, consultar_saldo, comprar, ver_movimientos]
modelo = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(HERRAMIENTAS)

class Estado(TypedDict):
    messages: Annotated[list, add_messages]

SISTEMA = """Eres un agente de tienda que vende SOLAMENTE laptops.
Usa herramientas para consultar información real de los archivos.
Antes de comprar, consulta el precio, stock y saldo, calcula el total y pregunta
al usuario: '¿Confirmas comprar X unidades del modelo Y por $Z?'.
No llames comprar hasta que el usuario confirme explícitamente en un mensaje posterior.
Si el saldo es insuficiente, informa y no compres.
Si el usuario rechaza, cancela sin cambios.
Nunca inventes compras ni precios. Para ver catálogo usa cotizar con LISTA.
Después de comprar, ofrece mostrar el comprobante mediante ver_movimientos.
"""

def agente(estado: Estado):
    return {"messages": [modelo.invoke([SystemMessage(content=SISTEMA)] + estado["messages"])]}


def herramientas(estado: Estado):
    salidas = []
    for llamada in estado["messages"][-1].tool_calls:
        funcion = next(h for h in HERRAMIENTAS if h.name == llamada["name"])
        # Barrera adicional: comprar exige confirmación reciente y exacta.
        if llamada["name"] == "comprar":
            ultimo = next((m.content for m in reversed(estado["messages"]) if isinstance(m, HumanMessage)), "")
            args = llamada["args"]
            # La confirmación debe mencionar código, cantidad y verbo de aprobación.
            import re
            texto = str(ultimo).lower()
            codigo = str(args.get("simbolo", "")).lower()
            cantidad = str(args.get("cantidad", ""))
            aprobado = bool(re.search(r"\b(confirmo|autorizo|apruebo)\b", texto))
            if not (aprobado and codigo in texto and re.search(rf"(?<!\d){re.escape(cantidad)}(?!\d)", texto)):
                resultado = "Compra bloqueada: escribe 'Confirmo MODELO CANTIDAD' (ej.: Confirmo LENOVO-I5 1)."
            else:
                resultado = funcion.invoke(args)
        else:
            resultado = funcion.invoke(llamada["args"])
        salidas.append(ToolMessage(content=str(resultado), tool_call_id=llamada["id"]))
    return {"messages": salidas}


def decidir(estado: Estado):
    ultimo = estado["messages"][-1]
    return "herramientas" if isinstance(ultimo, AIMessage) and ultimo.tool_calls else END

grafo = StateGraph(Estado)
grafo.add_node("agente", agente)
grafo.add_node("herramientas", herramientas)
grafo.add_edge(START, "agente")
grafo.add_conditional_edges("agente", decidir, {"herramientas": "herramientas", END: END})
grafo.add_edge("herramientas", "agente")
app = grafo.compile(checkpointer=MemorySaver())

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Configura OPENAI_API_KEY en tu archivo .env")
    print("Agente de laptops. Escribe salir para terminar.")
    config = {"configurable": {"thread_id": "cliente-demo"}}
    while True:
        entrada = input("\nTú: ").strip()
        if entrada.lower() in {"salir", "exit"}:
            break
        if not entrada:
            continue
        respuesta = app.invoke({"messages": [HumanMessage(content=entrada)]}, config=config)
        print("Agente:", respuesta["messages"][-1].content)
