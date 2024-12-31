STYLE_SHEET = """
QMainWindow {
    background-color: #f0f2f5;
}

QLabel {
    font-size: 12px;
    color: #333;
}

QLineEdit, QTextEdit {
    padding: 8px;
    border: 1px solid #ccc;
    border-radius: 4px;
    background-color: white;
}

QPushButton {
    background-color: #0a66c2;
    color: white;
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #004182;
}

QPushButton:disabled {
    background-color: #cccccc;
}

QProgressBar {
    border: 1px solid #ccc;
    border-radius: 4px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #0a66c2;
}
"""