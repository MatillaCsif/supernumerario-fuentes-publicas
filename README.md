# Monitor remoto de fuentes públicas de Supernumerario

Repositorio público autorizado por su titular. Monitor programado dos veces al día; el estado efectivo y las incidencias de cada ejecución constan en `data/status.json`.

- Solo consulta fuentes oficiales públicas de JCyL: comisiones, archivo BOCYL y estadísticas.
- Conserva copias comprimidas por SHA-256 y versiones con fecha de captura; pueden incluir información ya publicada en documentos oficiales. No lee Gmail ni archivos privados.
- Se ejecuta dos veces al día en un runner estándar gratuito de GitHub. El workflow se niega a ejecutarse en repositorios privados. No utiliza artefactos, cachés facturables, LFS, servicios de IA ni claves de servicios externos.
- Límite de conservación: 256 MB comprimidos. Si se alcanza, registra el fallo y detiene la captura; no activa almacenamiento de pago.
- El BOCYL recupera las ediciones desde su cursor. Los errores y ediciones extraordinarias no comprobadas retienen el avance.
- Las capturas remotas no equivalen a validar sus efectos jurídicos. El Atlas local contrasta los originales antes de atribuir hechos a plazas.

La ejecución remota permite capturar mientras el ordenador está apagado. La programación gratuita de GitHub puede sufrir retrasos; el registro de continuidad permite recuperar ediciones permanentes del BOCYL.

El Atlas local importa las capturas dentro de su ciclo A0 y vuelve a comprobar las identidades y las huellas antes de mostrarlas. Una captura remota no acredita ocupación actual ni el efecto jurídico de una resolución. Un enlace histórico que devuelve 404 se señala como aviso si su original ya está conservado; si falta el original, sigue siendo un error.
