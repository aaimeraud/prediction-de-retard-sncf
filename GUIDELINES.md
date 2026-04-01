# Directives du Projet (Guidelines)

## 1. Documentation & Commentaires

- **Strictement aucun commentaire inline (`#`) local dans le code.**
- Toute explication de code doit utiliser **exclusivement des Docstrings Python** `""" explication """`.
- Cette règle est appliquée pour assurer la cohérence et la propreté du code lu par les Agents ML et QA.

## 2. Déploiement Git et Worktrees

- Ne travaillez jamais sur la branche principale pour le developpement.
- Utilisez systématiquement la méthode **Git Worktrees** au sein du répertoire racine :
  - **Dossier de destination :** `./worktrees/`
- **Conventions de nommage des branches :**
  - Feature : `feat/<nom>`
  - Hotfix : `hotfix/<nom>`
  - Documentation : `docs/<nom>`
  - Infrastructure : `infra/<nom>`
  - Refactoring : `refactor/<nom>`
  - Maintenance : `chore/<nom>`
- **Commande type :** `git worktree add ./worktrees/<nom-branche> <nom-branche>`
- Cela permet un isolement robuste des environnements et de l'implémentation.

## 3. Python & Dépendances

- Utilisez **exclusivement** `python3` et `pip3` pour toutes les commandes.
- Les dépendances sont gérées via `requirements.txt` dans le worktree.
- Lors du déploiement : `pip3 install -r requirements.txt` ou `pip3 install --upgrade -r requirements.txt`.

## 4. Qualité et Tests (QA)

- Tous les modules ML developpés et les API associées doivent etre testés unitairement (via Pytest) en simulant un environnement comme Colab.
- Le dossier `tests/` recueille tous les tests.

## 5. Contexte MCP & Agents

- Conserver le contexte du projet actualisé dans le fichier `CONTEXT.md`.
- Le suivi des tâches doit toujours être maintenu dans `PROGRESSION.md` (Fait | En cours | To-do).
- L'agent TF-ENGINEER intègre toujours le MCP SDK et gère les incertitudes par "Zero-Hallucination policy" en stop/question.
