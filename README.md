# Monitor remoto de fuentes públicas de Supernumerario

Preparado para un **repositorio público nuevo**, con autorización del titular. No está publicado ni activado.

- Solo consulta fuentes oficiales públicas de JCyL: comisiones, archivo BOCYL y estadísticas.
- Conserva copias comprimidas por SHA-256 y versiones con fecha de captura; pueden incluir información ya publicada en documentos oficiales. No lee Gmail ni archivos privados.
- Se ejecuta dos veces al día en un runner estándar gratuito de GitHub. El workflow se niega a ejecutarse en repositorios privados. No utiliza artefactos, cachés facturables, LFS, servicios de IA ni claves de servicios externos.
- Límite de conservación: 256 MB comprimidos. Si se alcanza, registra el fallo y detiene la captura; no activa almacenamiento de pago.
- El BOCYL recupera las ediciones desde su cursor. Los errores y ediciones extraordinarias no comprobadas retienen el avance.
- Las capturas remotas no equivalen a validar sus efectos jurídicos. El Atlas local contrasta los originales antes de atribuir hechos a plazas.

La ejecución remota permite capturar mientras el ordenador está apagado. La programación gratuita de GitHub puede sufrir retrasos; el registro de continuidad permite recuperar ediciones permanentes del BOCYL.

Para activar: crear el repositorio público dedicado y publicar únicamente estos archivos, nunca la carpeta del proyecto local. Antes debe estar acordado el repositorio de destino y habilitada la sincronización de sus capturas con el Atlas.
