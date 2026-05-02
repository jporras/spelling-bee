# AGENTS.md

Este proyecto es una app de escritorio PyQt6 para practicar ingles con personajes visuales tipo ukagaka.

No es un RAG.
No agregar vector store, retrieval ni carpetas de RAG salvo que exista una razon tecnica ya presente en el codigo.

## Objetivo Del Proyecto

Whisper Ukagaka, tambien llamado `spelling-bee`, es un tutor local de ingles con:

- agentes visuales,
- modos de practica guiados,
- skills dinamicos,
- memoria local del usuario,
- y adaptadores de infraestructura para audio, STT, TTS, LLM y persistencia.

## Arquitectura Esperada

- `src/domain`
  Entidades, puertos e interfaces puras.
  No debe depender de PyQt, SQLite, Faster Whisper, llama.cpp ni pyttsx3.

- `src/application`
  Logica principal de la app.
  La implementacion real debe vivir en subpaquetes:
  `agents`, `modes`, `supervisor`, `memory`, `services`.

- `src/infrastructure`
  Adaptadores concretos:
  `audio`, `stt`, `tts`, `llm`, `persistence`, `config`, `skill_loader`.

- `src/ui/pyqt`
  UI real.
  La UI no debe contener logica pedagogica pesada.

- `skills`
  Plugins ejecutables cargados dinamicamente.
  Cada skill valido mantiene el contrato:
  `module.py` con funcion `build()`.

- `prompts/agents`
  Prompts de personalidad de:
  `orion`, `nova`, `alden`, `pulse`, `glyph`, `echo`, `vera`, `atlas`.

- `prompts/skills`
  Prompts pedagogicos por modo:
  `grammar`, `talk`, `listen`, `spell`.

- `assets`
  Recursos visuales de personajes y UI.

- `runtime`
  Datos generados.
  No es codigo fuente.

## Personajes

- `Orion`: supervisor general.
- `Nova`: gramatica y refinamiento de expresion.
- `Alden`: conversacion guiada y practica de `Talk`.
- `Pulse`: escucha y transcripcion.
- `Glyph`: deletreo.
- `Echo`: TTS y reproduccion.
- `Vera`: evaluacion.
- `Atlas`: seguimiento del aprendizaje y micro-metas.

## Modos De Practica

- `Grammar`
  El usuario escribe o dice una frase.
  Nova corrige ortografia, gramatica y naturalidad.
  Echo puede pronunciar la version correcta.
  Vera evalua.
  Atlas guarda errores y progreso.

- `Talk`
  Alden muestra una frase.
  El usuario la pronuncia.
  La app compara el intento con la frase objetivo.
  Debe permitir reintentar o pedir una frase nueva.
  Se inicia con `start` o `Ctrl+N`.

- `Listen`
  Pulse muestra y pronuncia un parrafo.
  Luego hace una pregunta.
  Vera evalua la respuesta.
  Se inicia con `start` o `Ctrl+N`.

- `Spell`
  Glyph pide una lista de palabras o propone una.
  El usuario deletrea por voz.
  La app valida letra por letra.
  Se inicia con `start` o `Ctrl+N`.

## Reglas De Mantenimiento

- Mantener compatibilidad con `main.py` y `run_ui.py`.
- Mantener el loader de skills dinamicos.
- No borrar `runtime/data` ni `models`.
- No meter prompts largos dentro de Python si deben vivir en archivos editables.
- Antes de borrar carpetas o mover archivos sensibles, buscar referencias con `rg`.
- Ejecutar `python -m unittest` despues de cambios estructurales.

## Limites De La UI

La UI solo debe:

- capturar texto o audio,
- enviar eventos al supervisor,
- mostrar respuesta,
- cambiar personaje o expresion,
- reproducir audio si corresponde.

La UI no debe decidir la pedagogia ni contener reglas profundas de evaluacion o memoria.

## Verificacion Minima

Antes de cerrar una refactorizacion importante:

1. Confirmar que `python main.py` siga iniciando la app.
2. Ejecutar `python -m unittest`.
3. Revisar que `README.md` refleje la arquitectura actual.
