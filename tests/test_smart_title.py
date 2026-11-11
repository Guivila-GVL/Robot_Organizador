import sys
import os

WORKSPACE_DIR = r"D:\OneDrive\04_Desarrollo_proyectos\2026_Proyecto_RobotOrganizador"
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from app.services.project_scanner import smart_breakdown_task, synthesize_smart_title

def test_suite():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS DE SÍNTESIS DE TÍTULOS")
    print("==================================================")

    test_cases = [
        {
            "id": "TASK_83_PROMPT",
            "prompt": (
                "Cuando das al botón de crear una nueva tarea con el botón de crear IA, me sigue sin poner un título adecuado. "
                "Por favor, revisa a ver cómo podemos hacer que al darle a crear con IA sí que lea el texto, pero de alguna forma "
                "hay que crear un pequeño título que no sea coger simplemente las primeras palabras."
            ),
            "expected_contains": ["Crear con IA", "título"],
            "max_len": 72
        },
        {
            "id": "TASK_82_PROMPT",
            "prompt": "Al parecer, cuando cambias de proyecto, la consola de la derecha va cambiando, y eso no tiene sentido, debería mantenerse fija.",
            "expected_contains": ["Mantener fija", "consola", "proyecto"],
            "max_len": 72
        },
        {
            "id": "TASK_81_PROMPT",
            "prompt": "En la parte de terminal, igual a la derecha, en la parte del robot, esto que pone «Terminal CMD logs», me gustaría que tuviera un botón para limpiar.",
            "expected_contains": ["botón para limpiar", "Terminal CMD logs"],
            "max_len": 72
        },
        {
            "id": "TASK_80_PROMPT",
            "prompt": "En la parte de arriba de Consola & Actividad hay unos botones que pone «Ejecutando», «Limpiar», «Auto-scroll». Simplificar y compactar la cabecera.",
            "expected_contains": ["cabecera", "Consola & Actividad"],
            "max_len": 72
        },
        {
            "id": "TASK_74_PROMPT",
            "prompt": "Sí, me gustaría hacer un cambio en la parte de la consola de actividad, en la parte de la derecha que los logs muestren timestamp.",
            "expected_contains": ["Mostrar timestamp", "logs"],
            "max_len": 72
        },
        {
            "id": "TASK_68_PROMPT",
            "prompt": (
                "Me gustaría mejorar un poco el botón de la creación de tareas. Cuando le demos al botón de «Crear con IA», "
                "una vez que hemos puesto el texto, por supuesto que tiene que rellenar todos los campos y hacer lo que está haciendo ahora, "
                "pero el título de la tarea debería hacer un análisis un poquito más exhaustivo y poner un título que sea corto y que sea muy "
                "resumido de lo que vamos a hacer, no dejar simplemente las primeras palabras. Me gustaría hacer esa pequeña modificación "
                "sobre el botón «Crear con IA», manteniendo todo igual, pero el resumen del título que lo mejore y lo centre mucho más "
                "con respecto al texto del prompt y de la descripción."
            ),
            "expected_contains": ["Crear con IA", "título"],
            "max_len": 72
        },
        {
            "id": "VOICE_DICTATION_EXPORT_EXCEL",
            "prompt": "Oye mira, me gustaría añadir un botón para exportar a Excel en la tabla de tareas, para que cuando lo pulsemos descargue un archivo xlsx directamente.",
            "expected_contains": ["Añadir un botón para exportar a Excel"],
            "max_len": 72
        },
        {
            "id": "BUG_PORT_HANG",
            "prompt": "Hay que arreglar el fallo en el puerto 8000 que cuando se cierra el navegador el proceso se queda colgado en segundo plano.",
            "expected_contains": ["Arreglar el fallo en el puerto 8000"],
            "max_len": 72
        },
        {
            "id": "CONJUGATED_VERB_FIRST_PERSON",
            "prompt": "Buenas tardes, corrijamos el problema del formulario donde el selector de prioridad no guarda el valor urgente.",
            "expected_contains": ["Corregir el problema del formulario"],
            "max_len": 72
        },
        {
            "id": "SHORT_DIRECT_TASK",
            "prompt": "Dockerizar el servicio de watchdog para evitar reinicios manuales.",
            "expected_contains": ["Dockerizar el servicio de watchdog"],
            "max_len": 72
        },
        {
            "id": "FASTAPI_ENDPOINT",
            "prompt": "Crear un nuevo endpoint en FastAPI para consultar el histórico de logs de actividad y filtrarlo por fecha.",
            "expected_contains": ["Crear un nuevo endpoint en FastAPI"],
            "max_len": 72
        },
        {
            "id": "VERIFY_TAIL_CUT",
            "prompt": "Crear exportador de resúmenes en PDF y comprobar que se guarde en /docs.",
            "expected_contains": ["Crear exportador de resúmenes en PDF"],
            "max_len": 72
        }
    ]

    all_passed = True
    for case in test_cases:
        prompt = case["prompt"]
        result = smart_breakdown_task(prompt)
        title = result["title"]
        desc = result["description"]
        milestone = result["milestone_description"]
        priority = result["priority"]

        print(f"\nCaso: [{case['id']}]")
        print(f"  Prompt original ({len(prompt)} caracteres)")
        print(f"  -> Título generado: '{title}' ({len(title)} caracteres)")
        print(f"  -> Prioridad: {priority}")
        print(f"  -> Hito: {result['milestone_type']} -> '{milestone}'")

        # Verificaciones
        assert len(title) <= case["max_len"], f"Longitud excede {case['max_len']}: {len(title)}"
        assert not title.endswith("..."), "El título no debe terminar en puntos suspensivos '...'"
        assert len(desc) == len(prompt), "La descripción completa original debe preservarse intacta"
        for exp in case["expected_contains"]:
            assert exp.lower() in title.lower(), f"Se esperaba '{exp}' en el título '{title}'"

        print("  ✅ VERIFICADO CORRECTAMENTE")

    print("\n==================================================")
    print("✅ TODAS LAS PRUEBAS HAN PASADO SATISFACTORIAMENTE")
    print("==================================================")
    return True

if __name__ == "__main__":
    test_suite()
