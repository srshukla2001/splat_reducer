import sys
import os
import numpy as np
from plyfile import PlyData, PlyElement
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import uuid
import threading
import time
import atexit
import shutil
import signal
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Create directories
UPLOAD_DIR = 'uploads'
RESULT_DIR = 'results'
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

# Track active files and cleanup times
file_cleanup_tracker = {}
MAX_FILE_AGE_MINUTES = 5  # Clean up files after 5 minutes
CLEANUP_INTERVAL_SECONDS = 60  # Run cleanup every minute

# Progress tracking
progress_data = {
    'status': 'idle',
    'progress': 0,
    'message': ''
}

# Store task data
current_task_data = {
    'input_path': None,
    'result_path': None,
    'task_id': None
}

def schedule_file_cleanup(file_path, delay_seconds=300):
    """Schedule a file for deletion after delay"""
    def cleanup():
        time.sleep(delay_seconds)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Cleaned up: {file_path}")
        except Exception as e:
            print(f"Error cleaning up {file_path}: {e}")
    
    thread = threading.Thread(target=cleanup, daemon=True)
    thread.start()
    return thread

def cleanup_old_files():
    """Periodic cleanup of old files"""
    while True:
        time.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            now = datetime.now()
            
            # Clean uploads directory
            for filename in os.listdir(UPLOAD_DIR):
                filepath = os.path.join(UPLOAD_DIR, filename)
                if os.path.isfile(filepath):
                    file_age = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if now - file_age > timedelta(minutes=MAX_FILE_AGE_MINUTES):
                        try:
                            os.remove(filepath)
                            print(f"Cleaned old file: {filepath}")
                        except:
                            pass
            
            # Clean results directory
            for filename in os.listdir(RESULT_DIR):
                filepath = os.path.join(RESULT_DIR, filename)
                if os.path.isfile(filepath):
                    file_age = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if now - file_age > timedelta(minutes=MAX_FILE_AGE_MINUTES):
                        try:
                            os.remove(filepath)
                            print(f"Cleaned old file: {filepath}")
                        except:
                            pass
                            
        except Exception as e:
            print(f"Cleanup error: {e}")

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

# Cleanup on exit
def cleanup_on_exit():
    """Clean all files on application exit"""
    print("Cleaning up all files...")
    try:
        if os.path.exists(UPLOAD_DIR):
            shutil.rmtree(UPLOAD_DIR)
        if os.path.exists(RESULT_DIR):
            shutil.rmtree(RESULT_DIR)
    except:
        pass

atexit.register(cleanup_on_exit)

# Handle SIGTERM for Render shutdown
def handle_sigterm(signum, frame):
    cleanup_on_exit()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

def compress_ply_task(input_path, keep_ratio, task_id):
    """Background task to compress PLY file"""
    global progress_data, current_task_data
    
    try:
        progress_data['status'] = 'processing'
        progress_data['progress'] = 10
        progress_data['message'] = 'Reading PLY file...'
        
        print(f"Task {task_id}: Loading {input_path} ...")
        ply = PlyData.read(input_path)
        
        vertices = ply['vertex'].data  
        vertices_np = np.array(vertices) 

        total = len(vertices_np)
        keep = int(total * keep_ratio)

        print(f"Task {task_id}: Total splats: {total}")
        print(f"Task {task_id}: Keeping {keep} splats ({keep_ratio*100:.1f}%) ...")
        
        progress_data['progress'] = 30
        progress_data['message'] = 'Random sampling points...'
        
        idx = np.random.choice(total, keep, replace=False)
        reduced = vertices_np[idx]
        
        progress_data['progress'] = 60
        progress_data['message'] = 'Creating compressed PLY...'
        
        vertex_el = PlyElement.describe(reduced, 'vertex')
        
        # Save to unique file
        result_path = os.path.join(RESULT_DIR, f"compressed_{task_id}.ply")
        PlyData([vertex_el], text=ply.text).write(result_path)
        
        # Delete input file immediately after creating output
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
                print(f"Deleted input file: {input_path}")
        except Exception as e:
            print(f"Error deleting input file: {e}")
        
        # Update current task data
        current_task_data['input_path'] = None  # Already deleted
        current_task_data['result_path'] = result_path
        current_task_data['task_id'] = task_id
        
        progress_data['progress'] = 100
        progress_data['status'] = 'completed'
        progress_data['message'] = f'Compression complete! {keep}/{total} points kept.'
        
        print(f"Task {task_id}: Saved reduced PLY → {result_path}")
        
        # Schedule result file cleanup after 5 minutes
        schedule_file_cleanup(result_path, 300)
        
    except Exception as e:
        progress_data['status'] = 'error'
        progress_data['message'] = str(e)
        print(f"Task {task_id}: Error - {e}")
        
        # Clean up input file on error too
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except:
            pass

@app.route('/')
def index():
    """Serve the HTML interface"""
    return send_file('index.html')

@app.route('/app.js')
def serve_js():
    """Serve JavaScript file"""
    return send_file('app.js')

@app.route('/compress', methods=['POST'])
def compress():
    """Handle file upload and start compression"""
    global progress_data, current_task_data
    
    if 'plyfile' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['plyfile']
    keep_ratio = float(request.form.get('keep_ratio', 0.25))
    
    if not file.filename.lower().endswith('.ply'):
        return jsonify({'error': 'File must be a .ply file'}), 400
    
    # Reset progress
    progress_data = {
        'status': 'idle',
        'progress': 0,
        'message': ''
    }
    
    # Reset task data
    current_task_data = {
        'input_path': None,
        'result_path': None,
        'task_id': None
    }
    
    # Save uploaded file
    task_id = str(uuid.uuid4())[:8]
    input_path = os.path.join(UPLOAD_DIR, f"upload_{task_id}.ply")
    file.save(input_path)
    
    # Store input path for potential cleanup
    current_task_data['input_path'] = input_path
    current_task_data['task_id'] = task_id
    
    # Start compression in background thread
    thread = threading.Thread(
        target=compress_ply_task,
        args=(input_path, keep_ratio, task_id),
        daemon=True
    )
    thread.start()
    
    return jsonify({
        'message': 'Compression started',
        'task_id': task_id
    }), 202

@app.route('/progress')
def get_progress():
    """Get current compression progress"""
    return jsonify(progress_data)

@app.route('/result')
def get_result():
    """Download the compressed PLY file"""
    global current_task_data
    
    result_path = current_task_data.get('result_path')
    
    if not result_path or not os.path.exists(result_path):
        return jsonify({'error': 'No result file available'}), 404
    
    try:
        # Send file
        response = send_file(
            result_path,
            as_attachment=True,
            download_name=os.path.basename(result_path),
            mimetype='application/octet-stream'
        )
        
        # Schedule immediate cleanup after download
        def cleanup_after_download():
            try:
                if os.path.exists(result_path):
                    os.remove(result_path)
                    print(f"Cleaned up result file after download: {result_path}")
            except Exception as e:
                print(f"Error cleaning result file: {e}")
        
        # Start cleanup in background thread
        thread = threading.Thread(target=cleanup_after_download, daemon=True)
        thread.start()
        
        # Clear current task data
        current_task_data['result_path'] = None
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup', methods=['POST'])
def manual_cleanup():
    """Manual cleanup endpoint (call from frontend when user closes browser)"""
    global current_task_data
    
    try:
        cleaned = []
        
        # Clean input file if exists
        input_path = current_task_data.get('input_path')
        if input_path and os.path.exists(input_path):
            os.remove(input_path)
            cleaned.append(input_path)
            current_task_data['input_path'] = None
        
        # Clean result file if exists
        result_path = current_task_data.get('result_path')
        if result_path and os.path.exists(result_path):
            os.remove(result_path)
            cleaned.append(result_path)
            current_task_data['result_path'] = None
        
        # Clean old files in directories
        for filename in os.listdir(UPLOAD_DIR):
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
                cleaned.append(filepath)
        
        for filename in os.listdir(RESULT_DIR):
            filepath = os.path.join(RESULT_DIR, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
                cleaned.append(filepath)
        
        print(f"Manual cleanup completed: {len(cleaned)} files removed")
        return jsonify({
            'message': f'Cleaned {len(cleaned)} files',
            'cleaned': cleaned
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server on port {port}")
    print(f"Upload directory: {UPLOAD_DIR}")
    print(f"Result directory: {RESULT_DIR}")
    print(f"File cleanup: Every {CLEANUP_INTERVAL_SECONDS} seconds")
    app.run(host='0.0.0.0', port=port)