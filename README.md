# Whisper Ukagaka

Whisper Ukagaka es una aplicacion de escritorio para practicar ingles con agentes visuales tipo ukagaka. La idea central es que el usuario no interactue con una consola fria, sino con personajes que guian ejercicios de gramatica, pronunciacion, escucha y deletreo, mientras un supervisor coordina que agente debe responder y guarda el progreso.

El objetivo de la aplicacion es ayudar a practicar ingles de forma progresiva: recibe texto o voz, decide que modo usar, ejecuta una habilidad especializada, responde con un ukagaka, registra el resultado y adapta la dificultad segun el historial del usuario.

## Tecnologias

- Python 3.11 como lenguaje principal.
- PyQt6 para la interfaz de escritorio.
- Faster Whisper para transcripcion de audio a texto.
- llama.cpp mediante `llama-cpp-python` para correccion local con modelos GGUF.
- pyttsx3 para texto a voz local.
- sounddevice y numpy para grabacion desde microfono.
- SQLite para memoria persistente del usuario.
- Hugging Face Hub para descargar el modelo GGUF si no existe localmente.
- SVG y PNG para el globo de dialogo y personajes ukagaka.

## Estructura Actual

- `main.py`: entrada principal de la aplicacion PyQt.
- `run_ui.py`: alias compatible para iniciar la UI.
- `demo.py`: prueba rapida por consola del skill de correccion.
- `dev.py`: herramientas de desarrollo para crear skills o adapters.
- `src/domain`: entidades y puertos base.
- `src/application`: logica principal separada en `agents`, `modes`, `supervisor`, `memory` y `services`.
- `src/infrastructure`: adaptadores para audio, STT, LLM, TTS, configuracion, carga dinamica de skills y persistencia.
- `src/ui/pyqt`: ventana principal, widgets ukagaka, temas y exportacion de reportes.
- `src/devtools`: scaffolding usado por `dev.py`.
- `skills`: habilidades cargadas dinamicamente en runtime.
- `prompts/agents`: prompts de personalidad para Orion, Nova, Alden, Pulse, Glyph, Echo, Vera y Atlas.
- `prompts/skills`: prompts pedagogicos por modo: `grammar`, `talk`, `listen` y `spell`.
- `prompts/correction_prompt.txt`: plantilla concreta que sigue usando el skill de correccion actual.
- `assets`: personajes, manifests visuales y globo de dialogo.
- `themes`: temas visuales editables.
- `models`: modelos GGUF descargados o colocados manualmente.
- `runtime`: datos generados, grabaciones temporales, SQLite y reportes PDF.
- `tests`: pruebas unitarias del sistema.

Notas de arquitectura:

- La implementacion real vive en subpaquetes bajo `src/application`.
- `main.py` y `run_ui.py` siguen iniciando la app sin requerir capas legacy en `src/application`.
- No se agrego RAG, vector store ni retrieval.

## Inventario de Carpetas

Esta tabla sirve como mapa para futuras limpiezas. Si una carpeta aparece como `Conservar`, la app o las herramientas del proyecto la usan actualmente. Si aparece como `Generada`, no es codigo fuente: puede recrearse o limpiarse con cuidado segun el caso.

| Carpeta | Estado | Uso actual | Criterio |
| --- | --- | --- | --- |
| `.venv` | Generada | Entorno virtual local con dependencias instaladas. | No editar a mano ni documentar como codigo fuente. Se puede borrar solo si se quiere reinstalar el entorno. |
| `assets` | Conservar | Imagenes de personajes, manifests visuales y SVG del globo de dialogo. | Necesaria para que la UI muestre ukagakas y burbujas. |
| `assets/characters` | Conservar | Personajes por agente: `manager`, `grammar`, `conversation`, `transcription`, `spelling`, `voice`, `evaluation`, `learning`. | Mantener carpetas con `manifest.json`; `temp` es reserva para personajes futuros. |
| `assets/ui` | Conservar | Recursos visuales de UI, especialmente `balloons/speech_right.svg`. | Necesaria para el globo de texto. |
| `models` | Generada / local | Modelos GGUF y cache de Hugging Face. | No es codigo. Puede pesar mucho; conservar si no quieres volver a descargar el modelo. |
| `prompts` | Conservar | Prompts de agentes, prompts de modos y plantilla de correccion. | Mantener `prompts/agents`, `prompts/skills` y `correction_prompt.txt` mientras el skill de correccion lo use. |
| `runtime` | Generada | Base SQLite, grabaciones temporales y reportes PDF. | No es codigo. Conservar si quieres historial; limpiar grabaciones/reportes si ocupan espacio. |
| `runtime/data` | Generada importante | Memoria del usuario en `app.sqlite3`. | No borrar salvo que quieras reiniciar progreso. |
| `runtime/recordings` | Generada temporal | WAV creados durante grabacion. | Se puede limpiar si no hay grabacion activa. |
| `runtime/reports` | Generada | PDFs exportados desde `Report`. | Se puede archivar o borrar sin afectar la app. |
| `skills` | Conservar | Skills cargados dinamicamente por `SkillLoader`. | Solo carpetas con `module.py` se cargan en runtime. |
| `skills/correction` | Conservar | Correccion gramatical con LLM y prompt. | Necesaria para `Grammar` y parte de `Talk`. |
| `skills/spelling` | Conservar | Validacion letra por letra. | Necesaria para `Spell`. |
| `skills/transcription` | Conservar | Adaptador skill para STT. | Necesaria para grabacion/audio. |
| `skills/tts` | Conservar | Sintesis de voz. | Necesaria para pronunciar frases/respuestas. |
| `src` | Conservar | Codigo fuente principal. | No borrar. |
| `src/application` | Conservar | Corazon de la app. | Se organiza por `agents`, `modes`, `supervisor`, `memory` y `services`. |
| `src/devtools` | Conservar | Funciones usadas por `dev.py` para scaffolding. | Mantener mientras exista `dev.py` y pruebas de devtools. |
| `src/domain` | Conservar | Entidades y puertos compartidos. | Base de arquitectura. |
| `src/infrastructure` | Conservar | Configuracion, loaders, adapters, persistencia, audio, LLM, STT y TTS. | Necesaria para conectar la app con herramientas reales. |
| `src/ui` | Conservar | Capa de interfaz. | Actualmente solo debe contener `pyqt`. |
| `src/ui/pyqt` | Conservar | App PyQt, ventana, widgets, temas y reportes. | UI real actual. |
| `tests` | Conservar | Pruebas unitarias. | Mantener para verificar cambios antes de limpiar/refactorizar. |
| `themes` | Conservar | Temas editables usados por la UI. | Mantener para cambiar colores desde la app. |
| `__pycache__` | No conservar | Cache generado por Python. | Puede borrarse siempre; Python lo recrea. |

Carpetas eliminadas por estar obsoletas:

| Carpeta | Motivo |
| --- | --- |
| `src/ui/ukagaka` | Era un prototipo minimo de clases `Character`, `Bubble` y `Animation`; la UI real vive en `src/ui/pyqt`. |
| `skills/dev` | Contenia ideas de skills de desarrollo, pero no tenia `module.py` ni participaba en runtime. El scaffolding real vive en `src/devtools` y `dev.py`. |

Regla practica para futuras limpiezas: antes de borrar una carpeta, buscar referencias con `rg "nombre_carpeta"` y correr `python -m unittest`. Si la carpeta contiene datos del usuario (`runtime/data`) o modelos (`models`), tratarla como datos locales, no como codigo descartable.

## Software Necesario

- Windows 10/11.
- Python 3.11.
- Visual Studio Build Tools con la carga `Desktop development with C++`, necesario si `llama-cpp-python` debe compilarse localmente.
- VS Code opcional, recomendado para editar y trabajar con Codex.
- Acceso aceptado al modelo de Hugging Face si se usa Gemma u otro modelo gated.
- Microfono funcional para los modos de voz.

## Instalacion Rapida

Si solo quieres levantar la app en Windows lo mas rapido posible:

```powershell
git clone https://github.com/jporras/spelling-bee.git
cd spelling-bee
.\setup.ps1
Copy-Item .env.example .env
.\.venv\Scripts\Activate.ps1
python .\main.py
```

Antes del primer arranque revisa `.env` y ajusta como minimo:

```env
APP_USER_NAME=guest
UI_THEME=cream
HF_TOKEN=tu_token_de_huggingface
AUTO_DOWNLOAD_MODEL=true
HF_MODEL_REPO=google/gemma-3-4b-it-qat-q4_0-gguf
LLAMA_CPP_MODEL=models/gemma-3-4b-it-q4_0.gguf
FASTER_WHISPER_MODEL=base
TTS_RATE=180
```

Notas rapidas:

- `setup.ps1` crea `.venv`, instala dependencias e intenta reinstalar `llama-cpp-python` usando Visual Studio Build Tools si los detecta.
- En el primer arranque la app puede tardar mientras descarga el modelo GGUF si `AUTO_DOWNLOAD_MODEL=true`.
- La carpeta `models/` no viene incluida en el repo; se crea localmente cuando descargas o copias un modelo.

## Instalacion Detallada

1. Instala Python 3.11 y confirma que `python --version` responda desde PowerShell.
2. Instala Visual Studio Build Tools con la carga `Desktop development with C++`.
3. Clona el repositorio.
4. Crea y activa el entorno virtual.
5. Instala dependencias.
6. Copia `.env.example` a `.env`.
7. Ajusta el modelo y tu token de Hugging Face si vas a usar descarga automatica.
8. Verifica el entorno.
9. Ejecuta la app.

Comandos:

```powershell
git clone https://github.com/jporras/spelling-bee.git
cd spelling-bee
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
.\verify_env.ps1
python .\main.py
```

Variables recomendadas en `.env`:

```env
HF_TOKEN=tu_token_de_huggingface
LLAMA_CPP_MODEL=models/gemma-3-4b-it-q4_0.gguf
AUTO_DOWNLOAD_MODEL=true
HF_MODEL_REPO=google/gemma-3-4b-it-qat-q4_0-gguf
HF_MODEL_FILE=
UI_THEME=cream
APP_USER_NAME=guest
LLAMA_CPP_N_CTX=2048
LLAMA_CPP_TEMPERATURE=0.2
LLAMA_CPP_MAX_TOKENS=256
FASTER_WHISPER_MODEL=base
RECORDING_DURATION_SECONDS=4
TTS_VOICE_NAME=default
TTS_RATE=180
```

## Primer Arranque

- Si `AUTO_DOWNLOAD_MODEL=true`, la app intentara descargar el archivo GGUF configurado en `HF_MODEL_REPO`.
- Si el repositorio de Hugging Face es gated, debes aceptar sus terminos en la web de Hugging Face antes de usar tu token.
- Si prefieres evitar la descarga automatica, coloca manualmente el `.gguf` dentro de `models/` y apunta `LLAMA_CPP_MODEL` a esa ruta.
- La base de datos `runtime/data/app.sqlite3` se crea localmente al usar la app.

## Verificacion

Comprobacion minima:

```powershell
.\verify_env.ps1
```

Pruebas unitarias:

```powershell
python -m unittest
```

## Troubleshooting

### `pip install -r requirements.txt` falla en `llama-cpp-python`

- Asegurate de tener Visual Studio Build Tools con `Desktop development with C++`.
- Cierra y abre otra terminal despues de instalar las tools.
- Prueba el script `.\setup.ps1`, que intenta reinstalar `llama-cpp-python` usando `vcvars64.bat`.

### La app no descarga el modelo

- Revisa que `HF_TOKEN` exista en `.env`.
- Confirma que aceptaste el acceso al modelo en Hugging Face si es gated.
- Verifica que `HF_MODEL_REPO` sea correcto.
- Si sigue fallando, descarga el `.gguf` manualmente y guardalo en `models/`, luego actualiza `LLAMA_CPP_MODEL`.

### Error de modelo no encontrado o ruta invalida

- Comprueba que el archivo indicado en `LLAMA_CPP_MODEL` exista realmente.
- Usa rutas relativas desde la raiz del proyecto, por ejemplo `models/gemma-3-4b-it-q4_0.gguf`.
- Si cambiaste de modelo, revisa que el nombre del archivo en `.env` coincida con el descargado.

### El microfono no funciona

- Confirma que Windows tenga permiso para usar el microfono.
- Cierra apps que puedan estar reteniendo el dispositivo de audio.
- Verifica que `sounddevice` se haya instalado bien con `.\verify_env.ps1`.
- Prueba primero los modos por texto para aislar si el problema es solo de captura.

### La ventana abre pero alguna voz o skill no responde

- Revisa la consola desde la que lanzaste `python .\main.py`; ahi suelen verse los errores reales.
- Ejecuta `python -m unittest` para confirmar que el entorno base sigue sano.
- Si falta un modelo o dependencia opcional, algunas rutas tienen fallback, pero la experiencia completa requiere STT, TTS y LLM funcionando.

### PowerShell bloquea la activacion del entorno

- Ejecuta PowerShell como usuario normal y prueba:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

- Luego activa otra vez con `.\.venv\Scripts\Activate.ps1`.

## Flujo de Comunicacion

1. El usuario escribe o graba audio desde la interfaz PyQt.
2. Si hay audio, `MicrophoneRecorder` genera un WAV temporal.
3. `transcription_skill` usa Faster Whisper para convertir audio a texto.
4. `Orion`, el supervisor, recibe el texto y decide el modo o respeta el modo seleccionado.
5. El agente especializado ejecuta su skill: correccion, spelling, TTS o transcripcion.
6. `MemoryManager` registra la interaccion, puntaje, errores, nivel y siguiente foco.
7. `UserStore` persiste el historial en SQLite.
8. La UI actualiza el personaje ukagaka, el globo, el dashboard y opcionalmente pronuncia la respuesta.

## Modos de Practica

- `Grammar`: el usuario escribe o dice una frase; Nova revisa ortografia/gramatica, pronuncia la frase, propone correccion y sugiere una forma mas natural.
- `Talk`: Alden muestra una frase; el usuario la pronuncia; la app compara el intento y permite reintentar o pedir una nueva frase. Para iniciar se escribe `start` o se usa `Ctrl+N`.
- `Listen`: Pulse muestra y pronuncia un parrafo, hace una pregunta y evalua que tan acertada fue la respuesta del usuario. Para iniciar se escribe `start` o se usa `Ctrl+N`.
- `Spell`: Glyph pide una lista de palabras o propone una; el usuario deletrea por voz y la app valida letra por letra. Para iniciar una palabra sugerida se escribe `start` o se usa `Ctrl+N`.

## Personajes

- `Orion`: supervisor y coordinador general.
- `Nova`: gramatica y refinamiento de expresion.
- `Alden`: conversacion guiada y practica de `Talk`.
- `Pulse`: escucha y transcripcion.
- `Glyph`: deletreo.
- `Echo`: voz y reproduccion TTS.
- `Vera`: evaluacion.
- `Atlas`: seguimiento de aprendizaje y siguiente micro-meta.

## Memoria y Reportes

La app esta pensada para un solo usuario local. El nombre se define en `.env` con `APP_USER_NAME`.

El historial se guarda en `runtime/data/app.sqlite3`. Tambien se guarda un resumen al cerrar la aplicacion para que Orion recuerde donde ibas, que debilidades se han visto y que conviene practicar luego.

Desde el menu de la app se puede abrir:

- `Dashboard`: estadisticas visuales, barras de progreso y curva de evolucion.
- `Report`: exporta un PDF en `runtime/reports`.
- `Theme`: cambia tema visual.
- `Compact` / `Classic`: cambia densidad de la interfaz.
- `Pin`: mantiene la ventana por encima de otras.
- `Close`: cierra guardando resumen.

Atajos:

- `Ctrl+Q`: cerrar aplicacion.
- `Ctrl+N`: equivalente a escribir `start` en modos que necesitan iniciar dinamica.
- `Esc`: cancelar grabacion activa.

## Capacidades Que Tal Vez No Has Visto

- Descarga automatica del modelo GGUF si `AUTO_DOWNLOAD_MODEL=true`.
- Fallbacks cuando falta un modelo o una dependencia opcional.
- Temas editables desde archivos en `themes`.
- Cambio entre modo compacto y clasico.
- Paginacion dentro del globo de dialogo.
- Reporte PDF local.
- Memoria de palabras usadas en `Spell`.
- Dificultad adaptativa entre niveles como `A2`, `B1`, `B2` y `C1`.
- Herramientas para crear skills y adapters con `dev.py`.
- Uso de manifests para cambiar personajes por agente y expresion.

## Desarrollo

Crear un skill:

```powershell
python .\dev.py create-skill my_skill --description "New skill" --mode grammar
```

Crear un adapter:

```powershell
python .\dev.py create-adapter my_adapter --port-kind custom
```

El loader carga automaticamente las carpetas dentro de `skills` que tengan un `module.py` con funcion `build()`.

## Convertir A EXE En Windows

El proyecto incluye un metodo para generar un `.exe` de Windows con PyInstaller.

Preparacion:

```powershell
.\setup.ps1
.\.venv\Scripts\Activate.ps1
```

Generar el ejecutable:

```powershell
.\build_exe.ps1
```

Salida esperada:

- El ejecutable se genera en `dist/WhisperUkagaka/WhisperUkagaka.exe`.
- El script tambien crea `models/`, `runtime/` y una copia inicial de `.env` dentro de `dist/WhisperUkagaka/`.
- Los recursos necesarios para la UI y los skills se empaquetan junto al exe: `assets`, `prompts`, `themes` y `skills`.

Uso del exe:

1. Abre `dist/WhisperUkagaka/.env`.
2. Ajusta `HF_TOKEN`, `LLAMA_CPP_MODEL`, `HF_MODEL_REPO` o el tema si hace falta.
3. Si no quieres descarga automatica, copia tu archivo `.gguf` a `dist/WhisperUkagaka/models/`.
4. Ejecuta `dist/WhisperUkagaka/WhisperUkagaka.exe`.

Notas:

- El metodo actual usa `--onedir`, no `--onefile`. Es mas practico aqui porque la app necesita varios recursos externos y carpetas de trabajo.
- Los datos del usuario creados por el exe se guardan dentro de `dist/WhisperUkagaka/runtime/`.
- Si el antivirus o Windows SmartScreen muestra advertencias, es normal en ejecutables sin firma digital.

Si necesitas reconstruir desde cero:

```powershell
Remove-Item -Recurse -Force .\build, .\dist
.\build_exe.ps1
```

## Que Sigue

- Mejorar la evaluacion real de pronunciacion con comparacion fonetica o forced alignment.
- Hacer que los ejercicios de `Talk`, `Listen` y `Spell` generen contenido mas variado segun el historial.
- Agregar lip sync o animaciones simples al hablar.
- Permitir seleccionar microfono desde la UI.
- Agregar calendario o plan semanal de practica.
- Mejorar el dashboard con mas metricas por modo y por tipo de error.
- Empaquetar la app como ejecutable de Windows.
- Separar claramente datos temporales, cache de modelos y backups de usuario.
