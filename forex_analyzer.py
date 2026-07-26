#!/usr/bin/env python3
"""
Forex Correlation Analyzer
Pares: USD/JPY, EUR/JPY, EUR/USD
- Analiza correlaciones históricas y en tiempo real
- Salida en terminal con tabla actualizada cada minuto
"""

import time
import sys
from datetime import datetime, timedelta, timezone

try:
    import yfinance as yf
except ImportError:
    print("Instala dependencias: pip install -r requirements.txt")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("Instala dependencias: pip install -r requirements.txt")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    from rich.layout import Layout
    from rich.live import Live
except ImportError:
    print("Instala dependencias: pip install -r requirements.txt")
    sys.exit(1)

# ── Configuración ────────────────────────────────────────────────────────────

PAIRS = {
    "USD/JPY": "USDJPY=X",
    "EUR/JPY": "EURJPY=X",
    "EUR/USD": "EURUSD=X",
}

WINDOWS = {
    "15 min":  15,
    "1 hora":  60,
    "4 horas": 240,
    "1 día":   1440,
}

REFRESH_SECONDS = 60

console = Console()

# ── Descarga de datos ────────────────────────────────────────────────────────

def fetch_history(period: str = "5d", interval: str = "1m") -> pd.DataFrame:
    """Descarga datos históricos de los 3 pares y los une en un DataFrame."""
    frames = {}
    for name, ticker in PAIRS.items():
        try:
            df = yf.download(ticker, period=period, interval=interval,
                             progress=False, auto_adjust=True)
            if not df.empty:
                frames[name] = df["Close"].squeeze()
        except Exception as exc:
            console.print(f"[yellow]Advertencia: no se pudo descargar {name} ({ticker}): "
                          f"{type(exc).__name__}: {exc}[/yellow]")

    if not frames:
        return pd.DataFrame()

    combined = pd.DataFrame(frames)
    combined.index = pd.to_datetime(combined.index, utc=True)
    combined = combined.ffill().dropna()
    return combined


def fetch_latest_price() -> dict:
    """Obtiene el precio más reciente de cada par."""
    prices = {}
    for name, ticker in PAIRS.items():
        try:
            df = yf.download(ticker, period="1d", interval="1m",
                             progress=False, auto_adjust=True)
            if not df.empty:
                prices[name] = float(df["Close"].squeeze().iloc[-1])
        except Exception as exc:
            console.print(f"[yellow]Advertencia: precio no disponible para {name}: "
                          f"{type(exc).__name__}: {exc}[/yellow]")
            prices[name] = None
    return prices

# ── Análisis de correlaciones ────────────────────────────────────────────────

def compute_correlations(df: pd.DataFrame) -> dict:
    """
    Calcula la correlación de Pearson entre cada par de divisas
    en distintas ventanas temporales (filas = minutos).
    Devuelve dict[ventana][par_de_pares] = correlación
    """
    pair_combos = [
        ("USD/JPY", "EUR/JPY"),
        ("USD/JPY", "EUR/USD"),
        ("EUR/JPY", "EUR/USD"),
    ]
    results = {}
    for label, minutes in WINDOWS.items():
        window_df = df.tail(minutes) if len(df) >= minutes else df
        corrs = {}
        for a, b in pair_combos:
            if a in window_df.columns and b in window_df.columns:
                c = window_df[a].corr(window_df[b])
                corrs[f"{a} ↔ {b}"] = round(c, 4) if pd.notna(c) else None
            else:
                corrs[f"{a} ↔ {b}"] = None
        results[label] = corrs
    return results


def detect_divergence_events(df: pd.DataFrame, threshold: float = 0.005) -> list:
    """
    Detecta momentos donde un par sube y otro baja simultáneamente
    (divergencia porcentual > threshold en el mismo minuto).
    threshold es un valor decimal: 0.005 equivale a 0.5%.
    Retorna lista de dicts con timestamp y descripción.
    """
    if df.empty or len(df) < 2:
        return []

    pct = df.pct_change().dropna()
    events = []

    pair_combos = [
        ("USD/JPY", "EUR/JPY"),
        ("USD/JPY", "EUR/USD"),
        ("EUR/JPY", "EUR/USD"),
    ]

    for idx, row in pct.iterrows():
        for a, b in pair_combos:
            if a not in row or b not in row:
                continue
            va, vb = row[a], row[b]
            if abs(va) < threshold or abs(vb) < threshold:
                continue
            if (va > 0 and vb < 0) or (va < 0 and vb > 0):
                direction_a = "↑" if va > 0 else "↓"
                direction_b = "↑" if vb > 0 else "↓"
                events.append({
                    "timestamp": idx,
                    "descripcion": (
                        f"{a} {direction_a} {va*100:+.3f}% / "
                        f"{b} {direction_b} {vb*100:+.3f}%"
                    ),
                })

    # Mantener solo los últimos 20 eventos para no saturar la pantalla
    return events[-20:]


def summarize_divergence_stats(events: list) -> dict:
    """
    Calcula estadísticas básicas sobre los eventos de divergencia detectados:
    cuántos hay por par y frecuencia aproximada.
    """
    stats: dict[str, int] = {}
    for ev in events:
        key = " ↔ ".join(
            part.split(" ")[0] for part in ev["descripcion"].split(" / ")
        )
        stats[key] = stats.get(key, 0) + 1
    return stats

# ── Renderizado de tablas ────────────────────────────────────────────────────

def color_corr(value) -> str:
    """Colorea la correlación según su signo e intensidad."""
    if value is None:
        return "[dim]N/A[/dim]"
    if value >= 0.7:
        return f"[bold green]{value:+.4f}[/bold green]"
    if value >= 0.3:
        return f"[green]{value:+.4f}[/green]"
    if value > -0.3:
        return f"[yellow]{value:+.4f}[/yellow]"
    if value > -0.7:
        return f"[red]{value:+.4f}[/red]"
    return f"[bold red]{value:+.4f}[/bold red]"


def build_price_table(prices: dict, df: pd.DataFrame) -> Table:
    """Tabla con precios actuales y cambio del último minuto."""
    table = Table(title="💱 Precios actuales", box=box.ROUNDED,
                  border_style="cyan", expand=True)
    table.add_column("Par", style="bold white", justify="center")
    table.add_column("Precio", justify="right")
    table.add_column("Δ 1 min", justify="right")

    for name in PAIRS:
        price = prices.get(name)
        price_str = f"{price:.4f}" if price else "N/A"

        delta_str = "—"
        if not df.empty and name in df.columns and len(df) >= 2 and price:
            prev = float(df[name].iloc[-2])
            delta = price - prev
            delta_pct = (delta / prev) * 100 if prev else 0
            arrow = "↑" if delta >= 0 else "↓"
            color = "green" if delta >= 0 else "red"
            delta_str = f"[{color}]{arrow} {delta_pct:+.4f}%[/{color}]"

        table.add_row(name, price_str, delta_str)

    return table


def build_correlation_table(corr_data: dict) -> Table:
    """Tabla de correlaciones por ventana de tiempo."""
    table = Table(title="📊 Correlaciones (Pearson)", box=box.ROUNDED,
                  border_style="magenta", expand=True)
    table.add_column("Par de divisas", style="bold white")

    windows_list = list(WINDOWS.keys())
    for w in windows_list:
        table.add_column(w, justify="center")

    # Obtener todas las combinaciones de pares
    all_pairs = set()
    for window_data in corr_data.values():
        all_pairs.update(window_data.keys())

    for pair_combo in sorted(all_pairs):
        row = [pair_combo]
        for w in windows_list:
            val = corr_data.get(w, {}).get(pair_combo)
            row.append(color_corr(val))
        table.add_row(*row)

    return table


def build_events_table(events: list) -> Table:
    """Tabla con los últimos eventos de divergencia detectados."""
    threshold_pct = int(0.005 * 100 * 10) / 10  # 0.5%
    table = Table(
        title=f"⚡ Últimos eventos de divergencia (umbral ≥ {threshold_pct}%)",
        box=box.SIMPLE_HEAD, border_style="yellow", expand=True
    )
    table.add_column("Timestamp (UTC)", style="dim", min_width=22)
    table.add_column("Evento", style="white")

    if not events:
        table.add_row("—", "[dim]Sin eventos detectados aún[/dim]")
    else:
        for ev in reversed(events[-10:]):  # mostrar los 10 más recientes
            ts = ev["timestamp"]
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if hasattr(ts, "strftime") else str(ts)
            table.add_row(ts_str, ev["descripcion"])

    return table


def build_stats_table(events: list) -> Table:
    """Tabla resumen de frecuencia de divergencias."""
    stats = summarize_divergence_stats(events)
    total = len(events)

    table = Table(title="📈 Estadísticas de divergencia (histórico)",
                  box=box.SIMPLE, border_style="blue", expand=True)
    table.add_column("Combinación", style="bold white")
    table.add_column("Ocurrencias", justify="right")
    table.add_column("% del total", justify="right")

    for key, count in sorted(stats.items(), key=lambda x: -x[1]):
        pct = (count / total * 100) if total else 0
        table.add_row(key, str(count), f"{pct:.1f}%")

    if not stats:
        table.add_row("[dim]—[/dim]", "0", "0%")

    return table

# ── Loop principal ───────────────────────────────────────────────────────────

def render_all(df: pd.DataFrame, prices: dict, events: list) -> str:
    """Construye y renderiza todas las tablas en la consola."""
    corr_data = compute_correlations(df)

    console.clear()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    console.print(
        Panel(
            f"[bold cyan]FOREX CORRELATION ANALYZER[/bold cyan]  |  "
            f"Pares: USD/JPY · EUR/JPY · EUR/USD  |  "
            f"[dim]Actualizado: {now}  —  próxima actualización en {REFRESH_SECONDS}s[/dim]",
            box=box.DOUBLE,
        )
    )

    # Precios actuales
    console.print(build_price_table(prices, df))

    # Correlaciones
    console.print()
    console.print(build_correlation_table(corr_data))

    # Leyenda de correlaciones
    console.print(
        "[bold green]■[/bold green] ≥ 0.7 muy positiva  "
        "[green]■[/green] 0.3–0.7 positiva  "
        "[yellow]■[/yellow] -0.3–0.3 neutra  "
        "[red]■[/red] -0.7–-0.3 negativa  "
        "[bold red]■[/bold red] ≤ -0.7 muy negativa"
    )

    # Eventos y estadísticas
    console.print()
    console.print(build_events_table(events))
    console.print()
    console.print(build_stats_table(events))
    console.print()
    console.print("[dim]Presiona Ctrl+C para salir.[/dim]")


def main():
    console.print("[bold cyan]Iniciando Forex Correlation Analyzer...[/bold cyan]")
    console.print("[dim]Descargando datos históricos (últimos 5 días, intervalo 1 min)...[/dim]")
    console.print("[dim]Esto puede tardar unos segundos.[/dim]\n")

    # Carga histórica inicial
    df = fetch_history(period="5d", interval="1m")

    if df.empty:
        console.print("[bold red]Error: no se pudieron obtener datos. "
                      "Verifica tu conexión a internet.[/bold red]")
        sys.exit(1)

    # Detectar eventos históricos
    events = detect_divergence_events(df)

    # Primera renderización
    prices = fetch_latest_price()
    render_all(df, prices, events)

    # Loop de actualización
    try:
        while True:
            time.sleep(REFRESH_SECONDS)

            # Descargar último minuto y adjuntar al DataFrame histórico
            new_data = fetch_history(period="1d", interval="1m")
            if not new_data.empty:
                # Combinar sin duplicados y mantener los últimos 7 días
                df = pd.concat([df, new_data])
                has_dups = df.index.duplicated().any()
                if has_dups:
                    df = df[~df.index.duplicated(keep="last")].sort_index()
                else:
                    df = df.sort_index()
                cutoff = pd.Timestamp.now(tz="UTC") - timedelta(days=7)
                df = df[df.index >= cutoff]

                new_events = detect_divergence_events(new_data)
                # Agregar eventos nuevos sin duplicar por timestamp
                existing_ts = {e["timestamp"] for e in events}
                for ev in new_events:
                    if ev["timestamp"] not in existing_ts:
                        events.append(ev)
                events = events[-100:]  # conservar los últimos 100

            prices = fetch_latest_price()
            render_all(df, prices, events)

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Programa terminado por el usuario.[/bold yellow]")


if __name__ == "__main__":
    main()
