import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(os.path.dirname(BASE_DIR), "0000_Utilidades", "03_OneNote"))

import sync_desarrollo_proyectos as sync_module
from app.services.task_protocol import sync_onenote_project
import inspect

class TestOneNoteSyncNextSteps(unittest.TestCase):

    def setUp(self):
        self.mock_project = {
            "id": "test_proj",
            "name": "Proyecto de Prueba",
            "icon": "🚀",
            "category": "Automatización",
            "description": "Proyecto para testing unitario",
            "folder_path": r"D:\OneDrive\04_Desarrollo_proyectos\test_proj",
            "port": 9000,
            "url": "http://localhost:9000"
        }
        self.in_progress = [
            {"title": "Tarea Activa 1", "description": "Detalle activa", "status": "in_progress", "priority": "alta"}
        ]
        self.pending = [
            {"title": "Tarea Pendiente 1", "description": "Detalle pendiente", "status": "pending", "priority": "media"}
        ]

    def test_build_next_steps_html_structure(self):
        html = sync_module.build_next_steps_page_html(self.mock_project, self.in_progress, self.pending)
        
        # Debe contener título y encabezado
        self.assertIn("<title>03. Siguientes Pasos y Evolución</title>", html)
        self.assertIn("Siguientes Pasos y Evolución", html)
        
        # Debe incluir el backlog activo con las tareas pasadas
        self.assertIn("1. Siguientes Pasos a Realizar (Backlog Activo)", html)
        self.assertIn("Tarea Activa 1", html)
        self.assertIn("Tarea Pendiente 1", html)
        
        # Debe incluir los 3 horizontes con etiquetas interactivas de OneNote data-tag="to-do"
        self.assertIn("2. Hoja de Ruta de Evolución (Horizontes de Trabajo)", html)
        self.assertIn("Horizonte 1: Inmediato & Consolidación", html)
        self.assertIn("Horizonte 2: Nuevas Funciones & Automatización", html)
        self.assertIn("Horizonte 3: Escalabilidad & Visión Futura", html)
        self.assertIn('data-tag="to-do"', html)
        
        # Debe incluir el banco de ideas
        self.assertIn("3. Banco de Ideas, Hipótesis y Mejoras Futuras", html)
        
        # Debe incluir el espacio de reflexión personal
        self.assertIn("4. Notas de Trabajo y Reflexión de Guillermo", html)

    def test_build_next_steps_empty_tasks(self):
        html = sync_module.build_next_steps_page_html(self.mock_project, [], [])
        self.assertIn("Actualmente no hay tareas pendientes en la cola", html)
        self.assertIn("Horizonte 1", html)

    def test_sync_onenote_signature(self):
        sig = inspect.signature(sync_onenote_project)
        self.assertIn("force_next_steps", sig.parameters)
        self.assertEqual(sig.parameters["force_next_steps"].default, False)

if __name__ == "__main__":
    unittest.main()
