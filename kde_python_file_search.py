#!/usr/bin/env python3
"""
kde_python_file_search.py

Application de recherche de fichiers pour Debian KDE Plasma.
Fonctionnalités:
- Cherche un mot-clé dans les noms de fichiers et dossiers (partiel ou entier, insensible à la casse)
- Recherche sur tout le système (selon permissions) ou sur points de montage externes montés
- Indicateur de chargement pendant la recherche
- Résultats affichés sous le champ de recherche
- Copier le chemin, ouvrir le dossier parent dans un terminal (konsole si disponible)

Dépendances: python3, PyQt5
Installation (Debian): sudo apt install python3 python3-pyqt5

Note de sécurité: Ce programme ne modifiera pas automatiquement les permissions (chmod).
Si vous avez besoin d'accéder à des répertoires protégés, lancez l'application avec des privilèges root (pkexec/sudo).
"""

import os
import sys
import fnmatch
import stat
import subprocess
from threading import Event

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices


def find_mounts_external():
    """Retourne une liste de points de montage qui semblent être des disques externes/USB.
    On lit /proc/mounts et on filtre les devices qui commencent par /dev/sd ou /dev/mmcblk ou mtdblock
    (heuristique simple).
    """
    mounts = []
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    dev, mnt = parts[0], parts[1]
                    if dev.startswith('/dev/sd') or dev.startswith('/dev/mmcblk') or dev.startswith('/dev/nvme'):
                        mounts.append(mnt)
    except Exception:
        pass
    return sorted(set(mounts))


class SearchWorker(QtCore.QThread):
    found = pyqtSignal(str)
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, roots, keyword, stop_event: Event):
        super().__init__()
        self.roots = roots
        self.keyword = keyword.lower()
        self._stop_event = stop_event

    def run(self):
        total = 0
        for root in self.roots:
            for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
                if self._stop_event.is_set():
                    self.finished.emit()
                    return
                name = os.path.basename(dirpath).lower()
                if self.keyword in name:
                    self.found.emit(dirpath)
                for fname in filenames:
                    if self._stop_event.is_set():
                        self.finished.emit()
                        return
                    if self.keyword in fname.lower():
                        full = os.path.join(dirpath, fname)
                        self.found.emit(full)
                total += 1
                if total % 500 == 0:
                    self.progress.emit(total)
        self.finished.emit()


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Recherche de fichiers - KDE (Python)')
        self.setMinimumSize(800, 500)
        self.setWindowIcon(QIcon('/home/cattac/.local/share/icons/kde_python_file_search.svg'))
        self._stop_event = Event()
        self.worker = None

        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        top_row = QtWidgets.QHBoxLayout()

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText('Tape un mot-clé (nom partiel ou complet)')
        self.search_input.returnPressed.connect(self.start_search)
        top_row.addWidget(self.search_input)

        self.search_button = QtWidgets.QPushButton('Recherche')
        self.search_button.clicked.connect(self.start_search)
        top_row.addWidget(self.search_button)

        self.stop_button = QtWidgets.QPushButton('Arrêter')
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_search)
        top_row.addWidget(self.stop_button)

        layout.addLayout(top_row)

        opts = QtWidgets.QHBoxLayout()

        self.include_external_cb = QtWidgets.QCheckBox("Inclure disques externes montés")
        opts.addWidget(self.include_external_cb)

        self.select_folders_btn = QtWidgets.QPushButton('Ajouter un dossier')
        self.select_folders_btn.clicked.connect(self.add_custom_folder)
        opts.addWidget(self.select_folders_btn)

        self.clear_roots_btn = QtWidgets.QPushButton('Réinitialiser racines')
        self.clear_roots_btn.clicked.connect(self.clear_custom_roots)
        opts.addWidget(self.clear_roots_btn)

        self.roots_label = QtWidgets.QLabel('Racines: / (par défaut)')
        self.roots_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        opts.addWidget(self.roots_label, stretch=1)

        layout.addLayout(opts)

        self.loader = QtWidgets.QProgressBar()
        self.loader.setTextVisible(False)
        self.loader.setVisible(False)
        layout.addWidget(self.loader)

        self.result_list = QtWidgets.QListWidget()
        self.result_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.result_list.itemDoubleClicked.connect(self.open_item)
        self.result_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.result_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.result_list)

        status_row = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel('Prêt')
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        self.custom_roots = []

    def add_custom_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, 'Choisir un dossier')
        if d:
            self.custom_roots.append(d)
            self._update_roots_label()

    def clear_custom_roots(self):
        self.custom_roots = []
        self._update_roots_label()

    def _update_roots_label(self):
        if not self.custom_roots:
            self.roots_label.setText('Racines: / (par défaut)')
        else:
            self.roots_label.setText('Racines: ' + ', '.join(self.custom_roots))

    def start_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            self.status_label.setText('Entrer un mot-clé')
            return

        roots = []
        if self.custom_roots:
            roots.extend(self.custom_roots)
        else:
            roots.append('/')

        if self.include_external_cb.isChecked():
            mounts = find_mounts_external()
            for m in mounts:
                if m not in roots:
                    roots.append(m)

        self.result_list.clear()
        self._stop_event.clear()
        self.worker = SearchWorker(roots, keyword, self._stop_event)
        self.worker.found.connect(self.on_found)
        self.worker.finished.connect(self.on_finished)
        self.worker.progress.connect(self.on_progress)
        self.loader.setRange(0, 0)
        self.loader.setVisible(True)
        self.search_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText('Recherche en cours...')
        self.worker.start()

    def stop_search(self):
        if self.worker and self.worker.isRunning():
            self._stop_event.set()
            self.status_label.setText('Arrêt en cours...')

    def on_found(self, path):
        item = QtWidgets.QListWidgetItem(path)
        self.result_list.addItem(item)

    def on_progress(self, n):
        self.status_label.setText(f'Parcouru ~{n} dossiers...')

    def on_finished(self):
        self.loader.setVisible(False)
        self.search_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText(f'Fini. {self.result_list.count()} résultats')

    def show_context_menu(self, pos):
        item = self.result_list.itemAt(pos)
        if not item:
            return
        path = item.text()
        menu = QtWidgets.QMenu()
        copy_act = menu.addAction('Copier le chemin')
        open_parent_act = menu.addAction('Ouvrir terminal dans le dossier parent')
        open_here_act = menu.addAction('Ouvrir terminal ici')
        open_file_act = menu.addAction('Ouvrir avec l\'application par défaut')
        act = menu.exec_(self.result_list.mapToGlobal(pos))
        if act == copy_act:
            QtWidgets.QApplication.clipboard().setText(path)
        elif act == open_parent_act:
            d = os.path.dirname(path)
            if not d:
                d = path
            self.open_terminal_at(d)
        elif act == open_here_act:
            if os.path.isdir(path):
                self.open_terminal_at(path)
            else:
                self.open_terminal_at(os.path.dirname(path))
        elif act == open_file_act:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def open_item(self, item):
        path = item.text()
        if os.path.isdir(path):
            self.open_terminal_at(path)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def open_terminal_at(self, folder):
        candidates = ['konsole', 'x-terminal-emulator', 'xfce4-terminal', 'gnome-terminal', 'urxvt', 'xterm']
        cmd = None
        for c in candidates:
            if shutil_which(c):
                cmd = c
                break
        if not cmd:
            QtWidgets.QMessageBox.warning(self, 'Aucun terminal', "Aucun terminal compatible trouvé (konsole, xterm, ...).")
            return
        try:
            if cmd == 'konsole':
                subprocess.Popen([cmd, '--workdir', folder])
            elif cmd == 'x-terminal-emulator' or cmd == 'gnome-terminal':
                subprocess.Popen([cmd, '--', 'bash', '-c', f'cd "{folder}"; exec bash'])
            else:
                subprocess.Popen([cmd, '-e', f'bash -lc "cd \"{folder}\"; exec bash"'])
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Erreur', f'Impossible d\'ouvrir le terminal: {e}')


def shutil_which(prog):
    try:
        import shutil
        return shutil.which(prog)
    except Exception:
        for path in os.environ.get('PATH', '').split(':'):
            p = os.path.join(path, prog)
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p
        return None


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
