# Directives du Projet (Guidelines)

## 1. Documentation & Commentaires
- **Strictement aucun commentaire inline (`#`) local dans le code.**
- Toute explication de code doit utiliser **exclusivement des Docstrings Python** `""" explication """`.
- Cette règle est appliquée pour assurer la cohérence et la propreté du code lu par les Agents ML et QA.

## 2. Déploiement Git et Worktrees
- Ne travaillez jamais sur la branche principale pour le developpement de features.
- Utilisez systématiquement la méthode **Git Worktrees**:
  ```bash
  git worktree add ../feature-<nom> -b feat/<nom>
  ```
- Cela permet un isolement robuste des environnements et de l'implémentation.

## 3. Qualité et Tests (QA)
- Tous les modules ML developpés et les API associées doivent etre testés unitairement (via Pytest) en simulant un environnement comme Colab.
- Le dossier `tests/` recueille tous les tests.

## 4. Contexte MCP & Agents
- Conserver le contexte du projet actualisé dans le fichier `CONTEXT.md`.
- Le suivi des tâches doit toujours être maintenu dans `PROGRESSION.md` (Fait | En cours | To-do).
- L'agent TF-ENGINEER intègre toujours le MCP SDK et gère les incertitudes par "Zero-Hallucination policy" en stop/question.
