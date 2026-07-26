# 📊 Forex Correlation Analyzer

Analiza en tiempo real las correlaciones entre **USD/JPY**, **EUR/JPY** y **EUR/USD**.

## ¿Qué hace?

- Descarga datos históricos de los últimos 5 días (intervalo de 1 minuto)
- Se actualiza cada 60 segundos con datos nuevos
- Calcula la **correlación de Pearson** entre los pares en ventanas de: 15 min, 1h, 4h y 1 día
- Detecta **eventos de divergencia** (cuando un par sube y otro baja al mismo tiempo)
- Muestra todo en una tabla visual en la terminal

---

## 📱 Instalación en Android (Termux)

### Paso 1 — Instalar Termux
Descarga **Termux** desde [F-Droid](https://f-droid.org/en/packages/com.termux/) (recomendado, no la versión de Play Store que está desactualizada).

### Paso 2 — Preparar el entorno
Abre Termux y ejecuta:

```bash
pkg update && pkg upgrade -y
pkg install python git -y
pip install --upgrade pip
```

### Paso 3 — Descargar el programa
```bash
git clone https://github.com/juanpablovialh-stack/propuesta-cita.git
cd propuesta-cita
```

### Paso 4 — Instalar dependencias
```bash
pip install -r requirements.txt
```

### Paso 5 — Correr el programa
```bash
python forex_analyzer.py
```

Para salir: presiona `Ctrl + C`

---

## 💻 Instalación en PC (Windows / Mac / Linux)

### Requisitos
- Python 3.9 o superior → [python.org](https://www.python.org/downloads/)

### Instalación
```bash
# Clonar o descargar el repositorio
git clone https://github.com/juanpablovialh-stack/propuesta-cita.git
cd propuesta-cita

# Instalar dependencias
pip install -r requirements.txt

# Correr el programa
python forex_analyzer.py
```

---

## 📖 ¿Cómo leer los resultados?

### Tabla de precios
Muestra el precio actual de cada par y el cambio porcentual del último minuto.

### Tabla de correlaciones

| Color | Significado |
|-------|-------------|
| 🟢 Verde fuerte | Correlación muy positiva (≥ 0.7): ambos suben/bajan juntos |
| 🟢 Verde | Correlación positiva (0.3 – 0.7) |
| 🟡 Amarillo | Correlación neutra (-0.3 – 0.3): movimientos independientes |
| 🔴 Rojo | Correlación negativa (-0.7 – -0.3): cuando uno sube, el otro baja |
| 🔴 Rojo fuerte | Correlación muy negativa (≤ -0.7) |

### Eventos de divergencia
Momentos en los que un par subió ≥ 0.5% mientras el otro bajó ≥ 0.5% en el mismo minuto.

### Estadísticas históricas
Cuántas veces ocurrió cada tipo de divergencia en los datos analizados.

---

## 🔧 Dependencias

| Librería | Uso |
|----------|-----|
| `yfinance` | Descarga de precios forex desde Yahoo Finance |
| `pandas` | Procesamiento y correlación de datos |
| `rich` | Tablas visuales en terminal |
