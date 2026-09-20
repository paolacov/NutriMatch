"""Capa LLM OPCIONAL con tres roles: `planner` (traduce lenguaje natural a JSON validado),
`critic` (auditor determinista que verifica que cada afirmación esté respaldada por hechos
calculados) y `narrate` (redacta la explicación en markdown). Aquí vive también `tools.py`, un
registro DELGADO que expone al planner las operaciones deterministas implementadas en `engine/`:
esta capa nunca calcula. El sistema debe funcionar completo sin ella.
"""
