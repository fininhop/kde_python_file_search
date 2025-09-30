# KDE Python File Search

Application de recherche de fichiers pour **Debian KDE Plasma** en Python avec interface PyQt5.  

---

## Fonctionnalités

- Recherche un mot-clé dans les **noms de fichiers et dossiers** (partiel ou complet, insensible à la casse).  
- Recherche sur **tout le système** (selon permissions) ou sur **disques externes montés**.  
- Indicateur de chargement pendant la recherche.  
- Affichage des résultats directement sous le champ de recherche.  
- Menu contextuel pour chaque résultat :  
  - Copier le chemin  
  - Ouvrir le dossier parent dans un terminal (konsole si disponible)  
  - Ouvrir le fichier avec l'application par défaut  

---

## Dépendances

- Python 3
- PyQt5


## Pre-Installation

1. Installer les dépendances :
sudo apt install python3 python3-pyqt5

## Installation

Pour installer Debian KDE Booster sur votre système Debian/KDE, suivez ces étapes :

### 1. Copier le fichier exécutable

Placez le fichier `kde_python_file_search.py` dans `/usr/local/bin/` :

sudo cp kde_python_file_search.py /usr/local/bin/

### 2. Copier le fichier desktop

cp kde_python_file_search.desktop ~/.local/share/applications/

### 3. Copier l’icône

cp kde_python_file_search.png ~/.local/share/icons/

### 4. Donner les permissions d’exécution

sudo chmod +x /usr/local/bin/kde_python_file_search.py

### 5. Lancer l’application
Vous pouvez maintenant lancer l’application depuis le menu KDE ou directement via le terminal :

Si depuis le terminal utiliser: 

sudo python3 kde_python_file_search.py

Sinon si vous avez fais les étapes de 1 à 4 vous pouvez trouver l'application depuis le le menu KDE.

