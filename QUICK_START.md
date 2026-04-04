À démarrer le projet, vous avez plusieurs options:

1. **🎯 Launcher Interactif (Recommandé)**
   ```bash
   cd /path/to/project
   ./start.sh
   ```
   Cela vous donnera un menu pour choisir:
   - Jupyter Notebook (développement)
   - Streamlit Dashboard (interface web)
   - FastAPI API (production)
   - Tests pytest
   - Modèle minimal

2. **📊 Lancer Streamlit Directement**
   ```bash
   .venv/bin/streamlit run src/streamlit_dashboard.py
   ```
   Accédez à http://localhost:8501

3. **📓 Lancer Jupyter Notebook**
   ```bash
   .venv/bin/jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser
   ```
   Accédez à http://localhost:8888

4. **🐳 Via Docker (Recommandé pour TensorFlow)**
   ```bash
   docker build -t sncf-ml .
   docker run -p 8888:8888 -p 5000:5000 -p 8501:8501 sncf-ml
   ```

5. **☁️ Google Colab (Meilleure compatibilité TensorFlow)**
   Clonez le repo et exécutez depuis Colab

## État du Projet

✅ **Phase 8 - Terminé**
- 219 tests Phases 1-7 (toutes validées)
- 49 tests Phase 8 (explainability, monitoring, optimization)
- 13 modules Python
- Documentation complète
- CI/CD retiré (projet académique)

## Structure

```
src/
├── data_loader.py (GTFS/SIRI)
├── feature_engineer.py
├── model_classifier.py (TensorFlow)
├── model_training.py (Pipeline)
├── model_registry.py
├── model_versioning.py
├── ab_testing.py
├── api_server.py (FastAPI)
└── streamlit_dashboard.py

tests/ (220+ tests)
docs/ (Documentation)
```

## Points Importants

⚠️ **TensorFlow sur macOS ARM64**: Peut être lent. Docker/Colab recommandés.
✅ **Tous les imports**: Fonctionnent correctement
✅ **Code validé**: Pas de syntaxe, erreurs corrigées
✅ **Prêt à l'emploi**: Lancez et testez immédiatement
