// ---------------------------------------------------------
// MATRIX RAIN BACKGROUND EFFECT
// ---------------------------------------------------------
const canvas = document.getElementById('matrix-canvas');
const ctx = canvas.getContext('2d');

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ'.split('');
const fontSize = 14;
let columns = canvas.width / fontSize;
let drops = [];
for (let x = 0; x < columns; x++) drops[x] = 1;

function drawMatrix() {
    ctx.fillStyle = 'rgba(5, 5, 16, 0.05)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#00ffcc';
    ctx.font = fontSize + 'px monospace';

    for (let i = 0; i < drops.length; i++) {
        const text = chars[Math.floor(Math.random() * chars.length)];
        ctx.fillText(text, i * fontSize, drops[i] * fontSize);
        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
            drops[i] = 0;
        }
        drops[i]++;
    }
}
setInterval(drawMatrix, 33);

// ---------------------------------------------------------
// UI & DRAG-AND-DROP LOGIC
// ---------------------------------------------------------
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const filePreviewSection = document.getElementById('file-preview-section');
const fileGrid = document.getElementById('file-grid');
const fileCountUi = document.getElementById('file-count');
const actionArea = document.getElementById('action-area');
const readyCount = document.getElementById('ready-count');

const stateIdle = document.getElementById('state-idle');
const stateProcessing = document.getElementById('state-processing');
const stateSuccess = document.getElementById('state-success');

const btnStart = document.getElementById('btn-start');
const btnDownload = document.getElementById('btn-download');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');

let selectedFiles = [];

// Drag Events
dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        handleFiles(e.dataTransfer.files);
    }
});

// Click to Upload
dropzone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

function handleFiles(files) {
    const validImageFiles = Array.from(files).filter(file => file.type.startsWith('image/'));
    selectedFiles = [...selectedFiles, ...validImageFiles];
    updateUI();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateUI();
}

function updateUI() {
    if (selectedFiles.length === 0) {
        filePreviewSection.classList.add('hidden');
        actionArea.classList.add('hidden');
        fileInput.value = ''; // reset input
        return;
    }

    filePreviewSection.classList.remove('hidden');
    actionArea.classList.remove('hidden');

    // Reset specific states
    stateIdle.classList.remove('hidden');
    stateProcessing.classList.add('hidden');
    stateSuccess.classList.add('hidden');

    fileCountUi.textContent = selectedFiles.length;
    readyCount.textContent = selectedFiles.length;

    // Render Grid
    fileGrid.innerHTML = '';
    selectedFiles.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';

        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);

        const label = document.createElement('div');
        label.className = 'file-label';
        label.textContent = file.name;

        const btn = document.createElement('button');
        btn.className = 'btn-remove';
        btn.innerHTML = feather.icons['x'].toSvg({ width: 14, height: 14 });
        btn.onclick = (e) => {
            e.stopPropagation();
            removeFile(index);
        };

        item.appendChild(img);
        item.appendChild(label);
        item.appendChild(btn);
        fileGrid.appendChild(item);
    });
}

// ---------------------------------------------------------
// CLOAKING EXECUTION (Backend Connection)
// ---------------------------------------------------------
let cloakedFilesData = [];

btnStart.addEventListener('click', async () => {
    if (selectedFiles.length === 0) return;

    // Transition UI State
    stateIdle.classList.add('hidden');
    stateProcessing.classList.remove('hidden');

    progressBar.style.width = '0%';
    progressText.textContent = '0%';
    cloakedFilesData = []; // Reset previous downloads

    try {
        const totalFiles = selectedFiles.length;
        let processedCount = 0;

        for (let i = 0; i < totalFiles; i++) {
            const file = selectedFiles[i];
            const formData = new FormData();
            formData.append('file', file);

            // POST to the Python FastAPI backend
            const response = await fetch('http://127.0.0.1:8000/cloak', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${await response.text()}`);
            }

            // The backend returns the raw image blob
            const blob = await response.blob();
            cloakedFilesData.push({
                originalName: file.name,
                blob: blob
            });

            // Update UI Progress smoothly
            processedCount++;
            const currentProgress = Math.round((processedCount / totalFiles) * 100);
            progressBar.style.width = `${currentProgress}%`;
            progressText.textContent = `${currentProgress}%`;
        }

        // Switch to Success State after all files are processed
        setTimeout(() => {
            stateProcessing.classList.add('hidden');
            stateSuccess.classList.remove('hidden');
            feather.replace(); // Re-initialize icons
        }, 800);

    } catch (error) {
        console.error("Cloaking Error:", error);
        alert(`PROTOCOL FAILURE: ${error.message}\nEnsure the Python Backend is running on port 8000.`);

        // Revert UI on failure
        stateProcessing.classList.add('hidden');
        stateIdle.classList.remove('hidden');
    }
});

btnDownload.addEventListener('click', () => {
    if (cloakedFilesData.length === 0) return;

    // For single file, just download it directly
    if (cloakedFilesData.length === 1) {
        downloadBlob(cloakedFilesData[0].blob, `cloaked_${cloakedFilesData[0].originalName}`);
        return;
    }

    // For multiple files, we'll download them sequentially 
    // (A real app would zip them on the frontend using JSZip, but this is simpler for the prototype)
    cloakedFilesData.forEach((fileData, index) => {
        setTimeout(() => {
            downloadBlob(fileData.blob, `cloaked_${fileData.originalName}`);
        }, index * 300); // Stagger downloads slightly
    });
});

function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}
