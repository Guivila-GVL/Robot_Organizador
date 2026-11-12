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
        },
        {
            "id": "TASK_140_PROMPT",
            "prompt": (
                "Cuando vamos a lanzar una tarea, me gustaría que el título fuera un resumen de la descripción que se ha puesto aquí, "
                "pero que no cogiera las primeras palabras. Eso es una cosa que hay que cambiar, además, para todos los proyectos.  "
                "Siempre que le dé al botón de crear con IA, que me crea el prompt para hacer toda la tarea y todo esto, el título "
                "debería analizarse y crearse a partir de un resumen de todo lo que he pedido que se haga."
            ),
            "expected_contains": ["Crear con IA", "título"],
            "max_len": 72
        },
        {
            "id": "TASK_106_PROMPT",
            "prompt": (
                "Me gustaría que me abrieras en OneNote un resumen de los paneles que tenemos y las gráficas que tenemos y el detalle "
                "de cada una de esas gráficas, que me lo listaras un poco para tener claro qué es lo que tenemos en Grafana.  Y luego "
                "también tenemos un gran trabajo hecho en Power BI. Me gustaría que hicieras lo mismo: tener un listado con una pequeña "
                "descripción y qué hay dentro de cada uno de los gráficos, tanto de Grafana como de Power BI."
            ),
            "expected_contains": ["OneNote", "paneles", "Grafana"],
            "max_len": 72
        },
        {
            "id": "TASK_105_PROMPT",
            "prompt": (
                "Me da la impresión de que aquí en el Watchdog que tenemos de Antigravity no se actualiza perfectamente el tema del "
                "modelo, del porcentaje que le queda y de cómo están los otros. Lo digo porque me ha llegado varias veces un mensaje "
                "de que se ha agotado el motor y cambiamos a otro, y sin embargo la página de aquí de seguimiento no refleja que ese "
                "motor ha disminuido o que ya prácticamente no queda."
            ),
            "expected_contains": ["Watchdog", "modelo", "porcentaje"],
            "max_len": 72
        },
        {
            "id": "TASK_104_PROMPT",
            "prompt": (
                "Quiero crear una tarea que sea: debería existir la opción de que, si se pide hacer una tarea que sea extremadamente "
                "grande, poder dividirla en subtareas y que sean las que realmente aparezcan aquí en el seguimiento.  Es decir, yo puedo "
                "hacer una frase aquí, crear aquí un esto, pero quizá al dar al botón «Crear con IA» me debería proponer de alguna forma "
                "dividirlo en subtareas y crear varias si es el caso de que es algo complejo. No sé cómo podríamos plantear eso, pero me "
                "interesaría pensarlo. No sé cómo lo podrías poner. Quizá hazme una hoja en OneNote con la estrategia de cómo podríamos "
                "hacerlo, porque por ahora no lo veo.  Entonces, aquí en Robot de Gestión de Proyectos ábreme una hoja en OneNote y "
                "proponme una estrategia de cómo dividirlo en subtareas cuando yo aquí pida una tarea que quiero hacer, y al comenzarla "
                "se analice si tiene sentido o no que se divida en varias tareas."
            ),
            "expected_contains": ["subtareas"],
            "max_len": 72
        },
        {
            "id": "TASK_93_PROMPT",
            "prompt": (
                "Me gustaría cambiar el nombre de esta aplicación, que se llama Robot de Gestión de Proyectos. Me gustaría ponerle algún "
                "tipo de nombre a este robot. No sé qué propuesta de nombres podemos hacer. Iron Man usa uno que se llama JARVIS. Otra "
                "idea, no sé, sería como ponerle un nombre de persona. Pues esta idea.  Al final, es simplemente cambiarle el nombre y el "
                "iconito de gestión de proyectos de un robot, pues sí, algo más profesional. No sé, ponerle algo. Va a ser una IA, pero "
                "me gustaría ponerle nombre. Me gustaría que me hicieras una propuesta o cambiar, pensar cómo es cuál y cambiar un poquito "
                "el icono a algo más, no de gestión. No sé, un pro, no sé qué imagen puedo poner de un robot."
            ),
            "expected_contains": ["Robot de Gestión de Proyectos", "nombre"],
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
