const dropArea = document.getElementById('dropArea');
const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const fileInfo = document.getElementById('fileInfo');
const compressionSlider = document.getElementById('compressionSlider');
const percentageValue = document.getElementById('percentageValue');
const compressBtn = document.getElementById('compressBtn');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const downloadBtn = document.getElementById('downloadBtn');
const statusInfo = document.getElementById('statusInfo');

let selectedFile = null;

// Drag & drop functionality
dropArea.addEventListener('click', () => fileInput.click());

dropArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropArea.style.background = '#e6f0ff';
});

dropArea.addEventListener('dragleave', () => {
    dropArea.style.background = '';
});

dropArea.addEventListener('drop', (e) => {
    e.preventDefault();
    dropArea.style.background = '';
    if (e.dataTransfer.files.length) {
        handleFile(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleFile(e.target.files[0]);
    }
});

function handleFile(file) {
    if (!file.name.toLowerCase().endsWith('.ply')) {
        showStatus('Please select a .ply file', 'error');
        return;
    }

    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.style.display = 'block';
    compressBtn.disabled = false;
    downloadBtn.style.display = 'none';
    progressContainer.style.display = 'none';

    showStatus('File loaded successfully. Adjust compression slider and click Compress.', 'info');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Update percentage display
compressionSlider.addEventListener('input', () => {
    percentageValue.textContent = compressionSlider.value;
});

// Compress button click
compressBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    compressBtn.disabled = true;
    progressContainer.style.display = 'block';
    progressFill.style.width = '10%';
    progressText.textContent = 'Uploading to server...';
    showStatus('', 'info');

    const formData = new FormData();
    formData.append('plyfile', selectedFile);
    formData.append('keep_ratio', (compressionSlider.value / 100).toString());

    try {
        const response = await fetch('/compress', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        progressFill.style.width = '50%';
        progressText.textContent = 'Processing with Python...';

        // Check progress
        const interval = setInterval(async () => {
            try {
                const progressRes = await fetch('/progress');
                const data = await progressRes.json();

                if (data.status === 'processing') {
                    progressFill.style.width = `${50 + data.progress * 0.5}%`;
                    progressText.textContent = `Compressing: ${Math.round(data.progress)}%`;
                } else if (data.status === 'completed') {
                    clearInterval(interval);
                    progressFill.style.width = '100%';
                    progressText.textContent = 'Compression complete!';

                    // Get the result
                    const resultRes = await fetch('/result');
                    const blob = await resultRes.blob();

                    // Create download link
                    const url = window.URL.createObjectURL(blob);
                    downloadBtn.onclick = () => {
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `compressed_${selectedFile.name}`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);
                    };

                    downloadBtn.style.display = 'block';
                    showStatus(`Compression successful! Reduced to ${compressionSlider.value}% of original points.`, 'success');
                } else if (data.status === 'error') {
                    clearInterval(interval);
                    showStatus(`Error: ${data.message}`, 'error');
                    progressContainer.style.display = 'none';
                    compressBtn.disabled = false;
                }
            } catch (error) {
                console.error('Progress check error:', error);
            }
        }, 1000);

    } catch (error) {
        console.error('Error:', error);
        showStatus(`Error: ${error.message}`, 'error');
        progressContainer.style.display = 'none';
        compressBtn.disabled = false;
    }
});

function showStatus(message, type) {
    statusInfo.textContent = message;
    statusInfo.className = 'status ' + type;
    statusInfo.style.display = message ? 'block' : 'none';
}

// Initialize percentage display
percentageValue.textContent = compressionSlider.value;