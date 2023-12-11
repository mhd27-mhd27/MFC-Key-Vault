import os
import sys
import emoji
import re
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QTableWidgetItem, QAbstractItemView,QInputDialog,QCheckBox
)
from PyQt6.QtCore import Qt,QTimer
from PyQt6 import  QtGui
from PyQt6.QtGui import QIcon
from cryptography.fernet import Fernet
from PyQt6.QtGui import QClipboard, QKeySequence,QShortcut

def generate_key():
    return Fernet.generate_key()

def encrypt_password(key, password):
    cipher_suite = Fernet(key)
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(key, encrypted_password):
    cipher_suite = Fernet(key)
    return cipher_suite.decrypt(encrypted_password.encode()).decode()


class StyledButton(QPushButton):
    def __init__(self, text, color, hover_color, parent=None):
        """
        Constructeur de la classe StyledButton.

        Args:
            text (str): Texte affiché sur le bouton.
            color (str): Couleur du bouton en état normal.
            hover_color (str): Couleur du bouton lorsqu'il est survolé.
            parent (QWidget): Widget parent du bouton (par défaut None).
        """
        super().__init__(text, parent)

        # Couleur du bouton en état normal.
        self.color = color

        # Couleur du bouton lorsqu'il est survolé.
        self.hover_color = hover_color

        # Applique le style défini dans la méthode set_style.
        self.set_style()

    def set_style(self):
        """
        Définit le style du bouton en utilisant les couleurs spécifiées.
        """
        style = (
            f"QPushButton {{"
            f"background-color: {self.color};"
            f"border: 1px solid #222222;"
            f"border-radius: 5px;"
            f"padding: 5px 10px;"  # Ajoutez cette ligne pour définir la taille des boutons
            f"}}"
            f"QPushButton:hover {{"
            f"background-color: {self.hover_color};"
            f"border: 1px solid #555555;"
            f"}}"
        )

        # Applique la feuille de style au bouton.
        self.setStyleSheet(style)

class PasswordItemButton(StyledButton):
    def __init__(self, icon_name, text, color, hover_color, click_handler, parent=None):
        super().__init__(text, color, hover_color, parent)
        icon = QIcon.fromTheme(icon_name)
        self.setIcon(icon)
        self.clicked.connect(click_handler)

# Widget personnalisé pour les mots de passe dans le tableau
class PasswordItem(QTableWidgetItem):
    def __init__(self, text):
        """
        Constructeur de la classe PasswordItem.

        Args:
            text (str): Texte initial de l'élément.
        """
        super().__init__()

        # Définit les drapeaux pour rendre l'élément sélectionnable et activé.
        self.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

        # Définit le texte de l'élément.
        self.setText(text)

        # Stocke le texte initial dans original_text pour référence future.
        self.original_text = text

    def clone(self):
        """
        Crée et renvoie un clone de l'objet PasswordItem.

        Returns:
            PasswordItem: Clone de l'objet PasswordItem.
        """
        return PasswordItem(self.text())

    def setData(self, role, value):
        """
        Définit les données associées à un rôle spécifique.

        Args:
            role (int): Rôle pour lequel les données sont définies.
            value: Valeur des données.

        Notes:
            Cette méthode est appelée lors de la modification des données de l'élément.
        """
        if role == Qt.ItemDataRole.EditRole:
            # Si le rôle est EditRole, définissez le texte de l'élément et mettez à jour original_text.
            self.setText(value)
            self.original_text = value
        else:
            # Sinon, appelez la méthode setData de la classe parente.
            super().setData(role, value)

    def display_password(self):
        """
        Masque le texte de l'élément en affichant une série d'astérisques.

        Notes:
            Cette méthode est utilisée pour masquer le mot de passe réel lors de son affichage.
        """
        self.setText("*******************")

class PasswordVaultApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Chemin de l'emplacement de la base de données
        self.db_path = os.path.join(os.path.expanduser("~"), ".ManagePassword", "database.db")
        self.save_version('2.1.3')
        

        # Vérifier si le répertoire "ManagePassword" existe, sinon le créer
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Vérifier si la base de données existe, sinon la créer
        if not os.path.exists(self.db_path):
            self.create_database()

        # Générer ou charger la clé de chiffrement
        #self.load_or_generate_key()

        self.initUI()
         # Create a shortcut for the Enter key to trigger the "Déverouiller" button click
        self.enter_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        self.enter_shortcut.activated.connect(self.unlock)

        self.lock_shortcut= QShortcut(QKeySequence(Qt.Key.Key_Alt + Qt.Key.Key_F2), self)
        self.lock_shortcut.activated.connect(self.lock_interface)

         # Ajouter un minuteur pour le verrouillage automatique après 2 minutes d'inactivité
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.timeout.connect(self.lock_interface)
        self.reset_inactivity_timer()

        
        
    

    # ... (autres méthodes)

    '''   def apply_dark_style(self):
        # Appliquer un style sombre aux widgets de l'interface
        # Vous devrez ajuster cela en fonction de votre interface réelle
        dark_style = "background-color: #2c3e50; color: white;"  # Utilisation d'une nuance de bleu foncé
        self.centralWidget().setStyleSheet(dark_style)
        self.table.setStyleSheet(dark_style)
        self.statusBar().setStyleSheet(dark_style)

    def remove_dark_style(self):
        # Retirer le style sombre des widgets de l'interface
        self.centralWidget().setStyleSheet("")
        self.table.setStyleSheet("")
        self.statusBar().setStyleSheet("")'''
    
    def save_version(self, version):
        version_file_path = os.path.join(os.path.expanduser("~"), ".ManagePassword", "version.txt")
        with open(version_file_path, 'w') as version_file:
            version_file.write(version)
    
    def read_version(self):
        version_file_path = os.path.join(os.path.expanduser("~"), ".ManagePassword", "version.txt")
        try:
            with open(version_file_path, 'r') as version_file:
                return version_file.read().strip()
        except FileNotFoundError:
            return 'Version not available'
        
    def save_readme(readme_content, readme_path):
        """
        Sauvegarde le contenu du README dans le fichier spécifié s'il n'existe pas.

        Parameters:
            readme_content (str): Le contenu du README.
            readme_path (str): Le chemin où le README doit être sauvegardé.
        """
        # Vérifiez si le fichier README existe déjà
        if not os.path.exists(readme_path):
            # Créez le répertoire s'il n'existe pas
            os.makedirs(os.path.dirname(readme_path), exist_ok=True)

            # Écrivez le contenu du README dans le fichier
            with open(readme_path, 'w', encoding='utf-8') as readme_file:
                readme_file.write(readme_content)
            print(f'Le fichier README a été sauvegardé à {readme_path}')
        else:
            print(f'Le fichier README existe déjà à {readme_path}')

    readme_content = """
# MFC ~ Key Vault

## Description
MFC ~ Key Vault est une application simple de gestion des mots de passe construite avec Python et PyQt. Elle permet aux utilisateurs de stocker et gérer leurs mots de passe de manière sécurisée.

## Fonctionnalités
- Stocker et gérer les mots de passe de façons sécurisé avec une encryption base64
- Copier les mots de passe dans le presse-papiers
- Modifier et supprimer les mots de passe
- Interface simple et conviviale



## Propriétaire
- **Nom :** Mouhameth Fall Carvalho
- **Email :** mouhamethfall112@gmail.com
- **GitHub :** [mhd27-mhd27](https://github.com/mhd27-mhd27)

## Version
- Version actuelle : 2.1.3

## Licence
Ce projet est sous licence [MIT](LICENSE).

## Comment contribuer
1. Fork du dépôt
2. Créez une nouvelle branche : `git checkout -b feature/votre-fonctionnalite`
3. Effectuez vos modifications : `git commit -m 'Ajouter votre fonctionnalité'`
4. Poussez la branche : `git push origin feature/votre-fonctionnalite`
5. Soumettez une pull request


N'hésitez pas à personnaliser ce modèle pour qu'il corresponde aux spécificités de votre projet et à fournir plus de détails au besoin.
"""

    readme_path = os.path.join(os.path.expanduser("~"), ".ManagePassword", "README.md")

    save_readme(readme_content, readme_path)


    def create_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Création de la table 'comptes' avec des colonnes pour le site, le nom d'utilisateur et le mot de passe chiffré
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comptes (
                site TEXT,
                nom_utilisateur TEXT,
                mot_de_passe TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def load_or_generate_key(self):
        folder_name = ".ManagePassword"
        key_dir = os.path.join(os.path.expanduser("~"), folder_name)
        key_path = os.path.join(key_dir, "key.key")

        # Create the directory if it doesn't exist
        os.makedirs(key_dir, exist_ok=True)

        try:
            # Charger la clé de chiffrement s'il existe
            with open(key_path, 'rb') as key_file:
                self.key = key_file.read()
        except FileNotFoundError:
            # Générer une nouvelle clé de chiffrement et la sauvegarder
            self.key = generate_key()
            with open(key_path, 'wb') as key_file:
                key_file.write(self.key)

            #self.show_key_message_box()  # Show the message box with the key

    def initUI(self):
        self.setWindowTitle('MFC ~ Key Vault')
        self.setGeometry(100, 100, 1100, 600)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("key.ico"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.setWindowIcon(icon)
        self.center_on_screen()
        light_style = "background-color: #f2f2f0; color: black;"# 2c3e50
        self.setStyleSheet(light_style)
        

        self.key_label = QLabel('Entrez la clé de chiffrement:')
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setClearButtonEnabled(True)

        self.version_label = QLabel(f'Version {self.read_version()}')
        self.statusBar().addPermanentWidget(self.version_label)
        
        #self.unlock_button = QPushButton(emoji.emojize("Unlock :unlocked:"))
        #self.unlock_button.clicked.connect(self.unlock)

        self.unlock_button = StyledButton(emoji.emojize("Unlock :unlocked:"), "#3498db", "#2980b9", self)
        self.unlock_button.clicked.connect(self.unlock)

        self.search_label = QLabel('Recherche:')
        self.search_input = QLineEdit()
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.filter_table)

        key_layout = QHBoxLayout()
        key_layout.addWidget(self.key_label)
        key_layout.addWidget(self.key_input)
        key_layout.addWidget(self.unlock_button)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Site", "Nom d'utilisateur", "Mot de passe", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header_style = """
                QHeaderView::section {
                    background-color: #333;
                    color: white;
                    padding: 6px;
                    font-weight: bold;
                    border: none;
                }
            """
        self.table.horizontalHeader().setStyleSheet(header_style)
        #self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.add_site_label = QLabel('Site:')
        self.add_site_input = QLineEdit()
        self.add_site_input.setClearButtonEnabled(True)

        self.add_username_label = QLabel('Nom d\'utilisateur:')
        self.add_username_input = QLineEdit()
        self.add_username_input.setClearButtonEnabled(True)

        self.add_password_label = QLabel('Mot de passe:')
        self.add_password_input = QLineEdit()
        self.add_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_password_input.setClearButtonEnabled(True)

        '''self.add_button = QPushButton(emoji.emojize("Ajouter :plus:"))
        self.add_button.setDisabled(True)
        self.add_button.clicked.connect(self.add_account)

        self.show_button = QPushButton(emoji.emojize('Afficher :bookmark_tabs:'))
        self.show_button.setDisabled(True)
        self.show_button.clicked.connect(self.show_table)'''

        self.add_button = StyledButton(emoji.emojize("Ajouter :plus:"), "#27ae60", "#218c54", self)
        self.add_button.setDisabled(True)
        self.add_button.clicked.connect(self.add_account)

        self.show_button = StyledButton(emoji.emojize('Afficher :bookmark_tabs:'), "#e74c3c", "#c0392b", self)
        self.show_button.setDisabled(True)
        self.show_button.clicked.connect(self.show_table)
        
        #self.generate_password_button = QPushButton(emoji.emojize("Générer :key:"))
        self.generate_password_button = StyledButton(emoji.emojize("Générer :key:"), "#e77c3c", "#c0392b", self)
        self.generate_password_button.clicked.connect(self.generate_password)

        # Ajouter une case à cocher pour inclure des ponctuations
        #self.include_punctuations_checkbox = QCheckBox('Punctuation', self)
        #self.include_punctuations_checkbox.setChecked(True)  # Par défaut, inclure les ponctuations
        #self.include_punctuations_checkbox.stateChanged.connect(self.generate_password)
         # Ajouter un interrupteur (checkbox) pour basculer entre les modes sombre et clair
        #self.dark_mode_checkbox = QCheckBox('Mode sombre', self)
        self.dark_mode_checkbox = QCheckBox('Mode sombre', self)
        self.dark_mode_checkbox.stateChanged.connect(self.toggle_dark_mode)

        # Initialisez la variable de suivi de l'état du mode sombre
        self.dark_mode_enabled = False

        # 

        add_layout = QHBoxLayout()
        add_layout.addWidget(self.add_site_label)
        add_layout.addWidget(self.add_site_input)
        add_layout.addWidget(self.add_username_label)
        add_layout.addWidget(self.add_username_input)
        add_layout.addWidget(self.add_password_label)
        add_layout.addWidget(self.add_password_input)
        # Ajouter la case à cocher à la mise en page
        #add_layout.addWidget(self.include_punctuations_checkbox)

        add_layout.addWidget(self.generate_password_button)
        add_layout.addWidget(self.add_button)
        add_layout.addWidget(self.show_button)
        
    

        layout = QVBoxLayout()
        layout.addLayout(key_layout)
        layout.addWidget(self.search_label)
        layout.addWidget(self.search_input)
        layout.addWidget(self.dark_mode_checkbox)

        layout.addWidget(self.table)
        layout.addLayout(add_layout)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        

        self.conn = None
        self.cursor = None
        self.show()
        # Check if the key has been generated before
        if not os.path.exists(os.path.join(os.path.expanduser("~"), ".ManagePassword", "key_generated")):
            # Key not generated before, show the message box and generate the key
            self.show_key_message_box()
            with open(os.path.join(os.path.expanduser("~"), ".ManagePassword", "key_generated"), "w") as file:
                file.write("generated")
                
    def toggle_dark_mode(self, state):
       
        # Fonction appelée lors du changement d'état de la case (cochée ou non)
        #self.dark_mode_enabled = state == Qt.CheckState.Checked
        self.dark_mode_enabled = not self.dark_mode_enabled
        if self.dark_mode_enabled:
             self.apply_dark_style()
        else:
            self.remove_dark_style()
            

    def apply_dark_style(self):
        # Appliquer un style sombre aux widgets de l'interface
        # Vous devrez ajuster cela en fonction de votre interface réelle
        dark_style = "background-color: #2c3e50; color: white;"
        self.centralWidget().setStyleSheet(dark_style)
        self.table.setStyleSheet(dark_style)
        self.statusBar().setStyleSheet(dark_style)

    def remove_dark_style(self):
        # Retirer le style sombre des widgets de l'interface
        light_style = "background-color: #f2f2f0; color: black;"
        self.centralWidget().setStyleSheet(light_style)
        self.table.setStyleSheet(light_style)
        self.statusBar().setStyleSheet(light_style)

    def filter_table(self):
        search_text = self.search_input.text().lower()
        for row in range(self.table.rowCount()):
            site_item = self.table.item(row, 0)
            username_item = self.table.item(row, 1)

            site = site_item.text().lower()
            username = username_item.text().lower()

            if search_text in site or search_text in username:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)

    def center_on_screen(self):
        qr=self.frameGeometry()           
        cp=QtGui.QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def generate_password(self):
        # Utilisez QInputDialog pour obtenir des informations sur la génération de mot de passe
        length, ok = QInputDialog.getInt(self, 'Longueur du mot de passe', 'Longueur:', 13, 8, 256)
        if not ok:
            return

        # Générez un mot de passe fort (vous pouvez personnaliser cela selon vos critères)
        generated_password = self.generate_strong_password(length)

        # Affichez le mot de passe généré dans le champ de mot de passe
        self.add_password_input.setText(generated_password)

    def generate_strong_password(self, length):
        # Votre logique de génération de mot de passe fort ici (par exemple, utilisez des lettres majuscules, minuscules, chiffres et caractères spéciaux)
        # Assurez-vous d'ajuster cela selon vos critères de force de mot de passe
        # Ceci est un exemple simple, vous pouvez utiliser des bibliothèques Python telles que "secrets" pour cela
        import random
        import string

        characters = string.ascii_letters + string.digits + string.punctuation
        generated_password = ''.join(random.choice(characters) for _ in range(length))
        return generated_password
    
    """def generate_password(self):
        # Utilisez QInputDialog pour obtenir des informations sur la génération de mot de passe
        length, ok = QInputDialog.getInt(self, 'Longueur du mot de passe', 'Longueur:', 13, 8, 256)
        if not ok:
            return

        include_punctuations = self.include_punctuations_checkbox.isChecked()

        # Générez un mot de passe fort en fonction de la case à cocher
        generated_password = self.generate_strong_password(length, include_punctuations)

        # Affichez le mot de passe généré dans le champ de mot de passe
        self.add_password_input.setText(generated_password)

    def generate_strong_password(self, length, include_punctuations):
        # Votre logique de génération de mot de passe fort ici
        # Utilisez la variable include_punctuations pour décider d'inclure ou non les ponctuations
        import random
        import string

        characters = string.ascii_letters + string.digits

        if include_punctuations:
            characters += string.punctuation

        generated_password = ''.join(random.choice(characters) for _ in range(length))
        return generated_password"""

    '''def show_key_message_box(self):
        # Show a message box with the key and a custom "Copy" button
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Clé de chiffrement générée")
        msg_box.setText("La clé de chiffrement a été générée avec succès.\n"
                         "Conservez cette clé en lieu sûr pour accéder à vos mots de passe ultérieurement.\n"
                         "Il ne sera plus généré à nouveau.\n"
                         )

        # Create a custom "Copy" button and add it to the message box
        copy_button = QPushButton("Copier")
        msg_box.addButton(copy_button, QMessageBox.ButtonRole.ActionRole)
        msg_box.exec()

        # If the user clicks the "Copier" button, copy the key to the clipboard
        if msg_box.clickedButton() == copy_button:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.key.decode())
        folder_name = ".ManagePassword"
        key_dir = os.path.join(os.path.expanduser("~"), folder_name)
        key_path = os.path.join(key_dir, "key.key")
        os.remove(key_path)'''
    
    def show_key_message_box(self):
        # Show a message box with the key and additional instructions
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Clé de chiffrement générée")
        
        instructions_text = (
            "La clé de chiffrement a été générée avec succès.\n"
            "Conservez cette clé en lieu sûr pour accéder à vos mots de passe ultérieurement.\n"
            "Il ne sera plus généré à nouveau.\n"
            "\n"
            "Instructions supplémentaires :\n"
            "1. Copiez la clé dans un endroit sécurisé.\n"
            "2. Ne partagez jamais la clé avec d'autres personnes.\n"
            "3. En cas de perte de la clé, vous ne pourrez plus récupérer vos mots de passe."
        )

        msg_box.setText(instructions_text)

        # Create a custom "Copy" button and add it to the message box
        copy_button = QPushButton("Copier")
        msg_box.addButton(copy_button, QMessageBox.ButtonRole.ActionRole)
        msg_box.exec()

        # If the user clicks the "Copier" button, copy the key to the clipboard
        if msg_box.clickedButton() == copy_button:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.key.decode())

        # Remove the key file after it has been copied
        folder_name = ".ManagePassword"
        key_dir = os.path.join(os.path.expanduser("~"), folder_name)
        key_path = os.path.join(key_dir, "key.key")
        os.remove(key_path)

    def reset_inactivity_timer(self):
        # Réinitialiser le minuteur à chaque interaction de l'utilisateur
        self.inactivity_timer.stop()
        self.inactivity_timer.start(120000)  # 120000 millisecondes = 2 minutes

    def lock_interface(self):
        # Verrouiller l'interface après 2 minutes d'inactivité
        # Vous pouvez implémenter ici la logique de verrouillage de l'interface
        # Par exemple, masquer certaines fonctionnalités et afficher une boîte de dialogue de verrouillage
        # Assombrir l'interface
        self.apply_dark_style()
        self.key_label.setVisible(True)
        self.key_input.setVisible(True)
        self.unlock_button.setVisible(True)
        self.show_button.setEnabled(False)
        self.add_button.setEnabled(False)
        self.table.setDisabled(True)
        self.statusBar().showMessage('Interface verrouillée après 2 minutes d\'inactivité')

    # ... (autres fonctions)
    def closeEvent(self, event):
        # Arrêter le minuteur lorsque l'application se ferme
        self.inactivity_timer.stop()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        # Gérer l'événement de pression de touche pour réinitialiser le minuteur
        self.reset_inactivity_timer()
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        # Gérer l'événement de clic de souris pour réinitialiser le minuteur
        self.reset_inactivity_timer()
        super().mousePressEvent(event)

    def unlock(self):
        key_input = self.key_input.text().encode()
        try:
            # Vérifier si la clé de chiffrement est valide
            Fernet(key_input)

            # Connexion à la base de données SQLite avec la clé saisie
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()

            # Déverrouiller l'interface principale
            self.key = key_input
            self.key_input.clear()
            self.init_main_ui()
            self.remove_dark_style()
            self.show_button.setEnabled(True)
            self.add_button.setEnabled(True)
            self.show_table()
            self.table.setDisabled(False)
            self.reset_inactivity_timer()
            self.statusBar().showMessage('',2000)
        except Exception as e:
            QMessageBox.warning(self, 'Erreur', 'Clé de chiffrement incorrecte.')

    def init_main_ui(self):
        # Masquer les widgets liés à la saisie de la clé de chiffrement
        self.key_label.setVisible(False)
        self.key_input.setVisible(False)
        self.unlock_button.setVisible(False)

    def is_strong_password(self, password):
        # Define your criteria for a strong password
        # For example, we require a minimum length of 8 characters, at least one digit,
        # and at least one special character (e.g., !@#$%^&*()_-+=)
        if len(password) < 12 or not any(char.isdigit() for char in password) or not re.search(r'[!@#$%^&*()_-]+', password):
            return False
        return True

    def add_account(self):
        site = self.add_site_input.text()
        username = self.add_username_input.text()
        password = self.add_password_input.text()
        if not site or not username or not password:
            QMessageBox.warning(self, 'Champs vides', 'Veuillez remplir tous les champs.')
            return

        if not self.is_strong_password(password):
            QMessageBox.warning(self, 'Mot de passe faible', 'Le mot de passe doit contenir au moins 12 caractères et au moins un chiffre.')
            return

        encrypted_password = encrypt_password(self.key, password)

        self.cursor.execute('INSERT INTO comptes (site, nom_utilisateur, mot_de_passe) VALUES (?, ?, ?)', (site, username, encrypted_password))
        self.conn.commit()

        self.add_site_input.clear()
        self.add_username_input.clear()
        self.add_password_input.clear()

        # Mettre à jour la table avec le nouveau compte
        self.show_table()

    def show_table(self):
        if not self.conn:
            return

        self.table.clearContents()
        self.cursor.execute('SELECT site, nom_utilisateur, mot_de_passe FROM comptes')
        accounts = self.cursor.fetchall()

        if accounts:
            self.table.setRowCount(len(accounts))
            for row, account in enumerate(accounts):
                site, username, encrypted_password = account
                decrypted_password = decrypt_password(self.key, encrypted_password)

                site_item = QTableWidgetItem(site)
                username_item = QTableWidgetItem(username)
                password_item = PasswordItem(decrypted_password)  # Utilisation de notre widget personnalisé
                password_item.display_password()

                self.table.setItem(row, 0, site_item)
                self.table.setItem(row, 1, username_item)
                self.table.setItem(row, 2, password_item)


                copy_button = PasswordItemButton("edit-copy", emoji.emojize("Copy :scissors:"), "#3498db", "#2980b9",
                                 lambda: self.copy_password(decrypted_password))

                edit_button = PasswordItemButton("document-edit", emoji.emojize("Edit :crayon:"), "#2ecc71", "#27ae60",
                                 lambda: self.edit_password(row))

                delete_button = PasswordItemButton("edit-delete", emoji.emojize("Delete :cross_mark:"), "#e74c3c", "#c0392b",
                                   lambda: self.delete_password(row))

                button_layout = QHBoxLayout()
                button_layout.addWidget(copy_button)
                button_layout.addWidget(edit_button)
                button_layout.addWidget(delete_button)
                button_layout.setContentsMargins(5, 0, 5, 0)

                buttons_widget = QWidget()
                buttons_widget.setLayout(button_layout)

                self.table.setCellWidget(row, 3, buttons_widget)

        else:
            QMessageBox.information(self, 'Information', 'Aucun compte trouvé dans la base de données.')

    def copy_password(self, password):
        clipboard = QApplication.clipboard()
        clipboard.setText(password)
        self.statusBar().showMessage('Mot de passe copié', 2000)

    '''def edit_password(self, row):
        password_item = self.table.item(row, 2)
        new_password, ok = QInputDialog.getText(self, 'Modifier le mot de passe', 'Nouveau mot de passe:', QLineEdit.EchoMode.Password)
        if ok and new_password:
            encrypted_password = encrypt_password(self.key, new_password)
            password_item.setData(Qt.ItemDataRole.EditRole, new_password)
            site_item = self.table.item(row, 0)
            username_item = self.table.item(row, 1)
            site = site_item.text()
            username = username_item.text()
            self.cursor.execute('UPDATE comptes SET mot_de_passe=? WHERE site=? AND nom_utilisateur=?', (encrypted_password, site, username))
            self.conn.commit()
            self.statusBar().showMessage('Mot de passe modifié', 2000)'''
    
    def edit_password(self, row):
        site_item = self.table.item(row, 0)
        username_item = self.table.item(row, 1)
        password_item = self.table.item(row, 2)

        site = site_item.text()
        username = username_item.text()
        current_password = password_item.text()

        new_site, ok = QInputDialog.getText(self, 'Modifier le site', 'Nouveau site:', text=site)
        if not ok:
            return

        new_username, ok = QInputDialog.getText(self, 'Modifier le nom d\'utilisateur', 'Nouveau nom d\'utilisateur:', text=username)
        if not ok:
            return

        new_password, ok = QInputDialog.getText(self, 'Modifier le mot de passe', 'Nouveau mot de passe:', QLineEdit.EchoMode.Password)
        if not ok:
            return

        if not new_site or not new_username or not new_password:
            QMessageBox.warning(self, 'Erreur', 'Veuillez remplir tous les champs.')
            return

        if not self.is_strong_password(new_password):
            QMessageBox.warning(self, 'Erreur', 'Le mot de passe doit contenir au moins 12 caractères, au moins un chiffre et un caractère spécial.')
            return

        encrypted_password = encrypt_password(self.key, new_password)
        password_item.setData(Qt.ItemDataRole.EditRole, new_password)
        site_item.setData(Qt.ItemDataRole.EditRole, new_site)
        username_item.setData(Qt.ItemDataRole.EditRole, new_username)

        self.cursor.execute('UPDATE comptes SET site=?, nom_utilisateur=?, mot_de_passe=? WHERE site=? AND nom_utilisateur=?',
                            (new_site, new_username, encrypted_password, site, username))
        self.conn.commit()
        self.show_table()

        self.statusBar().showMessage('Mot de passe modifié', 2000)


    def delete_password(self, row):
    # Demander confirmation à l'utilisateur
        confirmation = QMessageBox.question(self, 'Confirmation', 'Voulez-vous vraiment supprimer ce mot de passe ?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirmation == QMessageBox.StandardButton.Yes:
            site_item = self.table.item(row, 0)
            username_item = self.table.item(row, 1)
            site = site_item.text()
            username = username_item.text()
            self.cursor.execute('DELETE FROM comptes WHERE site=? AND nom_utilisateur=?', (site, username))
            self.conn.commit()
            self.table.removeRow(row)
            self.statusBar().showMessage('Mot de passe supprimé', 2000)

    def closeEvent(self, event):
        if self.conn:
            # Fermeture de la connexion à la base de données lors de la fermeture de l'application
            self.conn.close()
            self.conn = None



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PasswordVaultApp()
    window.show()
    
    sys.exit(app.exec())
