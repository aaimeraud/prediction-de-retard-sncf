# 🚀 SNCF Delay Prediction - Lancement du Projet

## Environnement Requis
- Python 3.9+ (3.11/3.12 recommandé pour TensorFlow)
- Virtual environment configuré
- Dépendances installées via `requirements.txt`

## Option 1: Lancer avec Jupyter Notebook
```bash
.venv/bin/jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser
```
Puis ouvrez http://localhost:8888 dans votre navigateur.

## Option 2: Lancer avec Streamlit Dashboard
```bash
.venv/bin/streamlit run src/streamlit_dashboard.py
```
L'interface web s'ouvrira à http://localhost:8501

## Option 3: Lancer avec FastAPI (Production)
```bash
.venv/bin/uvicorn src.api_server:app --reload --host 0.0.0.0 --port 5000
```
Accédez à http://localhost:5000/docs pour la documentation Swagger.

## Option 4: Lancer avec Docker
```bash
docker build -t sncf-ml .
docker run -p 8888:8888 -p 5000:5000 -p 8501:8501 \
  -e PYTHONUNBUFFERED=1 \
  sncf-ml
```

## Option 5: Tester sur Google Colab (RECOMMANDÉ)
Le projet est conçu pour être exécuté sur Colab où TensorFlow/Keras fonctionne mieux.

```python
# Installer les dépendances
!pip install -q -r requirements.txt

# Charger le projet
import os
os.chdir('/content/path/to/repo')

# Importer et utiliser
import sys
sys.path.insert(0, 'src')
from model_training import ModelTrainingPipeline
from data_loader import GTFSDataLoader

loader = GTFSDataLoader()
pipeline = ModelTrainingPipeline()
# ...
```

## Exécuter les Tests
```bash
.venv/bin/python -m pytest tests/ -v
```

## Utiliser le Script d'Entraînement Minimal
```bash
.venv/bin/python train_model.py
```
Génère un modèle pré-entraîné pour Streamlit: `models/delay_classifier.keras`

## Fichiers Clés du Projet

### Architecture
```
src/
  ├── data_loader.py          # Chargement données GTFS/SIRI
  ├── data_validator.py       # Validation qualité données
  ├── feature_engineer.py     # Ingénierie des features
  ├── model_classifier.py     # Classificateur TensorFlow
  ├── model_training.py       # Pipeline d'entraînement
  ├── model_registry.py       # Registre des modèles
  ├── model_versioning.py     # Gestion des versions
  ├── ab_testing.py           # Tests A/B
  ├── api_server.py           # Serveur FastAPI
  └── streamlit_dashboard.py  # Dashboard Streamlit
```

### Tests
```
tests/ (220+ tests)
  ├── test_data_loader.py
  ├── test_feature_engineer.py
  ├── test_model_classifier.py
  ├── test_model_training.py
  ├── test_api_server.py
  ├── test_streamlit_dashboard.py
  └── test_integration.py
```

## Documentation
- `CONTEXT.md` - État complet du projet
- `PROGRESSION.md` - Phases et statut
- `GUIDELINES.md` - Standards de code
- `README.md` - Description générale

## Problèmes Connus

### TensorFlow sur macOS ARM64
TensorFlow 2.13+ peut avoir des problèmes de compilation sur macOS avec processeur ARM64.
**Solution:** Utiliser Docker ou Google Colab.

### SSL/LibreSSL Warning
```
urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL'
```
Cet avertissement n'affecte pas le fonctionnement. Ignorez-le.

## Support Colab

Le projet fonctionne mieux sur Google Colab. Pour utiliser:

1. Créez un notebook Colab
2. Clonez le repo: `!git clone https://github.com/aaimeraud/prediction-de-retard-sncf.git`
3. Installez les dépendances: `!pip install -q -r requirements.txt`
4. Importez et utilisez comme documenté dans les tests

## Prochaines Étapes
1. Charger les données GTFS réelles
2. Entraîner le modèle sur données complètes
3. Déployer via API ou Dashboard
4. Monitorer performances
5. Implémenter A/B tests
