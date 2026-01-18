import sys
import numpy as np
from plyfile import PlyData, PlyElement
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor

# Check for pyvista and vtk
try:
    import pyvista as pv
    from pyvistaqt import QtInteractor
    PV_AVAILABLE = True
except ImportError:
    PV_AVAILABLE = False
    print("Warning: PyVista not installed. Install with: pip install pyvista pyvistaqt")

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
        self.current_plotter = None
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
        self.setGeometry(100, 100, 1200, 700)
        
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
            color: #aaaaaa;
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
                color: #cccccc;
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
        
        # Preview button
        self.preview_btn = QPushButton("PREVIEW CURRENT")
        self.preview_btn.setFixedHeight(45)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a2a40;
                border: 1px solid #4a3a50;
                border-radius: 4px;
                color: #cccccc;
                font-size: 13px;
                font-weight: 500;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #443348;
                border: 1px solid #5a4a60;
            }
            QPushButton:pressed {
                background-color: #3a2a40;
            }
            QPushButton:disabled {
                background-color: #2a2a30;
                color: #666666;
                border: 1px solid #3a3a40;
            }
        """)
        self.preview_btn.clicked.connect(self.preview_current)
        self.preview_btn.setEnabled(False)
        left_layout.addWidget(self.preview_btn)
        
        left_layout.addSpacing(30)
        
        # Stats section
        stats_title = QLabel("FILE INFO")
        stats_title.setStyleSheet("font-size: 12px; color: #777777; font-weight: 500;")
        left_layout.addWidget(stats_title)
        
        self.file_name_label = QLabel("—")
        self.file_name_label.setStyleSheet("font-size: 14px; color: #cccccc; margin-top: 5px;")
        left_layout.addWidget(self.file_name_label)
        
        self.points_label = QLabel("Points: —")
        self.points_label.setStyleSheet("font-size: 13px; color: #888888; margin-top: 5px;")
        left_layout.addWidget(self.points_label)
        
        left_layout.addStretch()
        
        # Version
        version = QLabel("v1.0")
        version.setStyleSheet("font-size: 11px; color: #555555;")
        left_layout.addWidget(version)
        
        main_layout.addWidget(left_panel)
        
        # Right panel
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #202025;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(40, 40, 40, 40)
        right_layout.setSpacing(25)
        
        # Compression section
        compression_title = QLabel("COMPRESSION SETTINGS")
        compression_title.setStyleSheet("font-size: 14px; color: #aaaaaa; font-weight: 500;")
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
        min_label.setStyleSheet("color: #777777; font-size: 12px;")
        max_label = QLabel("More Points")
        max_label.setStyleSheet("color: #777777; font-size: 12px;")
        
        labels_layout.addWidget(min_label)
        labels_layout.addStretch()
        labels_layout.addWidget(max_label)
        right_layout.addLayout(labels_layout)
        
        right_layout.addSpacing(10)
        
        # Info label
        self.info_label = QLabel("Adjust slider to control how many points to keep")
        self.info_label.setStyleSheet("color: #888888; font-size: 13px;")
        right_layout.addWidget(self.info_label)
        
        # 3D Viewer section
        viewer_title = QLabel("3D PREVIEW")
        viewer_title.setStyleSheet("font-size: 14px; color: #aaaaaa; font-weight: 500; margin-top: 15px;")
        right_layout.addWidget(viewer_title)
        
        # 3D Viewer container
        viewer_container = QFrame()
        viewer_container.setStyleSheet("""
            QFrame {
                background-color: #1a1a1f;
                border: 1px solid #2a2a30;
                border-radius: 6px;
            }
        """)
        viewer_container.setMinimumHeight(350)
        viewer_layout = QVBoxLayout(viewer_container)
        viewer_layout.setContentsMargins(2, 2, 2, 2)
        
        if PV_AVAILABLE:
            # Create PyVista QtInteractor
            self.plotter = QtInteractor(viewer_container)
            viewer_layout.addWidget(self.plotter.interactor)
            
            # Configure plotter for dark theme
            self.plotter.set_background("#1a1a1f")
            self.plotter.add_axes(color='white')
            self.plotter.add_camera_orientation_widget()
            
            # Add initial placeholder text - using valid color format
            self.plotter.add_text(
                "No point cloud loaded\n\nImport a PLY file to visualize",
                position='upper_left',
                font_size=14,
                color='gray'  # Changed from #888 to valid color
            )
            self.plotter.show_grid(color='#333333')
            
        else:
            # Fallback message if PyVista not available
            error_label = QLabel("PyVista not installed.\n\nInstall with:\npip install pyvista pyvistaqt")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: #888888; font-size: 14px; padding: 20px;")
            viewer_layout.addWidget(error_label)
        
        right_layout.addWidget(viewer_container)
        
        right_layout.addSpacing(15)
        
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
        self.status_label.setStyleSheet("color: #999999; font-size: 13px;")
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
                color: #999999;
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
                self.preview_btn.setEnabled(True)
                
                # Auto-preview the loaded file
                if PV_AVAILABLE:
                    self.preview_file(file_name, "Original")
                
                # Update slider info based on file size
                self.update_ratio_value(self.slider.value())
                self.export_btn.setEnabled(True)
                
            except Exception as e:
                self.status_label.setText(f"Error loading file")
                QMessageBox.critical(self, "Error", f"Could not load file:\n{str(e)}")
                
    def preview_current(self):
        """Preview the currently loaded file with current compression ratio"""
        if not self.input_file or not PV_AVAILABLE:
            return
            
        try:
            ply = PlyData.read(self.input_file)
            vertices = ply['vertex'].data
            vertices_np = np.array(vertices)
            
            total = len(vertices_np)
            keep_ratio = self.slider.value() / 100.0
            keep = int(total * keep_ratio)
            
            idx = np.random.choice(total, keep, replace=False)
            reduced = vertices_np[idx]
            
            # Create temporary array for visualization
            if vertices_np.dtype.names is not None:
                # Extract position data (assuming first 3 fields are x, y, z)
                if 'x' in vertices_np.dtype.names:
                    points = np.column_stack([reduced['x'], reduced['y'], reduced['z']])
                else:
                    # Try to find position data in first 3 columns
                    points = np.column_stack([reduced[reduced.dtype.names[0]], 
                                            reduced[reduced.dtype.names[1]], 
                                            reduced[reduced.dtype.names[2]]])
                
                # Try to extract color if available
                colors = None
                if 'red' in vertices_np.dtype.names and 'green' in vertices_np.dtype.names and 'blue' in vertices_np.dtype.names:
                    colors = np.column_stack([reduced['red']/255.0, 
                                            reduced['green']/255.0, 
                                            reduced['blue']/255.0])
                elif 'r' in vertices_np.dtype.names and 'g' in vertices_np.dtype.names and 'b' in vertices_np.dtype.names:
                    colors = np.column_stack([reduced['r']/255.0, 
                                            reduced['g']/255.0, 
                                            reduced['b']/255.0])
            else:
                # If no structured array, assume first 3 columns are positions
                points = reduced[:, :3]
                colors = None
                
            self.visualize_points(points, colors, f"Preview ({keep}/{total} points)")
            
        except Exception as e:
            self.status_label.setText(f"Preview error")
            QMessageBox.warning(self, "Preview Error", f"Could not generate preview:\n{str(e)}")
    
    def preview_file(self, file_path, title="Point Cloud"):
        """Preview a PLY file directly"""
        if not PV_AVAILABLE:
            return
            
        try:
            # Clear previous plot
            self.plotter.clear()
            
            # Read and visualize PLY file
            mesh = pv.read(file_path)
            
            # Check if it's point cloud or mesh
            if mesh.n_points < 1000000:  # For reasonable performance
                if isinstance(mesh, pv.PolyData) and mesh.n_cells > 0:
                    # It's a mesh with faces
                    self.plotter.add_mesh(
                        mesh,
                        color='#6a9eff',
                        show_edges=False,
                        opacity=0.8
                    )
                else:
                    # It's a point cloud
                    self.plotter.add_points(
                        mesh.points,
                        color='#6a9eff',
                        point_size=3.0,
                        render_points_as_spheres=True
                    )
            else:
                # For large point clouds, show only subset
                subset = mesh.points[::10]  # Show every 10th point
                self.plotter.add_points(
                    subset,
                    color='#6a9eff',
                    point_size=2.0,
                    render_points_as_spheres=True
                )
            
            self.plotter.add_axes(color='white')
            self.plotter.add_text(
                title,
                position='upper_left',
                font_size=12,
                color='lightgray'  # Changed to valid color
            )
            self.plotter.show_grid(color='#333333')
            self.plotter.reset_camera()
            self.plotter.render()
            
        except Exception as e:
            # If PyVista can't read it, try manual loading
            try:
                ply = PlyData.read(file_path)
                vertices = ply['vertex'].data
                vertices_np = np.array(vertices)
                
                # Extract position data
                if vertices_np.dtype.names is not None:
                    if 'x' in vertices_np.dtype.names:
                        points = np.column_stack([vertices_np['x'], 
                                                vertices_np['y'], 
                                                vertices_np['z']])
                    else:
                        points = vertices_np[[vertices_np.dtype.names[0], 
                                            vertices_np.dtype.names[1], 
                                            vertices_np.dtype.names[2]]].view(np.float32).reshape(-1, 3)
                else:
                    points = vertices_np[:, :3]
                
                self.visualize_points(points, None, title)
                
            except Exception as e2:
                self.plotter.clear()
                self.plotter.add_text(
                    f"Could not visualize: {str(e2)[:50]}...",
                    position='center',
                    font_size=12,
                    color='red'  # Changed to valid color
                )
                self.plotter.render()
    
    def visualize_points(self, points, colors=None, title="Point Cloud"):
        """Visualize point cloud data"""
        if not PV_AVAILABLE:
            return
            
        self.plotter.clear()
        
        # Create point cloud
        point_cloud = pv.PolyData(points)
        
        # Add points with optional colors
        if colors is not None and len(colors) == len(points):
            point_cloud['colors'] = colors
            self.plotter.add_points(
                point_cloud,
                scalars='colors' if colors is not None else None,
                rgb=True if colors is not None else False,
                point_size=3.0,
                render_points_as_spheres=True,
                opacity=0.8
            )
        else:
            self.plotter.add_points(
                point_cloud,
                color='#6a9eff',
                point_size=3.0,
                render_points_as_spheres=True,
                opacity=0.8
            )
        
        self.plotter.add_axes(color='white')
        self.plotter.add_text(
            f"{title}\nPoints: {len(points):,}",
            position='upper_left',
            font_size=12,
            color='lightgray'  # Changed to valid color
        )
        self.plotter.show_grid(color='#333333')
        self.plotter.reset_camera()
        self.plotter.render()
        
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
            self.preview_btn.setEnabled(False)
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
        self.preview_btn.setEnabled(True)
        
        if success:
            self.status_label.setText(f"✓ File saved")
            
            # Preview the exported file
            if PV_AVAILABLE:
                self.preview_file(message, "Compressed")
            
            QMessageBox.information(self, "Success", f"Compressed file saved:\n{message}")
        else:
            self.status_label.setText(f"✗ Error")
            QMessageBox.critical(self, "Error", f"Processing failed:\n{message}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Check for required packages
    if not PV_AVAILABLE:
        reply = QMessageBox.question(
            None,
            "Missing Dependencies",
            "PyVista is required for 3D visualization.\n\nInstall now? (Requires pip)",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyvista", "pyvistaqt"])
            QMessageBox.information(None, "Success", "Please restart the application.")
            sys.exit(0)
    
    # Set application-wide font
    font = QFont("Inter", 10)
    font.setWeight(QFont.Normal)
    app.setFont(font)
    
    window = PLYCompressorApp()
    window.show()
    sys.exit(app.exec_())