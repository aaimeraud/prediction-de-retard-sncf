#!/opt/local/bin/python3.9
"""
Interactive launcher for SNCF Delay Prediction ML Project
Permet de choisir comment lancer le projet
"""

import os
import sys
import subprocess
from pathlib import Path


def print_banner():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║       🚂 SNCF DELAY PREDICTION - ML PROJECT LAUNCHER 🚂       ║
    ║                     Phase 8 - Complete                        ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)


def get_venv_python():
    """Retourne le chemin vers l'exécutable Python du venv"""
    venv_path = Path(__file__).parent / ".venv" / "bin" / "python"
    if venv_path.exists():
        return str(venv_path)
    return "python"


def main():
    print_banner()
    
    os.chdir(Path(__file__).parent)
    python_exe = get_venv_python()
    
    print("🎯 Mode de lancement disponibles:\n")
    print("  1️⃣  Jupyter Notebook (Développement/Exploration)")
    print("  2️⃣  Streamlit Dashboard (Interface Web)")
    print("  3️⃣  FastAPI Server (API Production)")
    print("  4️⃣  Exécuter les Tests (220+ tests)")
    print("  5️⃣  Entraîner Modèle Minimal (pour Streamlit)")
    print("  6️⃣  Documentation & Aide")
    print("  0️⃣  Quitter\n")
    
    choice = input("Sélectionnez une option (0-6): ").strip()
    
    print()
    
    commands = {
        "1": (f"{python_exe} -m jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser",
              "Jupyter démarré sur http://localhost:8888"),
        
        "2": (f"{python_exe} -m streamlit run src/streamlit_dashboard.py",
              "Streamlit démarré sur http://localhost:8501"),
        
        "3": (f"{python_exe} -m uvicorn src.api_server:app --reload --host 0.0.0.0 --port 5000",
              "FastAPI démarré sur http://localhost:5000/docs"),
        
        "4": (f"{python_exe} -m pytest tests/ -v",
              "Tests exécutés..."),
        
        "5": (f"{python_exe} train_model.py",
              "Entraînement du modèle minimal..."),
        
        "6": ("cat LAUNCHER.md | less",
              "Affichage de la documentation..."),
    }
    
    if choice == "0":
        print("👋 Au revoir!")
        return 0
    
    if choice not in commands:
        print("❌ Choix invalide. Veuillez relancer.")
        return 1
    
    cmd, msg = commands[choice]
    print(f"🚀 {msg}")
    print(f"   Commande: {cmd}\n")
    print("─" * 60)
    
    try:
        os.system(cmd)
    except KeyboardInterrupt:
        print("\n\n⏹️  Arrêt par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
