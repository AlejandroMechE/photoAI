# 📸 Face Dataset Studio (Fuzzy Logic Dataset Collector)

Bienvenido al sistema de captura rápida de dataset facial y extracción de matriz lógica difusa (*Fuzzy Logic System*) para el equipo de **6 integrantes**:
**Alan, Alex, Jorge, Marco, Francis y Cristo**.

Este proyecto está configurado con **Sincronización en la Nube (Cloud Storage & Central DB)**. Todas las fotos que tome cada integrante desde su propia computadora se suben automáticamente a la base de datos centralizada de Cloudinary, permitiendo ver el progreso global del equipo en tiempo real.

---

## 📋 Lista de Integrantes y Emociones

- **Integrantes (6):** `Alan`, `Alex`, `Jorge`, `Marco`, `Francis`, `Cristo`
- **Emociones (3):** `Feliz` 😊, `Enojado` 😠, `Triste` 😢
- **Meta por Integrante:** 100 fotos por emoción = **300 fotos por persona**
- **Meta Total del Equipo:** **1,800 fotos** (`dataset_fuzzy_features.csv`)

---

## 🚀 Pasos de Instalación Rápida (Para tus Compañeros)

### 1. Clonar el Repositorio
Abre tu terminal (PowerShell o CMD) y ejecuta:
```bash
git clone https://github.com/AlejandroMechE/photo.git
cd photo
```

### 2. Instalar Dependencias de Python
Asegúrate de tener Python 3.10+ instalado y ejecuta:
```bash
pip install -r requirements.txt
```

### 3. Configurar el Archivo de Claves `.env`
Crea un archivo llamado `.env` en la raíz del proyecto (o copia `.env.example` como `.env`) y pega las siguientes claves del equipo:

```env
CLOUDINARY_URL=cloudinary://183411513584678:xvH9Cdjo30tQVk0mMn81XAfCRnM@nk2cgpxh

CLOUDINARY_CLOUD_NAME=nk2cgpxh
CLOUDINARY_API_KEY=183411513584678
CLOUDINARY_API_SECRET=xvH9Cdjo30tQVk0mMn81XAfCRnM

STORAGE_MODE=cloud
```

---

## 📸 ¿Cómo Usar la Aplicación?

1. **Iniciar el servidor local:**
   ```bash
   python app.py
   ```
2. **Abrir el navegador:** Ve a **[http://127.0.0.1:5000](http://127.0.0.1:5000)**.
3. **Verificar la Nube:** Asegúrate de que la insignia superior diga **<span style="color:#38bdf8;">☁️ Nube Conectada</span>**.
4. **Seleccionar tu Nombre y Emoción:**
   - Selecciona tu usuario (ejemplo: `Alan`).
   - Elige la emoción a capturar (`Feliz`, `Enojado` o `Triste`).
5. **Captura Rápida en Ráfaga:**
   - Alinea tu rostro con la guía ovalada en pantalla.
   - Haz clic en **"Iniciar Captura de 100 Fotos"**. El sistema tomará las 100 fotos automáticamente en ~10 segundos.
   - *Consejo:* Cambia ligeramente de ángulo y gesticulación durante los 10 segundos para darle variedad al dataset.

---

## 🗑️ Borrado y Reintento
- **Borrado Individual:** Pasa el cursor sobre cualquier foto en la galería inferior y haz clic en el bote de basura.
- **Borrar Sección Completa:** Si una ráfaga salió mal (ej. mala iluminación), presiona **"Borrar Sección"** para eliminar la ráfaga completa de ese integrante/emoción y reiniciar el contador a 0.

---

## 📊 Exportar Dataset Lógico Difuso (CSV)
Cualquier integrante puede hacer clic en **"Exportar Dataset Fuzzy (CSV)"** en la barra lateral para descargar el archivo `dataset_fuzzy_features.csv`, el cual contiene las métricas faciales calculadas (`mar`, `mouth_curvature`, `eyebrow_furrow`, `eyebrow_slant`, `ear`) listas para entrenar el modelo de lógica difusa.
