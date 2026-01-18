import sys
import os
import numpy as np
from plyfile import PlyData, PlyElement
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import uuid
import threading
import time

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Progress tracking
progress_data = {
    'status': 'idle',  # idle, processing, completed, error
    'progress': 0,
    'message': ''
}

result_file_path = None

def compress_ply_task(input_path, keep_ratio, task_id):
    """Background task to compress PLY file"""
    global progress_data, result_file_path
    
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
        result_file_path = f"compressed_{task_id}.ply"
        PlyData([vertex_el], text=ply.text).write(result_file_path)
        
        progress_data['progress'] = 100
        progress_data['status'] = 'completed'
        progress_data['message'] = f'Compression complete! {keep}/{total} points kept.'
        
        print(f"Task {task_id}: Saved reduced PLY → {result_file_path}")
        
        # Clean up input file after 5 minutes
        def cleanup():
            time.sleep(300)
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(result_file_path):
                os.remove(result_file_path)
        
        threading.Thread(target=cleanup, daemon=True).start()
        
    except Exception as e:
        progress_data['status'] = 'error'
        progress_data['message'] = str(e)
        print(f"Task {task_id}: Error - {e}")

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
    global progress_data
    
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
    
    # Save uploaded file
    task_id = str(uuid.uuid4())[:8]
    input_path = f"upload_{task_id}.ply"
    file.save(input_path)
    
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
    global result_file_path
    
    if not result_file_path or not os.path.exists(result_file_path):
        return jsonify({'error': 'No result file available'}), 404
    
    return send_file(
        result_file_path,
        as_attachment=True,
        download_name=os.path.basename(result_file_path),
        mimetype='application/octet-stream'
    )

if __name__ == '__main__':
    # Create required directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('results', exist_ok=True)
    
    print("Starting PLY Compression Server...")
    print("Open http://localhost:5000 in your browser")
    print("\nRequirements:")
    print("pip install flask flask-cors numpy plyfile")
    print("\nServer running on http://localhost:5000")
    
    app.run(debug=True, port=5000, host='0.0.0.0')