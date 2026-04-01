# Directives du Projet (Guidelines)

## 1. Documentation & Commentaires

- **Strictement aucun commentaire inline (`#`) local dans le code.**
- Toute explication de code doit utiliser **exclusivement des Docstrings Python** `""" explication """`.
- Cette règle est appliquée pour assurer la cohérence et la propreté du code lu par les Agents ML et QA.

## 2. Déploiement Git et Worktrees

### 2.1 Conventions de Nommage
- **Feature :** `feat/<nom>`
- **Hotfix :** `hotfix/<nom>`
- **Documentation :** `docs/<nom>`
- **Infrastructure :** `infra/<nom>`
- **Refactoring :** `refactor/<nom>`
- **Maintenance :** `chore/<nom>`

### 2.2 Workflow Explicite : Branche → Worktree
**Toujours créer la branche AVANT le worktree (protocole strict) :**

```bash
cd /path/to/repository.git

git branch feat/my-feature develop
git worktree add ./worktrees/feat-my-feature feat/my-feature
cd ./worktrees/feat-my-feature
```

**Pourquoi deux étapes ?**
- Branche explicite : visible dans `git branch -a`
- Worktree isolé : développement independant, pas de conflicts
- Traçabilité : historique Git conserve les branches créées

### 2.3 Isolation et Environnement
- Ne travaillez **jamais** sur `develop` ou `main` directement
- Chaque feature = 1 branche + 1 worktree = 1 environnement isolé
- **Dossier de destination worktrees :** `./worktrees/`
- Cela permet un isolement robuste des environnements et de l'implémentation.

### 2.4 Merge et Cleanup
Après merge vers `develop` :

```bash
cd /path/to/repository.git
git worktree remove ./worktrees/feat-my-feature
```

La branche persiste (pour historique git), le worktree est supprimé (nettoyage).

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
