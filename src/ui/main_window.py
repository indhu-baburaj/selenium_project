from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QTextEdit, QPushButton, QLabel, 
                            QFileDialog, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from linkedin_bot import LinkedInBot  # Use absolute import



class WorkerThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, username, password, csv_path, note):
        super().__init__()
        self.username = username
        self.password = password
        self.csv_path = csv_path
        self.note = note
        self.bot = LinkedInBot()

    def run(self):
        try:
            # Initialize browser
            self.progress.emit("Setting up browser...")
            browser = self.bot.setup_browser()

            # Login
            self.progress.emit("Logging in to LinkedIn...")
            if not self.bot.login_to_linkedin(self.username, self.password):
                self.finished.emit(False, "Login failed")
                return

            # Pre-scan profiles
            self.progress.emit("Pre-scanning profiles...")
            self.bot.pre_scan_profiles(browser, self.csv_path, self.username)

            # Connect with remaining
            self.progress.emit("Connecting with profiles...")
            self.bot.connect_with_remaining(browser, self.csv_path, self.note, self.username)

            self.finished.emit(True, "Process completed successfully")
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")
        finally:
            if hasattr(self.bot, 'browser'):
                self.bot.browser.quit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LinkedIn Automation")
        self.setMinimumSize(600, 400)
        self.setup_ui()

    def setup_ui(self):
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Credentials section
        credentials_group = self.create_group_box("LinkedIn Credentials")
        layout.addWidget(credentials_group)

        # File selection section
        file_group = self.create_group_box("CSV File Selection")
        layout.addWidget(file_group)

        # Note section
        note_group = self.create_group_box("Connection Note")
        layout.addWidget(note_group)

        # Progress section
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Ready")
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)

        # Start button
        self.start_button = QPushButton("Start Automation")
        self.start_button.clicked.connect(self.start_automation)
        layout.addWidget(self.start_button)

    def create_group_box(self, title):
        group = QWidget()
        layout = QVBoxLayout(group)

        if title == "LinkedIn Credentials":
            # Username
            self.username_input = QLineEdit()
            self.username_input.setPlaceholderText("LinkedIn Email/Username")
            layout.addWidget(self.username_input)

            # Password
            self.password_input = QLineEdit()
            self.password_input.setPlaceholderText("LinkedIn Password")
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(self.password_input)

        elif title == "CSV File Selection":
            file_layout = QHBoxLayout()
            self.file_path_input = QLineEdit()
            self.file_path_input.setPlaceholderText("Select CSV file with LinkedIn profiles")
            file_layout.addWidget(self.file_path_input)

            browse_button = QPushButton("Browse")
            browse_button.clicked.connect(self.browse_file)
            file_layout.addWidget(browse_button)
            layout.addLayout(file_layout)

        elif title == "Connection Note":
            self.note_input = QTextEdit()
            self.note_input.setPlaceholderText("Enter your connection note here...")
            self.note_input.setMaximumHeight(100)
            layout.addWidget(self.note_input)

        return group

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_name:
            self.file_path_input.setText(file_name)

    def start_automation(self):
        if not self.validate_inputs():
            return

        self.start_button.setEnabled(False)
        self.worker = WorkerThread(
            self.username_input.text(),
            self.password_input.text(),
            self.file_path_input.text(),
            self.note_input.toPlainText()
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_completion)
        self.worker.start()

    def validate_inputs(self):
        if not self.username_input.text():
            self.show_error("Username is required")
            return False
        if not self.password_input.text():
            self.show_error("Password is required")
            return False
        if not self.file_path_input.text():
            self.show_error("CSV file is required")
            return False
        if not os.path.exists(self.file_path_input.text()):
            self.show_error("Selected CSV file does not exist")
            return False
        return True

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def update_progress(self, message):
        self.status_label.setText(message)

    def on_completion(self, success, message):
        self.start_button.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)