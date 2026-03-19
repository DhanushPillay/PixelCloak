// ---------------------------------------------------------
// MATRIX RAIN BACKGROUND EFFECT (HIGH-END)
// ---------------------------------------------------------
const canvas = document.getElementById('matrix-canvas');
const ctx = canvas.getContext('2d');

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

// Premium Details: Mix of Binary and Japanese Katakana for authentic but sleek styling
const chars = '01ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ'.split('');
const fontSize = 14;
let columns = Math.floor(canvas.width / fontSize);
let drops = Array(columns).fill().map(() => Math.random() * -100); // Random stagger start

function drawMatrix() {
    // Fractional opacity for smooth cinematic motion trails
    ctx.fillStyle = 'rgba(3, 3, 5, 0.1)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.shadowColor = '#00ffcc';
    ctx.shadowBlur = 5;
    ctx.font = \`\${fontSize}px 'Courier New'\`; // Clean monospace

    for (let i = 0; i < columns; i++) {
        // Only draw if drop position is valid (handles staggering)
        if (drops[i] >= 0) {
            // Randomize brightness slightly for depth
            const alpha = Math.random() * 0.5 + 0.5;
            ctx.fillStyle = \`rgba(0, 255, 204, \${alpha})\`;
            
            const text = chars[Math.floor(Math.random() * chars.length)];
            ctx.fillText(text, i * fontSize, drops[i] * fontSize);
        }

        // Reset drop randomly to create varied column density
        if (drops[i] * fontSize > canvas.height && Math.random() > 0.98) {
            drops[i] = 0;
        }
        
        drops[i]++;
    }
}
// 50ms interval = 20fps for that cinematic monitor feel, avoiding jitter
setInterval(drawMatrix, 50);

// ---------------------------------------------------------
// TEXT SCRAMBLER ANIMATION
// ---------------------------------------------------------
class TextScrambler {
    constructor(el) {
        this.el = el;
        this.chars = '!<>-_\\/[]{}—=+*^?#________';
        this.update = this.update.bind(this);
    }
    setText(newText) {
        const oldText = this.el.innerText;
        const length = Math.max(oldText.length, newText.length);
        const promise = new Promise((resolve) => this.resolve = resolve);
        this.queue = [];
        for (let i = 0; i < length; i++) {
            const from = oldText[i] || '';
            const to = newText[i] || '';
            const start = Math.floor(Math.random() * 20);
            const end = start + Math.floor(Math.random() * 20);
            this.queue.push({ from, to, start, end });
        }
        cancelAnimationFrame(this.frameRequest);
        this.frame = 0;
        this.update();
        return promise;
    }
    update() {
        let output = '';
        let complete = 0;
        for (let i = 0, n = this.queue.length; i < n; i++) {
            let { from, to, start, end, char } = this.queue[i];
            if (this.frame >= end) {
                complete++;
                output += to;
            } else if (this.frame >= start) {
                if (!char || Math.random() < 0.28) {
                    char = this.chars[Math.floor(Math.random() * this.chars.length)];
                    this.queue[i].char = char;
                }
                output += \`<span class="text-accent">\${char}</span>\`;
            } else {
                output += from;
            }
        }
        this.el.innerHTML = output;
        if (complete === this.queue.length) {
            this.resolve();
        } else {
            this.frameRequest = requestAnimationFrame(this.update);
            this.frame++;
        }
    }
}

// ---------------------------------------------------------
// STATE & DOM ELEMENTS
// ---------------------------------------------------------
const API_URL = 'http://localhost:8000';
let selectedFiles = [];
let processedFiles = []; 
let currentMode = 'balanced';

// Initial staggering on load via classes
document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('.hero').classList.add('animate-entrance');
    document.querySelector('.main-content').classList.add('animate-entrance');
});

// Elements
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
const btnCompare = document.getElementById('btn-compare');

const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');

// Mode Selector
const modeBtns = document.querySelectorAll('.mode-btn');
const modeIndicator = document.getElementById('mode-indicator');
const modeStatusText = document.getElementById('mode-status-text');
const modeDesc = document.getElementById('mode-desc');
const scrambler = new TextScrambler(modeStatusText);

const modesData = {
    'fast': {
        index: 0,
        label: '[ FAST_FGSM ]',
        desc: '1 Step FGSM Attack | Epsilon: 2.0/255 | Surrogate: CLIP<br>Highest speed, lowest detection protection.'
    },
    'balanced': {
        index: 1,
        label: '[ BALANCED_PGD ]',
        desc: '10 Step PGD Attack | Epsilon: 4.0/255 | Surrogate: CLIP<br>Optimal balance of disruption and imperceptibility.'
    },
    'strong': {
        index: 2,
        label: '[ MAX_PGD_DISRUPTION ]',
        desc: '20 Step PGD Attack | Epsilon: 8.0/255 | Surrogate: CLIP<br>Maximum feature destruction. May cause visible artifacts.'
    }
};

// Mode logic with snappier CSS transitions triggering inside JS
modeBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
        const mode = e.target.dataset.mode;
        currentMode = mode;
        
        modeBtns.forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        
        const data = modesData[mode];
        modeIndicator.style.transform = \`translateX(\${data.index * 100}%)\`;
        scrambler.setText(data.label);
        
        // Smooth fade out/in for description text
        modeDesc.style.opacity = 0;
        setTimeout(() => {
            modeDesc.innerHTML = data.desc;
            modeDesc.style.opacity = 1;
        }, 150);
    });
});

// ---------------------------------------------------------
// FILE HANDLING
// ---------------------------------------------------------

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, () => dropzone.classList.add('dragover'), false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, () => dropzone.classList.remove('dragover'), false);
});

dropzone.addEventListener('drop', handleDrop, false);
dropzone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', function() { handleFiles(this.files); });

function handleFiles(files) {
    const newFiles = Array.from(files).filter(file => file.type.startsWith('image/'));
    const validSizeFiles = newFiles.filter(f => f.size <= 10 * 1024 * 1024);
    
    if(validSizeFiles.length < newFiles.length) {
        alert("Some files were skipped because they exceed the 10MB limit.");
    }
    if (validSizeFiles.length === 0) return;

    selectedFiles = [...selectedFiles, ...validSizeFiles];
    updateUI();
}

// Accessible globally from inside HTML onclick attribute
window.removeFile = function(index) {
    selectedFiles.splice(index, 1);
    updateUI();
}

function updateUI() {
    if (selectedFiles.length > 0) {
        filePreviewSection.classList.remove('hidden');
        actionArea.classList.remove('hidden');
        
        // Use timeout to allow display:block before opacity fade in
        setTimeout(() => {
            filePreviewSection.style.opacity = 1;
            actionArea.style.opacity = 1;
        }, 10);
        
        stateIdle.classList.remove('hidden');
        setTimeout(() => stateIdle.style.opacity = 1, 10);
        
        stateProcessing.classList.add('hidden');
        stateSuccess.classList.add('hidden');
        stateProcessing.style.opacity = 0;
        stateSuccess.style.opacity = 0;
        
        fileCountUi.innerText = selectedFiles.length;
        readyCount.innerText = selectedFiles.length;
        
        fileGrid.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onloadend = () => {
                const div = document.createElement('div');
                div.className = 'file-item';
                // Inline animation staggering for dynamically generated elements
                div.style.animationDelay = \`\${index * 0.05}s\`;
                
                div.innerHTML = \`
                    <img src="\${reader.result}" alt="preview">
                    <div class="file-label" style="position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.85); padding: 5px; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border-top: 1px solid rgba(0, 255, 204, 0.3); font-family: var(--font-mono); color: var(--accent-color);">\${file.name}</div>
                    <button class="btn-remove" onclick="removeFile(\${index})">
                        <i data-feather="x" style="width: 14px; height: 14px;"></i>
                    </button>
                \`;
                fileGrid.appendChild(div);
                feather.replace();
            }
        });
    } else {
        filePreviewSection.style.opacity = 0;
        actionArea.style.opacity = 0;
        setTimeout(() => {
            filePreviewSection.classList.add('hidden');
            actionArea.classList.add('hidden');
        }, 300);
    }
}

// ---------------------------------------------------------
// PROCESSING (API CALLS)
// ---------------------------------------------------------

function transitionState(hideEl, showEl) {
    hideEl.style.opacity = 0;
    setTimeout(() => {
        hideEl.classList.add('hidden');
        showEl.classList.remove('hidden');
        setTimeout(() => {
            showEl.style.opacity = 1;
        }, 50);
    }, 300);
}

btnStart.addEventListener('click', async () => {
    transitionState(stateIdle, stateProcessing);
    
    processedFiles = [];
    let completed = 0;
    
    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('mode', currentMode);

        try {
            const response = await fetch(\`\${API_URL}/cloak\`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) continue;

            const blob = await response.blob();
            const origUrl = URL.createObjectURL(file);
            
            processedFiles.push({
                name: \`cloaked_\${file.name.split('.')[0]}.png\`,
                originalUrl: origUrl,
                blob: blob
            });

        } catch (error) {
            console.error(\`Error processing \${file.name}:\`, error);
        }

        completed++;
        // Smoothly animate the gradient stripes bar
        const percent = Math.round((completed / selectedFiles.length) * 100);
        progressBar.style.width = percent + '%';
        
        // Scramble animation for the percentage text to match theme
        const pctScrambler = new TextScrambler(progressText);
        pctScrambler.setText(percent + '%');
    }

    if (processedFiles.length > 0) {
        transitionState(stateProcessing, stateSuccess);
    } else {
        alert("Operation failed for all files. Ensure backend is running.");
        transitionState(stateProcessing, stateIdle);
    }
});

// ---------------------------------------------------------
// DOWNLOAD & ZIP
// ---------------------------------------------------------

btnDownload.addEventListener('click', async () => {
    if (processedFiles.length === 1) {
        const url = URL.createObjectURL(processedFiles[0].blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = processedFiles[0].name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } else {
        const zip = new JSZip();
        processedFiles.forEach((gf) => zip.file(gf.name, gf.blob));
        
        const zipBlob = await zip.generateAsync({type: "blob"});
        const url = URL.createObjectURL(zipBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = \`PixelCloak_SecureBatch_\${Date.now()}.zip\`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
});

// ---------------------------------------------------------
// DIAGNOSTIC SLIDER & MODAL
// ---------------------------------------------------------
const modal = document.getElementById('comparison-modal');
const btnCloseModal = document.getElementById('btn-close-modal');
const btnAmplify = document.getElementById('btn-amplify');
const imgBefore = document.getElementById('img-before');
const imgAfter = document.getElementById('img-after');
const sliderOverlay = document.getElementById('slider-overlay');
const sliderHandle = document.getElementById('slider-handle');
const sliderContainer = document.getElementById('slider-container');

let isAmplified = false;
let isDragging = false;

btnCompare.addEventListener('click', () => {
    if(processedFiles.length === 0) return;
    
    const previewData = processedFiles[0];
    imgBefore.src = previewData.originalUrl;
    imgAfter.src = URL.createObjectURL(previewData.blob);
    
    isAmplified = false;
    imgAfter.classList.remove('amplify-noise');
    btnAmplify.innerText = "TOGGLE_10X_NOISE";
    btnAmplify.style.borderColor = "var(--text-color)";
    btnAmplify.style.color = "var(--text-color)";
    
    modal.classList.remove('hidden');
    setTimeout(() => modal.style.opacity = 1, 10);
    setSliderPosition(50);
});

btnCloseModal.addEventListener('click', () => {
    modal.style.opacity = 0;
    setTimeout(() => modal.classList.add('hidden'), 400);
});

btnAmplify.addEventListener('click', () => {
    isAmplified = !isAmplified;
    if(isAmplified) {
        imgAfter.classList.add('amplify-noise');
        btnAmplify.innerText = "AMPLIFIER_ACTIVE";
        btnAmplify.style.borderColor = "var(--accent-color)";
        btnAmplify.style.color = "var(--accent-color)";
        btnAmplify.style.boxShadow = "0 0 10px rgba(0, 255, 204, 0.4)";
    } else {
        imgAfter.classList.remove('amplify-noise');
        btnAmplify.innerText = "TOGGLE_10X_NOISE";
        btnAmplify.style.borderColor = "var(--text-color)";
        btnAmplify.style.color = "var(--text-color)";
        btnAmplify.style.boxShadow = "none";
    }
});

function setSliderPosition(percent) {
    percent = Math.min(Math.max(percent, 0), 100);
    sliderOverlay.style.width = \`\${percent}%\`;
    sliderHandle.style.left = \`\${percent}%\`;
    
    const containerWidth = sliderContainer.getBoundingClientRect().width;
    imgBefore.style.width = \`\${containerWidth}px\`;
}

window.addEventListener('resize', () => {
    if(!modal.classList.contains('hidden')) {
        const currentLeft = parseFloat(sliderHandle.style.left);
        setSliderPosition(currentLeft);
    }
});

sliderHandle.addEventListener('mousedown', () => isDragging = true);
window.addEventListener('mouseup', () => isDragging = false);
window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    moveSlider(e);
});

sliderContainer.addEventListener('mousedown', (e) => {
    isDragging = true;
    moveSlider(e);
});

function moveSlider(e) {
    const rect = sliderContainer.getBoundingClientRect();
    let x = e.clientX - rect.left;
    let percent = (x / rect.width) * 100;
    setSliderPosition(percent);
}
