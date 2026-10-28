# Music Download Manager (mdm)

Aplicación de terminal interactiva para descargar audio (MP3 / FLAC) o video (MP4) desde YouTube, con soporte para listas de reproducción. Usa [yt-dlp](https://github.com/yt-dlp/yt-dlp) y [rich](https://github.com/Textualize/rich).

## Características

- Descarga de pistas individuales o playlists completas.
- Audio: MP3 a 320 / 192 / 128 kbps o FLAC (sin pérdida), con metadatos y carátula incrustados.
- Video: MP4 a 1080p / 720p / 480p / 360p.
- Barras de progreso y tabla resumen (OK / FAIL por pista).
- Reintentos automáticos (esperas de 2, 4 y 8 s) ante errores de descarga.
- En playlists, una pista fallida no detiene el resto.
- Soporte de cookies (navegador o `cookies.txt`) para evitar restricciones de YouTube.
- Configuración persistente.

## Requisitos

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) en el `PATH`
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

## Instalación

```bash
git clone <url-del-repo>
cd music-download-manager
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python mdm.py
```

Menú principal:

1. **Download**: pega una URL de `youtube.com` o `youtu.be`, elige Audio/Video y calidad, confirma.
2. **Settings**: carpeta de descarga, calidad de audio por defecto y cookies.
3. **Exit**.

`Ctrl+C` cancela la operación actual (o sale desde el menú principal).

## Configuración

Se guarda en `~/.config/mdm/config.json`:

| Clave             | Por defecto                | Descripción                                                                 |
|-------------------|----------------------------|-----------------------------------------------------------------------------|
| `download_dir`    | `~/Music/Songs-Downloaded` | Carpeta de salida (se crea si no existe).                                   |
| `default_quality` | `320`                      | Calidad de audio preseleccionada: `320`, `192`, `128` o `flac`.             |
| `browser_cookies` | `none`                     | `none`, nombre de navegador (`chrome`, `safari`, `firefox`, `edge`) o ruta a un `cookies.txt`. |

### Cookies de YouTube

Si YouTube bloquea la descarga (verificación de bot, contenido con restricción de edad), indica en Settings un navegador con sesión iniciada o la ruta a un archivo `cookies.txt`. Un valor que termine en `.txt` o contenga `/` o `\` se trata como archivo; cualquier otro, como nombre de navegador.

## Estructura

```
mdm.py          # Punto de entrada y bucle del menú
ui.py           # Interfaz (rich): menús, prompts, progreso, resumen
downloader.py   # Lógica yt-dlp: info, audio, video, playlist, reintentos
config.py       # Carga/guardado de configuración JSON
tests/          # Tests con pytest
docs/           # Especificación y plan de diseño
```

## Tests

```bash
pytest
```

## Aviso legal

Descarga únicamente contenido sobre el que tengas derechos o permiso, respetando los términos de servicio de YouTube y la legislación de tu país.
