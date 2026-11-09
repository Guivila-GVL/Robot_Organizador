# Protocolo de Revisión General al Acabar una Tarea — Robot de Gestión de Proyectos

Este checklist define la revisión técnica obligatoria que debe ejecutarse al concluir cualquier tarea:

### 📋 Checklist de los 5 Pasos Obligatorios:

1. **📁 Documentación en /docs actualizada:**
   - Verificar que los cambios y decisiones queden documentados en la carpeta `docs/`.
   - Añadir o actualizar la entrada en `docs/REGISTRO_HITOS.md` con el resultado y fecha.

2. **📓 OneNote / Bitácora actualizada:**
   - Comprobar que la sección del proyecto en *Desarrollo Proyectos* refleje el avance reciente.
   - Hoja `01. Resumen`: porcentaje recalculado y fecha actualizada.
   - Hoja `02. Listado de Actividades`: tarea marcada como completada con su resultado.

3. **🐙 Git actualizado y subido a GitHub:**
   - Comprobar que no queden ficheros temporales ni secretos sin proteger en `.gitignore`.
   - Crear un commit descriptivo: `feat(hito): <tarea> [protocolo-completado]`.
   - Ejecutar `git push origin main` al repositorio de GitHub.

4. **🧠 Skills y forma de trabajo revisadas:**
   - Consultar las directrices de `0000_Utilidades/01_Skills` (`03_Gestion_Proyecto`, `02_OneNote_Management`, etc.).
   - Verificar que la arquitectura y limpieza del código sean consistentes con el estándar.

5. **📱 Check y envío a Telegram:**
   - Último paso de confirmación: enviar el check de esta revisión general con su imagen/captura al canal de Telegram (@Bot2_Video_bot).

---
*Automatización: En el Robot de Gestión de Proyectos, esta secuencia se ejecuta automáticamente al completar cualquier tarea.*
