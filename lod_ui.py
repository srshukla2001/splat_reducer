import sys
import numpy as np
from plyfile import PlyData, PlyElement
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor

class WorkerThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, input_path, output_path, keep_ratio):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.keep_ratio = keep_ratio
        
    def run(self):
        try:
            self.status.emit("Loading PLY file...")
            ply = PlyData.read(self.input_path)
            self.progress.emit(20)
            
            vertices = ply['vertex'].data  
            vertices_np = np.array(vertices)
            self.progress.emit(40)
            
            total = len(vertices_np)
            keep = int(total * self.keep_ratio)
            self.status.emit(f"Processing: {keep}/{total} points")
            self.progress.emit(60)
            
            idx = np.random.choice(total, keep, replace=False)
            reduced = vertices_np[idx]
            self.progress.emit(80)
            
            vertex_el = PlyElement.describe(reduced, 'vertex')
            PlyData([vertex_el], text=ply.text).write(self.output_path)
            self.progress.emit(100)
            
            self.status.emit(f"✓ File saved")
            self.finished.emit(True, self.output_path)
            
        except Exception as e:
            self.status.emit(f"✗ Error")
            self.finished.emit(False, str(e))

class PLYCompressorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.input_file = None
        self.initUI()
        self.set_dark_theme()
        
    def set_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(25, 25, 30))
        palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
        palette.setColor(QPalette.Base, QColor(35, 35, 40))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 50))
        palette.setColor(QPalette.ToolTipBase, QColor(40, 40, 45))
        palette.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
        palette.setColor(QPalette.Text, QColor(220, 220, 220))
        palette.setColor(QPalette.Button, QColor(45, 45, 50))
        palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
        palette.setColor(QPalette.BrightText, QColor(100, 150, 255))
        palette.setColor(QPalette.Highlight, QColor(100, 150, 255))
        palette.setColor(QPalette.HighlightedText, QColor(25, 25, 30))
        self.setPalette(palette)
        
    def initUI(self):
        self.setWindowTitle('PLY Compressor')
        self.setGeometry(100, 100, 900, 500)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left panel
        left_panel = QFrame()
        left_panel.setFixedWidth(280)
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #1a1a1f;
                border-right: 1px solid #2a2a30;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(30, 40, 30, 40)
        left_layout.setSpacing(20)
        
        # App title
        title = QLabel("PLY COMPRESSOR")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: 600;
            color: #aaa;
            letter-spacing: 1px;
        """)
        left_layout.addWidget(title)
        
        left_layout.addSpacing(20)
        
        # Import button
        import_btn = QPushButton("IMPORT PLY")
        import_btn.setFixedHeight(45)
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a30;
                border: 1px solid #3a3a40;
                border-radius: 4px;
                color: #ccc;
                font-size: 13px;
                font-weight: 500;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #333338;
                border: 1px solid #4a4a50;
            }
            QPushButton:pressed {
                background-color: #2a2a30;
            }
        """)
        import_btn.clicked.connect(self.import_ply)
        left_layout.addWidget(import_btn)
        
        left_layout.addSpacing(30)
        
        # Stats section
        stats_title = QLabel("FILE INFO")
        stats_title.setStyleSheet("font-size: 12px; color: #777; font-weight: 500;")
        left_layout.addWidget(stats_title)
        
        self.file_name_label = QLabel("—")
        self.file_name_label.setStyleSheet("font-size: 14px; color: #ccc; margin-top: 5px;")
        left_layout.addWidget(self.file_name_label)
        
        self.points_label = QLabel("Points: —")
        self.points_label.setStyleSheet("font-size: 13px; color: #888; margin-top: 5px;")
        left_layout.addWidget(self.points_label)
        
        left_layout.addStretch()
        
        # Version
        version = QLabel("v1.0")
        version.setStyleSheet("font-size: 11px; color: #555;")
        left_layout.addWidget(version)
        
        main_layout.addWidget(left_panel)
        
        # Right panel
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #202025;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(50, 50, 50, 50)
        right_layout.setSpacing(30)
        
        # Compression section
        compression_title = QLabel("COMPRESSION SETTINGS")
        compression_title.setStyleSheet("font-size: 14px; color: #aaa; font-weight: 500;")
        right_layout.addWidget(compression_title)
        
        # Slider and value
        slider_layout = QHBoxLayout()
        
        self.ratio_value = QLabel("50%")
        self.ratio_value.setFixedWidth(60)
        self.ratio_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.ratio_value.setStyleSheet("font-size: 24px; color: #6a9eff; font-weight: 600;")
        slider_layout.addWidget(self.ratio_value)
        
        slider_layout.addSpacing(20)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(10, 90)
        self.slider.setValue(50)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #2a2a30;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #6a9eff;
                border-radius: 2px;
            }
            QSlider::add-page:horizontal {
                background: #2a2a30;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #6a9eff;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #7aaeff;
                width: 18px;
                height: 18px;
                border-radius: 9px;
            }
        """)
        slider_layout.addWidget(self.slider)
        self.slider.valueChanged.connect(self.update_ratio_value)
        
        right_layout.addLayout(slider_layout)
        
        # Labels below slider
        labels_layout = QHBoxLayout()
        min_label = QLabel("Less Points")
        min_label.setStyleSheet("color: #777; font-size: 12px;")
        max_label = QLabel("More Points")
        max_label.setStyleSheet("color: #777; font-size: 12px;")
        
        labels_layout.addWidget(min_label)
        labels_layout.addStretch()
        labels_layout.addWidget(max_label)
        right_layout.addLayout(labels_layout)
        
        right_layout.addSpacing(10)
        
        # Info label
        self.info_label = QLabel("Adjust slider to control how many points to keep")
        self.info_label.setStyleSheet("color: #888; font-size: 13px;")
        right_layout.addWidget(self.info_label)
        
        right_layout.addStretch()
        
        # Progress section
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(10)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2a2a30;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #6a9eff;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #999; font-size: 13px;")
        progress_layout.addWidget(self.status_label)
        
        right_layout.addLayout(progress_layout)
        
        # Export button
        self.export_btn = QPushButton("EXPORT COMPRESSED FILE")
        self.export_btn.setFixedHeight(48)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a30;
                border: 1px solid #3a3a40;
                border-radius: 4px;
                color: #999;
                font-size: 13px;
                font-weight: 500;
                letter-spacing: 0.5px;
            }
            QPushButton:enabled {
                background-color: #6a9eff;
                border: 1px solid #6a9eff;
                color: #101015;
                font-weight: 600;
            }
            QPushButton:enabled:hover {
                background-color: #7aaeff;
                border: 1px solid #7aaeff;
            }
            QPushButton:enabled:pressed {
                background-color: #5a8eef;
            }
        """)
        self.export_btn.clicked.connect(self.export_ply)
        self.export_btn.setEnabled(False)
        right_layout.addWidget(self.export_btn)
        
        main_layout.addWidget(right_panel)
        
    def update_ratio_value(self, value):
        self.ratio_value.setText(f"{value}%")
        keep_percent = value
        reduce_percent = 100 - value
        self.info_label.setText(f"Keeping {keep_percent}% • Reducing by {reduce_percent}%")
        
    def import_ply(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open PLY File", "", "PLY Files (*.ply)"
        )
        
        if file_name:
            self.input_file = file_name
            filename_short = file_name.split('/')[-1]
            self.file_name_label.setText(filename_short[:30] + ("..." if len(filename_short) > 30 else ""))
            
            try:
                ply = PlyData.read(file_name)
                vertices = ply['vertex'].data
                total_points = len(vertices)
                self.points_label.setText(f"Points: {total_points:,}")
                self.status_label.setText(f"Loaded {total_points:,} points")
                
                # Update slider info based on file size
                self.update_ratio_value(self.slider.value())
                self.export_btn.setEnabled(True)
                
            except Exception as e:
                self.status_label.setText(f"Error loading file")
                QMessageBox.critical(self, "Error", f"Could not load file:\n{str(e)}")
                
    def export_ply(self):
        if not self.input_file:
            return
            
        output_file, _ = QFileDialog.getSaveFileName(
            self, "Save Compressed PLY", "", "PLY Files (*.ply)"
        )
        
        if output_file:
            if not output_file.endswith('.ply'):
                output_file += '.ply'
                
            keep_ratio = self.slider.value() / 100.0
            
            # Disable UI elements during processing
            self.export_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Processing...")
            
            # Start worker thread
            self.worker = WorkerThread(self.input_file, output_file, keep_ratio)
            self.worker.progress.connect(self.progress_bar.setValue)
            self.worker.status.connect(self.status_label.setText)
            self.worker.finished.connect(self.on_process_finished)
            self.worker.start()
            
    def on_process_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.export_btn.setEnabled(True)
        
        if success:
            self.status_label.setText(f"✓ File saved")
            QMessageBox.information(self, "Success", f"Compressed file saved:\n{message}")
        else:
            self.status_label.setText(f"✗ Error")
            QMessageBox.critical(self, "Error", f"Processing failed:\n{message}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application-wide font
    font = QFont("Inter", 10)
    font.setWeight(QFont.Normal)
    app.setFont(font)
    
    window = PLYCompressorApp()
    window.show()
    sys.exit(app.exec_())