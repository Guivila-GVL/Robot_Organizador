import os
import sys
import unittest
from datetime import datetime

# Añadir raíz del proyecto al path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.database import get_db_connection
from app.services.telegram_service import (
    notify_task_started,
    notify_task_intermediate_stage,
    STAGE_CONFIG,
    send_telegram_message
)
from app.services.execution_queue import (
    normalize_stage,
    update_task_progress
)


class TestTelegramMilestones(unittest.TestCase):

    def test_01_stage_config_definitions(self):
        """Verifica que las configuraciones de los 3 hitos intermedios requeridos existan."""
        self.assertIn("plan", STAGE_CONFIG)
        self.assertIn("development", STAGE_CONFIG)
        self.assertIn("validation", STAGE_CONFIG)

        # Hito 1: Pensado cómo implementarlo
        self.assertIn("pensado en cómo implementarlo", STAGE_CONFIG["plan"]["title"].lower())
        # Hito 2: Comienza desarrollo
        self.assertIn("comienza el desarrollo", STAGE_CONFIG["development"]["title"].lower())
        # Hito 3: Fin desarrollo y comienza validación
        self.assertIn("comienza la validación", STAGE_CONFIG["validation"]["title"].lower())

    def test_02_normalize_stage_detection(self):
        """Verifica que el reconocedor de fases mapee correctamente texto y porcentajes."""
        # Explícitos
        self.assertEqual(normalize_stage("plan"), "plan")
        self.assertEqual(normalize_stage("development"), "development")
        self.assertEqual(normalize_stage("validation"), "validation")
        self.assertEqual(normalize_stage("started"), "started")

        # Texto de paso: Hito 1 (pensado/estrategia)
        self.assertEqual(
            normalize_stage("Ya se ha pensado en cómo implementarlo: arquitectura diseñada"),
            "plan"
        )
        self.assertEqual(
            normalize_stage("Estrategia definida para el flujo"),
            "plan"
        )

        # Texto de paso: Hito 2 (comienza desarrollo)
        self.assertEqual(
            normalize_stage("Comienza el desarrollo e integración de código"),
            "development"
        )

        # Texto de paso: Hito 3 (fin desarrollo, comienza validación)
        self.assertEqual(
            normalize_stage("Ha acabado el desarrollo y ahora comienza la validación técnica"),
            "validation"
        )
        self.assertEqual(
            normalize_stage("Comienza la validación con pruebas automatizadas"),
            "validation"
        )

        # Fallback por porcentaje
        self.assertEqual(normalize_stage("", pct=25), "plan")
        self.assertEqual(normalize_stage("", pct=50), "development")
        self.assertEqual(normalize_stage("", pct=80), "validation")

    def test_03_notify_task_started_live(self):
        """Prueba de envío real o formato de mensaje de inicio de tarea."""
        res = notify_task_started(
            project_name="Robot de Gestión de Proyectos",
            task_title="Test de Notificación de Arranque de Tarea",
            task_id=9999,
            model_name="Gemini 3.8 Flash (Test Suite)",
            started_at=datetime.now().strftime("%H:%M:%S (%d/%m/%Y)")
        )
        self.assertTrue(res.get("success"), f"Fallo al notificar arranque: {res}")

    def test_04_notify_intermediate_milestones_live(self):
        """Prueba el envío de los 3 hitos intermedios a Telegram."""
        # 1. Hito Plan
        res_plan = notify_task_intermediate_stage(
            project_name="Robot de Gestión de Proyectos",
            task_title="Test Seguimiento de Hitos",
            stage="plan",
            stage_description="Ya se ha pensado en cómo implementarlo: módulos telegram_service y execution_queue conectados.",
            task_id=9999,
            progress_pct=25
        )
        self.assertTrue(res_plan.get("success"), f"Fallo en hito plan: {res_plan}")

        # 2. Hito Development
        res_dev = notify_task_intermediate_stage(
            project_name="Robot de Gestión de Proyectos",
            task_title="Test Seguimiento de Hitos",
            stage="development",
            stage_description="Comienza el desarrollo: creación de métodos y ajuste de handlers de progreso.",
            task_id=9999,
            progress_pct=50
        )
        self.assertTrue(res_dev.get("success"), f"Fallo en hito dev: {res_dev}")

        # 3. Hito Validation
        res_val = notify_task_intermediate_stage(
            project_name="Robot de Gestión de Proyectos",
            task_title="Test Seguimiento de Hitos",
            stage="validation",
            stage_description="Ha acabado el desarrollo y ahora comienza la validación con suite de tests.",
            task_id=9999,
            progress_pct=80
        )
        self.assertTrue(res_val.get("success"), f"Fallo en hito val: {res_val}")

    def test_05_update_task_progress_deduplication(self):
        """Verifica que update_task_progress evite duplicar notificaciones para el mismo hito."""
        conn = get_db_connection()
        c = conn.cursor()
        # Crear tarea temporal para test
        c.execute("""
            INSERT INTO tasks (project_id, title, status, progress_pct, created_at, notified_stages)
            VALUES ('gestion_proyectos', 'Tarea Temporal Test Deduplicacion', 'in_progress', 10, datetime('now'), '')
        """)
        temp_id = c.lastrowid
        conn.commit()
        conn.close()

        try:
            # 1. Primer avance al 25% (Hito 'plan') -> debe notificar
            r1 = update_task_progress(
                task_id=temp_id,
                progress_pct=25,
                current_step="Ya se ha pensado en cómo implementarlo: planificación lista",
                stage="plan"
            )
            self.assertTrue(r1["success"])
            self.assertEqual(r1["stage"], "plan")
            self.assertTrue(r1.get("telegram_notified"))

            # 2. Segundo avance al 30% aún en fase plan -> NO debe duplicar telegram
            r2 = update_task_progress(
                task_id=temp_id,
                progress_pct=30,
                current_step="Ajustando pequeños detalles del plan",
                stage="plan"
            )
            self.assertTrue(r2["success"])
            self.assertFalse(r2.get("telegram_notified"))

            # 3. Tercer avance al 50% (Hito 'development') -> debe notificar
            r3 = update_task_progress(
                task_id=temp_id,
                progress_pct=50,
                current_step="Comienza el desarrollo de la funcionalidad",
                stage="development"
            )
            self.assertTrue(r3["success"])
            self.assertEqual(r3["stage"], "development")
            self.assertTrue(r3.get("telegram_notified"))

            # Verificar que notified_stages contiene ambos
            conn = get_db_connection()
            row = conn.execute("SELECT notified_stages FROM tasks WHERE id = ?", (temp_id,)).fetchone()
            conn.close()
            stages = row["notified_stages"].split(",")
            self.assertIn("plan", stages)
            self.assertIn("development", stages)

        finally:
            # Limpiar tarea temporal
            conn = get_db_connection()
            conn.execute("DELETE FROM tasks WHERE id = ?", (temp_id,))
            conn.execute("DELETE FROM comments WHERE task_id = ?", (temp_id,))
            conn.commit()
            conn.close()

    def test_06_notify_telegram_false_does_not_suppress_stage(self):
        """Verifica que si notify_telegram=False se usa (arranque runner), no marque como notificado el hito plan."""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO tasks (project_id, title, status, progress_pct, created_at, notified_stages)
            VALUES ('gestion_proyectos', 'Tarea Temporal Test No Suppress', 'in_progress', 10, datetime('now'), '')
        """)
        temp_id = c.lastrowid
        conn.commit()
        conn.close()

        try:
            # 1. Simular arranque del runner con notify_telegram=False
            r1 = update_task_progress(
                task_id=temp_id,
                progress_pct=10,
                current_step="⚡ Ejecutando con motor de prueba...",
                note="Worker autónomo iniciado.",
                author="Cola Global",
                stage="started",
                notify_telegram=False
            )
            self.assertTrue(r1["success"])
            self.assertFalse(r1.get("telegram_notified"))

            conn = get_db_connection()
            row = conn.execute("SELECT notified_stages FROM tasks WHERE id = ?", (temp_id,)).fetchone()
            conn.close()
            notified_raw = row["notified_stages"] or ""
            self.assertNotIn("plan", notified_raw.split(","))

            # 2. Cuando el agente reporta Hito 1 (plan), debe notificar a Telegram exitosamente
            r2 = update_task_progress(
                task_id=temp_id,
                progress_pct=20,
                current_step="Ya se ha pensado en cómo implementarlo: arquitectura diseñada",
                stage="plan"
            )
            self.assertTrue(r2["success"])
            self.assertEqual(r2["stage"], "plan")
            self.assertTrue(r2.get("telegram_notified"))

            # 3. Y ahora sí debe estar en notified_stages
            conn = get_db_connection()
            row2 = conn.execute("SELECT notified_stages FROM tasks WHERE id = ?", (temp_id,)).fetchone()
            conn.close()
            self.assertIn("plan", (row2["notified_stages"] or "").split(","))

        finally:
            conn = get_db_connection()
            conn.execute("DELETE FROM tasks WHERE id = ?", (temp_id,))
            conn.execute("DELETE FROM comments WHERE task_id = ?", (temp_id,))
            conn.commit()
            conn.close()


if __name__ == "__main__":
    unittest.main()
