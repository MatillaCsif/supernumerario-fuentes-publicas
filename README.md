# Monitor remoto de fuentes públicas de Supernumerario

Repositorio público autorizado por su titular. Monitor programado dos veces al día; el estado efectivo y las incidencias de cada ejecución constan en `data/status.json`.

- Solo consulta fuentes oficiales públicas de JCyL: comisiones, archivo BOCYL y estadísticas.
- Conserva versiones por SHA-256 y fecha de captura. Las nuevas capturas BOCYL verifican el PDF durante la consulta y guardan el texto UTF-8, la huella histórica y el enlace oficial; no guardan el binario. Las fuentes de comisiones, estadísticas y demás documentos mantienen su archivo original. No lee Gmail ni archivos privados.
- Se ejecuta dos veces al día en un runner estándar gratuito de GitHub. El workflow se niega a ejecutarse en repositorios privados. No utiliza artefactos, cachés facturables, LFS, servicios de IA ni claves de servicios externos.
- Límite de conservación: 256 MB entre originales comprimidos y textos BOCYL. Si se alcanza, registra el fallo y detiene la captura; no activa almacenamiento de pago.
- El BOCYL recupera las ediciones desde su cursor. Los errores y ediciones extraordinarias no comprobadas retienen el avance.
- Las capturas remotas no equivalen a validar sus efectos jurídicos. El Atlas local contrasta los originales antes de atribuir hechos a plazas.

La ejecución remota permite capturar mientras el ordenador está apagado. La programación gratuita de GitHub puede sufrir retrasos; el registro de continuidad permite recuperar ediciones permanentes del BOCYL.

El Atlas local importa las capturas dentro de su ciclo A0 y comprueba la identidad del documento, la huella histórica del PDF y la huella del texto antes de mostrarlo. El enlace oficial permite consultar el original; el registro de texto no afirma que la copia binaria histórica siga almacenada. Una captura remota no acredita ocupación actual ni el efecto jurídico de una resolución. Un enlace histórico que devuelve 404 se señala como aviso si su original ya está conservado; si falta el original, sigue siendo un error.
