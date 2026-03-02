# Reglas de Ingeniería de Software
- Estilo: Clean Code y principios SOLID.
- Stack: Python 3.12+, FastAPI, SQLAlchemy.
- Base de Datos: PostgreSQL (usar Docker Compose).
- Testing: Mínimo 80% de cobertura con PyTest.
- Git: Haz un commit por cada funcionalidad terminada con mensajes en formato Conventional Commits.

Protocolo de Entrega Automática:

Al finalizar una tarea, ejecuta pytest y verifica que la cobertura sea > 90%.

Si los tests pasan, ejecuta: git push origin <rama-actual>.

Crea el Pull Request automáticamente: gh pr create --title "feat: <descripcion>" --body "Implementado por IA - Listo para revisión"
