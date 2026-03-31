# Prédiction de retard ferroviaire en temps réel

## Description
Projet visant à anticiper les retards des trains à court terme en exploitant les données ouvertes de la SNCF (horaires GTFS statiques et flux temps réel GTFS-RT/SIRI) combinées à des modèles de machine learning modernes.

## Infrastructure

- **Docker Compose (Standard 2026) :** TensorFlow 2.x (Multi-arch) + Colab runtime.
- **Python :** 3.10+
- **Sécurité :** Utilisateur non-root (UID/GID mapping pour Mac Silicon).

## Docker Quickstart

Pour garantir la sécurité et la portabilité, utilisez l'environnement conteneurisé.

### Mac, Linux et WSL

```bash
# Exportation des identifiants (Auto-détection)
export UID=$(id -u)
export GID=$(id -g)

# Lancement
docker compose up -d --build
```

### Windows (PowerShell)

```powershell
# Définition des variables d'environnement
$env:UID = 1000
$env:GID = 1000

# Lancement
docker compose up -d --build
```

Services disponibles :
- **Jupyter Lab :** [http://localhost:8888](http://localhost:8888)
- **API FastAPI :** [http://localhost:5000](http://localhost:5000)
- **Dashboard Streamlit :** [http://localhost:8501](http://localhost:8501)

## Protocol Git (Worktrees)

Étant donné le clone du dépôt en mode `--bare`, l'utilisation de `git worktree` est **obligatoire** au sein du répertoire `./worktrees/` :

### Workflow type pour un nouveau développement :

1. Création du worktree (depuis le dossier racine du projet) :
   ```bash
   git worktree add ./worktrees/<nom-branche> <nom-branche>
   cd ./worktrees/<nom-branche>
   ```
2. Développement et tests Docker
3. Commit et Push
4. Nettoyage :
   ```bash
   git worktree remove ./worktrees/<nom-branche>
   ```

## Accès Colab
Ce projet est compatible avec Google Colab grâce à l'image Docker spécifiée et la configuration des notebooks. Lancez le container Docker pour avoir accès à Jupyter.

## Données
Les données peuvent être structurées dans le dossier `data/`.
Lien open data: https://data.sncf.com/explore/dataset/horaires-sncf/information/
Lien API: https://data.sncf.com/api/explore/v2.1/catalog/datasets/horaires-sncf/records?limit=20
