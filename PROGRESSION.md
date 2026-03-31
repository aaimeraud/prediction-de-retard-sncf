# Progression du Projet ML: Retards SNCF

## Fait (Fini)
- [X] Scaffolding de l'arborescence du projet (src, tests, docker, etc.).
- [X] Rédaction des guidelines (Zero-Inline comments, worktrees).
- [X] Création du Dockerfile compatible TF + Colab et requirements de base.

## En cours
- [ ] Transition vers l'Agent 2 (TF-Engineer) pour l'implémentation ML initiale et le setup complet du MVP.

## To-do
- [ ] Setup Worktree pour la fonctionnalité de téléchargement / parsing GTFS-RT (via un script sandoxé).
- [ ] Conception du pipeline de features (Gare origine, destination, retards < 5min).
- [ ] Creation d'un notebook expérimental d'EDA sur l'historique temps-réel (dans `notebooks/`).
- [ ] Initialisation MCP par TF-Engineer.
- [ ] Validation QA Agent sur la suppression de `#` dans les scripts créés.
