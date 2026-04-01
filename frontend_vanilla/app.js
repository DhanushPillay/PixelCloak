// =================================================================
// PixelCloak — Frontend Application
// =================================================================

// Configurable API endpoint
var API_URL = window.PIXELCLOAK_API_URL || 'http://localhost:8000';

// =================================================================
// MATRIX RAIN BACKGROUND (Upgraded)
// Three character sets, lead characters, two speed tiers
// =================================================================
var canvas = document.getElementById('matrix-canvas');
var ctx = canvas.getContext('2d');

// Character sets with weighted selection
var charsBinary = '01'.split('');
var charsKatakana = 'ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ'.split('');
var charsHex = '0123456789ABCDEF'.split('');

function getRandomChar() {
    var roll = Math.random();
    if (roll < 0.4) {
        return charsBinary[Math.floor(Math.random() * charsBinary.length)];
    } else if (roll < 0.8) {
        return charsKatakana[Math.floor(Math.random() * charsKatakana.length)];
    } else {
        return charsHex[Math.floor(Math.random() * charsHex.length)];
    }
}

var fontSize = 14;
var columns = 0;
var drops = [];
var columnSpeeds = [];  // Speed multiplier per column

function initMatrixColumns() {
    columns = Math.floor(canvas.width / fontSize);
    drops = Array(columns).fill(0).map(function() { return Math.random() * -100; });
    // Assign speed tiers: 40% fast (0.7x interval), 60% slow (1.4x interval)
    columnSpeeds = Array(columns).fill(0).map(function() {
        return Math.random() < 0.4 ? 1.4 : 0.7;
    });
}

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    initMatrixColumns();
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

var frameCount = 0;

function drawMatrix() {
    frameCount++;
    // Fractional opacity for smooth trails (Warm Sand Theme)
    ctx.fillStyle = 'rgba(234, 221, 206, 0.12)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.font = fontSize + 'px "JetBrains Mono", monospace';

    for (var i = 0; i < columns; i++) {
        // Skip frames based on column speed (slower columns skip more)
        if (frameCount % Math.round(columnSpeeds[i] * 2) !== 0) continue;

        if (drops[i] >= 0) {
            var text = getRandomChar();
            var y = drops[i] * fontSize;

            // Lead character: Deep Espresso
            ctx.shadowColor = 'rgba(56, 52, 49, 0.5)';
            ctx.shadowBlur = 4;
            ctx.fillStyle = '#383431';
            ctx.fillText(text, i * fontSize, y);

            // Trail characters above (Warm Taupe)
            if (drops[i] > 1) {
                ctx.shadowBlur = 0;
                var alpha = Math.random() * 0.4 + 0.1;
                ctx.fillStyle = 'rgba(139, 126, 116, ' + alpha + ')'; // text-secondary
                var trailChar = getRandomChar();
                ctx.fillText(trailChar, i * fontSize, (drops[i] - 1) * fontSize);
            }

            // Reset shadow for performance
            ctx.shadowBlur = 0;
        }

        if (drops[i] * fontSize > canvas.height && Math.random() > 0.98) {
            drops[i] = 0;
        }

        drops[i]++;
    }
}

// Use requestAnimationFrame instead of setInterval for better performance
var matrixLastTime = 0;
var MATRIX_FPS_INTERVAL = 1000 / 20;  // 20fps

function matrixLoop(timestamp) {
    requestAnimationFrame(matrixLoop);
    if (timestamp - matrixLastTime < MATRIX_FPS_INTERVAL) return;
    matrixLastTime = timestamp;
    drawMatrix();
}
requestAnimationFrame(matrixLoop);


// =================================================================
// TEXT SCRAMBLER ANIMATION
// =================================================================
function TextScrambler(el) {
    this.el = el;
    this.chars = '!<>-_\\/[]{}—=+*^?#________';
    this.update = this.update.bind(this);
}

TextScrambler.prototype.setText = function(newText) {
    var self = this;
    var oldText = this.el.innerText;
    var length = Math.max(oldText.length, newText.length);
    var promise = new Promise(function(resolve) { self.resolve = resolve; });
    this.queue = [];
    for (var i = 0; i < length; i++) {
        var from = oldText[i] || '';
        var to = newText[i] || '';
        var start = Math.floor(Math.random() * 20);
        var end = start + Math.floor(Math.random() * 20);
        this.queue.push({ from: from, to: to, start: start, end: end });
    }
    cancelAnimationFrame(this.frameRequest);
    this.frame = 0;
    this.update();
    return promise;
};

TextScrambler.prototype.update = function() {
    var output = '';
    var complete = 0;
    for (var i = 0; i < this.queue.length; i++) {
        var item = this.queue[i];
        if (this.frame >= item.end) {
            complete++;
            output += item.to;
        } else if (this.frame >= item.start) {
            if (!item.char || Math.random() < 0.28) {
                item.char = this.chars[Math.floor(Math.random() * this.chars.length)];
                this.queue[i].char = item.char;
            }
            output += '<span class="text-accent">' + item.char + '</span>';
        } else {
            output += item.from;
        }
    }
    this.el.innerHTML = output;
    if (complete === this.queue.length) {
        this.resolve();
    } else {
        this.frameRequest = requestAnimationFrame(this.update);
        this.frame++;
    }
};


// =================================================================
// AMBIENT AUDIO TOGGLE (Web Audio API — 40 Hz binaural drone)
// =================================================================
var audioCtx = null;
var oscillatorL = null;
var oscillatorR = null;
var audioGain = null;
var audioActive = false;

var btnAudio = document.getElementById('btn-audio');
var audioIcon = document.getElementById('audio-icon');

function initAudio() {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    audioGain = audioCtx.createGain();
    audioGain.gain.value = 0.06;  // Very subtle
    audioGain.connect(audioCtx.destination);

    // Left channel: 40 Hz base
    oscillatorL = audioCtx.createOscillator();
    oscillatorL.type = 'sine';
    oscillatorL.frequency.value = 40;

    // Right channel: 40.5 Hz for binaural beat effect
    oscillatorR = audioCtx.createOscillator();
    oscillatorR.type = 'sine';
    oscillatorR.frequency.value = 40.5;

    var merger = audioCtx.createChannelMerger(2);
    var splitterL = audioCtx.createGain();
    var splitterR = audioCtx.createGain();

    oscillatorL.connect(splitterL);
    oscillatorR.connect(splitterR);

    splitterL.connect(merger, 0, 0);
    splitterR.connect(merger, 0, 1);

    merger.connect(audioGain);
    oscillatorL.start();
    oscillatorR.start();
}

if (btnAudio) {
    btnAudio.addEventListener('click', function() {
        if (!audioActive) {
            if (!audioCtx) initAudio();
            if (audioCtx.state === 'suspended') audioCtx.resume();
            audioGain.gain.setTargetAtTime(0.06, audioCtx.currentTime, 0.1);
            btnAudio.classList.add('active');
            audioActive = true;
            // Swap icon to volume-2
            var icon = btnAudio.querySelector('svg');
            if (icon) {
                icon.outerHTML = '<i data-feather="volume-2" id="audio-icon"></i>';
                feather.replace();
            }
        } else {
            audioGain.gain.setTargetAtTime(0, audioCtx.currentTime, 0.1);
            btnAudio.classList.remove('active');
            audioActive = false;
            var icon2 = btnAudio.querySelector('svg');
            if (icon2) {
                icon2.outerHTML = '<i data-feather="volume-x" id="audio-icon"></i>';
                feather.replace();
            }
        }
    });
}


// =================================================================
// STATE & DOM ELEMENTS
// =================================================================
var selectedFiles = [];  // {id, file, previewUrl}
var processedFiles = []; // {id, name, originalUrl, blob}
var currentMode = 'balanced';
var lastResponseMeta = null;  // Store metadata from last successful cloak
var fileIdCounter = 0;
var compareIndex = 0;  // index into processedFiles for comparison slider

// Entrance animations
document.addEventListener('DOMContentLoaded', function() {
    var hero = document.querySelector('.hero');
    var main = document.querySelector('.main-content');
    if (hero) hero.classList.add('animate-entrance');
    if (main) main.classList.add('animate-entrance');

    // Check backend health on load
    checkBackendHealth();
});

// Backend health check
function checkBackendHealth() {
    var indicator = document.getElementById('health-indicator');
    var healthText = document.getElementById('health-text');
    if (!indicator || !healthText) return;

    indicator.style.display = 'flex';

    function poll() {
        fetch(API_URL + '/health', { signal: AbortSignal.timeout(5000) })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.model_loaded) {
                    indicator.classList.add('healthy');
                    indicator.classList.remove('loading', 'error');
                    healthText.textContent = 'READY';
                    // Hide after 3s
                    setTimeout(function() { indicator.style.display = 'none'; }, 3000);
                } else {
                    indicator.classList.add('loading');
                    indicator.classList.remove('healthy', 'error');
                    healthText.textContent = 'LOADING MODEL...';
                    setTimeout(poll, 2000);
                }
            })
            .catch(function() {
                indicator.classList.add('error');
                indicator.classList.remove('healthy', 'loading');
                healthText.textContent = 'BACKEND OFFLINE';
                // Retry every 5s
                setTimeout(poll, 5000);
            });
    }

    poll();
}

// DOM references
var dropzone = document.getElementById('dropzone');
var fileInput = document.getElementById('file-input');
var filePreviewSection = document.getElementById('file-preview-section');
var fileGrid = document.getElementById('file-grid');
var fileCountUi = document.getElementById('file-count');
var actionArea = document.getElementById('action-area');
var readyCount = document.getElementById('ready-count');

var stateIdle = document.getElementById('state-idle');
var stateProcessing = document.getElementById('state-processing');
var stateSuccess = document.getElementById('state-success');
var stateError = document.getElementById('state-error');

var btnStart = document.getElementById('btn-start');
var btnDownload = document.getElementById('btn-download');
var btnCompare = document.getElementById('btn-compare');
var btnRetry = document.getElementById('btn-retry');

var progressBar = document.getElementById('progress-bar');
var progressText = document.getElementById('progress-text');
var fileCounter = document.getElementById('file-counter');
var processingTimer = document.getElementById('processing-timer');

var metadataDisplay = document.getElementById('metadata-display');

// Mode selector
var modeBtns = document.querySelectorAll('.mode-btn');
var modeIndicator = document.getElementById('mode-indicator');
var modeStatusText = document.getElementById('mode-status-text');
var modeDesc = document.getElementById('mode-desc');
var paramEps = document.getElementById('param-eps');
var paramSteps = document.getElementById('param-steps');
var scrambler = new TextScrambler(modeStatusText);

var modesData = {
    'fast': {
        index: 0,
        label: '[ FAST_FGSM ]',
        desc: '1 Step FGSM Attack | Epsilon: 2.0/255 | Surrogate: CLIP<br>Highest speed, lowest detection protection.',
        eps: '2.0',
        steps: '1'
    },
    'balanced': {
        index: 1,
        label: '[ BALANCED_PGD ]',
        desc: '10 Step PGD Attack | Epsilon: 4.0/255 | Surrogate: CLIP<br>Optimal balance of disruption and imperceptibility.',
        eps: '4.0',
        steps: '10'
    },
    'strong': {
        index: 2,
        label: '[ MAX_PGD_DISRUPTION ]',
        desc: '20 Step PGD Attack | Epsilon: 8.0/255 | Surrogate: CLIP<br>Maximum feature destruction. May cause visible artifacts.',
        eps: '8.0',
        steps: '20'
    }
};

modeBtns.forEach(function(btn) {
    btn.addEventListener('click', function(e) {
        var mode = e.target.dataset.mode;
        currentMode = mode;

        modeBtns.forEach(function(b) { b.classList.remove('active'); });
        e.target.classList.add('active');

        var data = modesData[mode];
        modeIndicator.style.transform = 'translateX(' + (data.index * 100) + '%)';
        scrambler.setText(data.label);

        // Update params display
        if (paramEps) paramEps.textContent = data.eps;
        if (paramSteps) paramSteps.textContent = data.steps;

        // Fade description
        modeDesc.style.opacity = 0;
        setTimeout(function() {
            modeDesc.innerHTML = data.desc;
            modeDesc.style.opacity = 1;
        }, 150);
    });
});


// =================================================================
// VISIBILITY HELPERS (simplified — no fragile transition callbacks)
// =================================================================
function showEl(el) {
    if (!el) return;
    el.classList.remove('hidden');
    // Remove ALL inline overrides so the element falls back to its CSS default
    el.style.removeProperty('display');
    el.style.removeProperty('opacity');
}

function hideEl(el, cb) {
    if (!el) return;
    el.classList.add('hidden');
    // Always fire the callback immediately — no more race conditions
    if (cb) cb();
}

function transitionState(hideElement, showElement) {
    hideEl(hideElement);
    showEl(showElement);
}


// =================================================================
// FILE HANDLING
// =================================================================

// Prevent defaults on drag events
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(function(eventName) {
    dropzone.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

['dragenter', 'dragover'].forEach(function(eventName) {
    dropzone.addEventListener(eventName, function() {
        dropzone.classList.add('dragover');
    }, false);
});

['dragleave', 'drop'].forEach(function(eventName) {
    dropzone.addEventListener(eventName, function() {
        dropzone.classList.remove('dragover');
    }, false);
});

// Fix: define drop handler inline (handleDrop was undefined)
dropzone.addEventListener('drop', function(e) {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
}, false);

dropzone.addEventListener('click', function() { fileInput.click(); });
fileInput.addEventListener('change', function() { handleFiles(this.files); });

function handleFiles(files) {
    var newFiles = Array.from(files).filter(function(file) {
        return file.type.startsWith('image/') || /\.(jpe?g|png|webp|avif|gif|bmp|tiff?|heic)$/i.test(file.name);
    });
    var maxSize = 100 * 1024 * 1024;
    var validSizeFiles = newFiles.filter(function(f) {
        return f.size <= maxSize;
    });

    if (validSizeFiles.length < newFiles.length) {
        alert('Some files were skipped because they exceed the 100MB limit.');
    }
    if (validSizeFiles.length === 0) return;

    for (var i = 0; i < validSizeFiles.length; i++) {
        var f = validSizeFiles[i];
        var entry = { id: fileIdCounter++, file: f, previewUrl: null };
        // Create preview URL and track it for cleanup
        entry.previewUrl = URL.createObjectURL(f);
        selectedFiles.push(entry);
    }
    updateUI();
}

// Remove file by ID (accessible from HTML onclick)
window.removeFile = function(id) {
    for (var i = 0; i < selectedFiles.length; i++) {
        if (selectedFiles[i].id === id) {
            if (selectedFiles[i].previewUrl) {
                URL.revokeObjectURL(selectedFiles[i].previewUrl);
            }
            selectedFiles.splice(i, 1);
            break;
        }
    }
    updateUI();
};

function updateUI() {
    if (selectedFiles.length > 0) {
        showEl(filePreviewSection);
        showEl(actionArea);

        showEl(stateIdle);
        hideEl(stateProcessing);
        hideEl(stateSuccess);
        if (stateError) hideEl(stateError);

        fileCountUi.innerText = selectedFiles.length;
        readyCount.innerText = selectedFiles.length;

        fileGrid.innerHTML = '';
        selectedFiles.forEach(function(entry, index) {
            var div = document.createElement('div');
            div.className = 'file-item';
            div.style.animationDelay = (index * 0.05) + 's';

            var src = entry.previewUrl || '';
            div.innerHTML =
                '<img src="' + src + '" alt="preview">' +
                '<div class="file-label">' + entry.file.name + '</div>' +
                '<button class="btn-remove" onclick="removeFile(' + entry.id + ')">' +
                    '<i data-feather="x" style="width: 14px; height: 14px;"></i>' +
                '</button>';
            fileGrid.appendChild(div);
            feather.replace();
        });
    } else {
        hideEl(filePreviewSection);
        hideEl(actionArea);
    }
}


// =================================================================
// PROCESSING (API CALLS)
// =================================================================

var processingTimerInterval = null;

function startProcessingTimer() {
    var startTime = Date.now();
    if (processingTimer) processingTimer.textContent = '00:00';
    processingTimerInterval = setInterval(function() {
        var elapsed = Math.floor((Date.now() - startTime) / 1000);
        var mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
        var secs = String(elapsed % 60).padStart(2, '0');
        if (processingTimer) processingTimer.textContent = mins + ':' + secs;
    }, 1000);
}

function stopProcessingTimer() {
    if (processingTimerInterval) {
        clearInterval(processingTimerInterval);
        processingTimerInterval = null;
    }
}

btnStart.addEventListener('click', async function() {
    transitionState(stateIdle, stateProcessing);
    progressBar.style.width = '0%';
    startProcessingTimer();

    processedFiles = [];
    lastResponseMeta = null;
    var completed = 0;
    var totalFailed = 0;
    var total = selectedFiles.length;

    // Mark all file items as pending
    var fileItems = fileGrid.querySelectorAll('.file-item');
    fileItems.forEach(function(item) { item.classList.remove('error', 'success'); });

    // Process with concurrency limit of 2
    var concurrency = 2;
    var queue = selectedFiles.slice();
    var fileErrors = {};  // id -> error message

    async function processEntry(entry, gridIndex) {
        var formData = new FormData();
        formData.append('file', entry.file);
        formData.append('mode', currentMode);

        var targetImageInput = document.getElementById('target-image');
        if (targetImageInput && targetImageInput.files.length > 0) {
            formData.append('target_image', targetImageInput.files[0]);
        }

        var targetPrompt = document.getElementById('target-prompt').value;
        if (targetPrompt && targetPrompt.trim() !== '') {
            formData.append('target_prompt', targetPrompt.trim());
        }

        var useRobustness = document.getElementById('use-robustness').checked;
        if (useRobustness) {
            formData.append('use_robustness', 'true');
        }

        try {
            var response = await fetch(API_URL + '/cloak', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                var errText = await response.text();
                var errMsg = "HTTP " + response.status;
                try {
                    var parsed = JSON.parse(errText);
                    if (parsed.error) errMsg = parsed.error;
                } catch(e) { errMsg = errText; }
                fileErrors[entry.id] = errMsg;
                return { success: false, id: entry.id, error: errMsg };
            }

            var meta = {
                mode: response.headers.get('X-PixelCloak-Mode') || currentMode,
                steps: response.headers.get('X-PixelCloak-Steps') || '?',
                epsilon: response.headers.get('X-PixelCloak-Epsilon') || '?',
                time: response.headers.get('X-PixelCloak-Time') || '?',
                maxDelta: response.headers.get('X-PixelCloak-MaxDelta') || '?',
                meanDelta: response.headers.get('X-PixelCloak-MeanDelta') || '?'
            };
            lastResponseMeta = meta;

            var blob = await response.blob();
            processedFiles.push({
                id: entry.id,
                name: 'cloaked_' + entry.file.name.split('.')[0] + '.png',
                originalUrl: entry.previewUrl || URL.createObjectURL(entry.file),
                blob: blob
            });
            return { success: true, id: entry.id };

        } catch (error) {
            fileErrors[entry.id] = error.message;
            return { success: false, id: entry.id, error: error.message };
        }
    }

    async function worker() {
        while (queue.length > 0) {
            var entry = queue.shift();
            var gridIndex = selectedFiles.indexOf(entry);
            if (fileCounter) {
                fileCounter.textContent = 'PROCESSING FILE ' + (completed + 1) + ' / ' + total;
            }
            var result = await processEntry(entry, gridIndex);
            completed++;
            if (!result.success) totalFailed++;

            // Mark file item visually
            var items = fileGrid.querySelectorAll('.file-item');
            for (var i = 0; i < items.length; i++) {
                if (selectedFiles[i] && selectedFiles[i].id === result.id) {
                    items[i].classList.add(result.success ? 'success' : 'error');
                    if (!result.success) {
                        items[i].title = result.error;
                    }
                    break;
                }
            }

            var percent = Math.round((completed / total) * 100);
            progressBar.style.width = percent + '%';

            var pctScrambler = new TextScrambler(progressText);
            pctScrambler.setText(percent + '%');
        }
    }

    // Launch workers
    var workers = [];
    for (var w = 0; w < Math.min(concurrency, total); w++) {
        workers.push(worker());
    }
    await Promise.all(workers);

    stopProcessingTimer();

    if (processedFiles.length > 0) {
        transitionState(stateProcessing, stateSuccess);

        // Reset comparison index
        compareIndex = 0;

        // Trigger data burst animation
        var burst = document.getElementById('data-burst');
        if (burst) {
            burst.classList.add('active');
            setTimeout(function() { burst.classList.remove('active'); }, 800);
        }

        // Display metadata strip with typewriter effect
        if (lastResponseMeta && metadataDisplay) {
            displayMetadata(lastResponseMeta);
        }

        // Show partial failure message if some files failed
        if (totalFailed > 0 && totalFailed < total) {
            var partialMsg = document.createElement('p');
            partialMsg.className = 'text-muted text-small mt-4';
            partialMsg.textContent = totalFailed + ' of ' + total + ' file(s) failed. Check highlighted files for details.';
            metadataDisplay.appendChild(partialMsg);
        }

        feather.replace();
    } else {
        if (stateError) {
            transitionState(stateProcessing, stateError);
            feather.replace();
        } else {
            transitionState(stateProcessing, stateIdle);
        }
    }
});

// Retry button
if (btnRetry) {
    btnRetry.addEventListener('click', function() {
        transitionState(stateError, stateIdle);
    });
}


// =================================================================
// METADATA DISPLAY (typewriter effect)
// =================================================================
function displayMetadata(meta) {
    var lines = [
        '<span class="meta-label">MODE:</span> <span class="meta-value">' + meta.mode.toUpperCase() + '</span>',
        '<span class="meta-label">STEPS:</span> <span class="meta-value">' + meta.steps + '</span>  ' +
        '<span class="meta-label">EPSILON:</span> <span class="meta-value">' + meta.epsilon + '/255</span>',
        '<span class="meta-label">TIME:</span> <span class="meta-value">' + meta.time + '</span>',
        '<span class="meta-label">MAX_DELTA:</span> <span class="meta-value">' + meta.maxDelta + '</span>  ' +
        '<span class="meta-label">MEAN_DELTA:</span> <span class="meta-value">' + meta.meanDelta + '</span>'
    ];

    var strip = document.createElement('div');
    strip.className = 'metadata-strip';
    strip.style.opacity = '0';
    metadataDisplay.innerHTML = '';
    metadataDisplay.appendChild(strip);

    // Typewriter: reveal lines one at a time
    var lineIndex = 0;
    strip.style.opacity = '1';

    function addLine() {
        if (lineIndex >= lines.length) return;
        var lineEl = document.createElement('div');
        lineEl.innerHTML = lines[lineIndex];
        strip.appendChild(lineEl);
        lineIndex++;
        setTimeout(addLine, 120);
    }
    addLine();
}


// =================================================================
// DOWNLOAD & ZIP
// =================================================================
btnDownload.addEventListener('click', async function() {
    if (processedFiles.length === 1) {
        var url = URL.createObjectURL(processedFiles[0].blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = processedFiles[0].name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } else {
        var zip = new JSZip();
        processedFiles.forEach(function(gf) { zip.file(gf.name, gf.blob); });

        var zipBlob = await zip.generateAsync({ type: 'blob' });
        var url2 = URL.createObjectURL(zipBlob);
        var a2 = document.createElement('a');
        a2.href = url2;
        a2.download = 'PixelCloak_SecureBatch_' + Date.now() + '.zip';
        document.body.appendChild(a2);
        a2.click();
        document.body.removeChild(a2);
        URL.revokeObjectURL(url2);
    }
});


// =================================================================
// COMPARISON MODAL & SLIDER
// =================================================================
var modal = document.getElementById('comparison-modal');
var btnCloseModal = document.getElementById('btn-close-modal');
var btnAmplify = document.getElementById('btn-amplify');
var btnSaveDiff = document.getElementById('btn-save-diff');
var imgBefore = document.getElementById('img-before');
var imgAfter = document.getElementById('img-after');
var sliderOverlay = document.getElementById('slider-overlay');
var sliderHandle = document.getElementById('slider-handle');
var sliderContainer = document.getElementById('slider-container');

var isAmplified = false;
var isDragging = false;

btnCompare.addEventListener('click', function() {
    if (processedFiles.length === 0) return;
    compareIndex = 0;
    loadComparisonImage(compareIndex);
    modal.classList.remove('hidden');
    modal.style.display = 'flex';
    setTimeout(function() { modal.style.opacity = 1; }, 10);
    setSliderPosition(50);
});

function loadComparisonImage(idx) {
    if (idx < 0 || idx >= processedFiles.length) return;
    compareIndex = idx;
    var previewData = processedFiles[idx];

    // Revoke previous Object URLs for modal images to prevent leaks
    if (imgBefore.src && imgBefore.src.startsWith('blob:')) URL.revokeObjectURL(imgBefore.src);
    if (imgAfter.src && imgAfter.src.startsWith('blob:')) URL.revokeObjectURL(imgAfter.src);

    imgBefore.src = previewData.originalUrl;
    imgAfter.src = URL.createObjectURL(previewData.blob);

    isAmplified = false;
    imgAfter.classList.remove('amplify-noise');
    btnAmplify.innerText = 'TOGGLE_10X_NOISE';
    btnAmplify.style.borderColor = '';
    btnAmplify.style.color = '';
    btnAmplify.style.boxShadow = '';

    // Update nav counter
    var navCounter = document.getElementById('compare-nav-counter');
    if (navCounter) {
        navCounter.textContent = (idx + 1) + ' / ' + processedFiles.length;
    }

    // Update nav button states
    var btnPrev = document.getElementById('btn-compare-prev');
    var btnNext = document.getElementById('btn-compare-next');
    if (btnPrev) btnPrev.disabled = (idx === 0);
    if (btnNext) btnNext.disabled = (idx === processedFiles.length - 1);
}

btnCloseModal.addEventListener('click', closeModal);

function closeModal() {
    modal.style.opacity = 0;
    setTimeout(function() {
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }, 400);
}

btnAmplify.addEventListener('click', function() {
    isAmplified = !isAmplified;
    if (isAmplified) {
        imgAfter.classList.add('amplify-noise');
        btnAmplify.innerText = 'AMPLIFIER_ACTIVE';
        btnAmplify.style.borderColor = 'var(--accent)';
        btnAmplify.style.color = 'var(--accent)';
        btnAmplify.style.boxShadow = '0 0 10px rgba(0, 229, 176, 0.4)';
    } else {
        imgAfter.classList.remove('amplify-noise');
        btnAmplify.innerText = 'TOGGLE_10X_NOISE';
        btnAmplify.style.borderColor = '';
        btnAmplify.style.color = '';
        btnAmplify.style.boxShadow = '';
    }
});

// Save diff layer: compute |original - cloaked| on hidden canvas, amplify x50
if (btnSaveDiff) {
    btnSaveDiff.addEventListener('click', function() {
        if (processedFiles.length === 0 || compareIndex >= processedFiles.length) return;

        var diffCanvas = document.getElementById('diff-canvas');
        var diffCtx = diffCanvas.getContext('2d');
        var data = processedFiles[compareIndex];

        var imgOrig = new Image();
        var imgCloak = new Image();
        var loaded = 0;

        function onBothLoaded() {
            loaded++;
            if (loaded < 2) return;

            var w = imgOrig.naturalWidth;
            var h = imgOrig.naturalHeight;
            diffCanvas.width = w;
            diffCanvas.height = h;

            // Draw original, get pixels
            diffCtx.drawImage(imgOrig, 0, 0, w, h);
            var origPixels = diffCtx.getImageData(0, 0, w, h);

            // Draw cloaked, get pixels
            diffCtx.drawImage(imgCloak, 0, 0, w, h);
            var cloakPixels = diffCtx.getImageData(0, 0, w, h);

            // Compute |orig - cloak| * 50
            var output = diffCtx.createImageData(w, h);
            for (var p = 0; p < origPixels.data.length; p += 4) {
                output.data[p]     = Math.min(255, Math.abs(origPixels.data[p]     - cloakPixels.data[p])     * 50);
                output.data[p + 1] = Math.min(255, Math.abs(origPixels.data[p + 1] - cloakPixels.data[p + 1]) * 50);
                output.data[p + 2] = Math.min(255, Math.abs(origPixels.data[p + 2] - cloakPixels.data[p + 2]) * 50);
                output.data[p + 3] = 255;
            }

            diffCtx.putImageData(output, 0, 0);

            // Download
            diffCanvas.toBlob(function(blob) {
                var url = URL.createObjectURL(blob);
                var a = document.createElement('a');
                a.href = url;
                a.download = 'POISON_LAYER_REVEALED.png';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }, 'image/png');
        }

        imgOrig.crossOrigin = 'anonymous';
        imgCloak.crossOrigin = 'anonymous';
        imgOrig.onload = onBothLoaded;
        imgCloak.onload = onBothLoaded;
        imgOrig.src = data.originalUrl;
        imgCloak.src = URL.createObjectURL(data.blob);
    });
}

// Comparison slider navigation
var btnComparePrev = document.getElementById('btn-compare-prev');
var btnCompareNext = document.getElementById('btn-compare-next');

if (btnComparePrev) {
    btnComparePrev.addEventListener('click', function() {
        if (compareIndex > 0) loadComparisonImage(compareIndex - 1);
    });
}
if (btnCompareNext) {
    btnCompareNext.addEventListener('click', function() {
        if (compareIndex < processedFiles.length - 1) loadComparisonImage(compareIndex + 1);
    });
}


// --- Slider position ---
function setSliderPosition(percent) {
    percent = Math.min(Math.max(percent, 0), 100);
    sliderOverlay.style.width = percent + '%';
    sliderHandle.style.left = percent + '%';

    var containerWidth = sliderContainer.getBoundingClientRect().width;
    imgBefore.style.width = containerWidth + 'px';
}

window.addEventListener('resize', function() {
    if (!modal.classList.contains('hidden')) {
        var currentLeft = parseFloat(sliderHandle.style.left);
        setSliderPosition(currentLeft);
    }
});

// Mouse drag
sliderHandle.addEventListener('mousedown', function() { isDragging = true; });
window.addEventListener('mouseup', function() { isDragging = false; });
window.addEventListener('mousemove', function(e) {
    if (!isDragging) return;
    moveSlider(e);
});

sliderContainer.addEventListener('mousedown', function(e) {
    isDragging = true;
    moveSlider(e);
});

// Touch support for slider
sliderHandle.addEventListener('touchstart', function() { isDragging = true; }, { passive: true });
window.addEventListener('touchend', function() { isDragging = false; });
window.addEventListener('touchmove', function(e) {
    if (!isDragging) return;
    moveSlider(e.touches[0]);
}, { passive: true });

sliderContainer.addEventListener('touchstart', function(e) {
    isDragging = true;
    moveSlider(e.touches[0]);
}, { passive: true });

function moveSlider(e) {
    var rect = sliderContainer.getBoundingClientRect();
    var x = (e.clientX || e.pageX) - rect.left;
    var percent = (x / rect.width) * 100;
    setSliderPosition(percent);
}

// Keyboard support: Escape closes, arrow keys move slider, Shift+arrows navigate files
document.addEventListener('keydown', function(e) {
    if (modal.classList.contains('hidden')) return;

    if (e.key === 'Escape') {
        closeModal();
    } else if (e.key === 'ArrowLeft' && e.shiftKey) {
        e.preventDefault();
        if (compareIndex > 0) loadComparisonImage(compareIndex - 1);
    } else if (e.key === 'ArrowRight' && e.shiftKey) {
        e.preventDefault();
        if (compareIndex < processedFiles.length - 1) loadComparisonImage(compareIndex + 1);
    } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        var current = parseFloat(sliderHandle.style.left) || 50;
        setSliderPosition(current - 5);
    } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        var current2 = parseFloat(sliderHandle.style.left) || 50;
        setSliderPosition(current2 + 5);
    }
});
