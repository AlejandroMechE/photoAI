document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const video = document.getElementById('webcam-feed');
    const guideOverlay = document.getElementById('guide-overlay');
    const guideCtx = guideOverlay.getContext('2d');
    
    const teamRosterContainer = document.getElementById('team-roster-container');
    const currentSubjectDisplay = document.getElementById('current-subject-display');
    const currentEmotionBadge = document.getElementById('current-emotion-badge');
    const gallerySubjectName = document.getElementById('gallery-subject-name');
    const galleryEmotionName = document.getElementById('gallery-emotion-name');
    
    const btnStartBurst = document.getElementById('btn-start-burst');
    const btnSinglePhoto = document.getElementById('btn-single-photo');
    const btnRefreshGallery = document.getElementById('btn-refresh-gallery');
    const intervalSelect = document.getElementById('interval-select');
    
    const burstOverlay = document.getElementById('burst-overlay');
    const burstCountNum = document.getElementById('burst-count-num');
    const flashEffect = document.getElementById('flash-effect');
    
    const totalProgressBar = document.getElementById('total-progress-bar');
    const totalPercentText = document.getElementById('total-percent-text');
    const totalCapturedCount = document.getElementById('total-captured-count');
    const galleryGrid = document.getElementById('gallery-grid');
    const galleryCountBadge = document.getElementById('gallery-count-badge');

    // State Variables
    let currentSubject = 'alan';
    let currentEmotion = 'feliz';
    let isCapturing = false;
    let systemStats = null;

    const TEAM_MEMBERS = ['alan', 'alex', 'jorge', 'marco', 'francis', 'cristo'];
    const EMOTIONS = ['feliz', 'enojado', 'triste'];

    // 1. Initialize Webcam Stream
    async function initWebcam() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
                audio: false
            });
            video.srcObject = stream;
            video.onloadedmetadata = () => {
                resizeOverlay();
                drawFaceGuide();
            };
        } catch (err) {
            console.error("Camera access error:", err);
            alert("No se pudo acceder a la cámara web. Por favor otorga permisos de cámara.");
        }
    }

    function resizeOverlay() {
        guideOverlay.width = video.clientWidth || 640;
        guideOverlay.height = video.clientHeight || 480;
    }
    window.addEventListener('resize', resizeOverlay);

    // 2. Draw Face Oval Overlay Guide on Canvas
    function drawFaceGuide() {
        const w = guideOverlay.width;
        const h = guideOverlay.height;
        guideCtx.clearRect(0, 0, w, h);

        if (!w || !h) return;

        const centerX = w / 2;
        const centerY = h / 2;
        const radiusX = w * 0.22;
        const radiusY = h * 0.35;

        // Outer dim background
        guideCtx.fillStyle = 'rgba(0, 0, 0, 0.25)';
        guideCtx.fillRect(0, 0, w, h);

        // Cutout face oval
        guideCtx.globalCompositeOperation = 'destination-out';
        guideCtx.beginPath();
        guideCtx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
        guideCtx.fill();
        guideCtx.globalCompositeOperation = 'source-over';

        // Draw dashed face oval outline
        guideCtx.strokeStyle = '#38bdf8';
        guideCtx.lineWidth = 3;
        guideCtx.setLineDash([8, 6]);
        guideCtx.beginPath();
        guideCtx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
        guideCtx.stroke();

        // Eye position crosshair guide line
        guideCtx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        guideCtx.lineWidth = 1;
        guideCtx.setLineDash([4, 4]);
        
        // Eye level horizontal line
        const eyeY = centerY - radiusY * 0.2;
        guideCtx.beginPath();
        guideCtx.moveTo(centerX - radiusX * 0.8, eyeY);
        guideCtx.lineTo(centerX + radiusX * 0.8, eyeY);
        guideCtx.stroke();

        requestAnimationFrame(drawFaceGuide);
    }

    // 3. Fetch Status & Render Team Roster
    async function loadStatus() {
        try {
            const res = await fetch('/api/status');
            systemStats = await res.json();
            renderTeamRoster();
            updateGlobalProgress();
        } catch (err) {
            console.error("Error fetching stats:", err);
        }
    }

    function renderTeamRoster() {
        teamRosterContainer.innerHTML = '';
        TEAM_MEMBERS.forEach(member => {
            let memberTotal = 0;
            if (systemStats && systemStats.stats[member]) {
                memberTotal = Object.values(systemStats.stats[member]).reduce((a, b) => a + b, 0);
            }

            const item = document.createElement('div');
            item.className = `team-member-item ${member === currentSubject ? 'active' : ''}`;
            const isComplete = memberTotal >= 300; // 3 emotions x 100

            item.innerHTML = `
                <div class="member-info">
                    <div class="member-avatar">${member[0].toUpperCase()}</div>
                    <span class="member-name">${member}</span>
                </div>
                <span class="member-progress-badge ${isComplete ? 'completed' : ''}">
                    ${memberTotal} / 300
                </span>
            `;

            item.addEventListener('click', () => {
                currentSubject = member;
                currentSubjectDisplay.textContent = member;
                gallerySubjectName.textContent = member;
                renderTeamRoster();
                loadGallery();
            });

            teamRosterContainer.appendChild(item);
        });
    }

    function updateGlobalProgress() {
        if (!systemStats) return;
        const total = systemStats.total_images || 0;
        const target = systemStats.target_total || 1800;
        const percent = Math.min(100, Math.round((total / target) * 100));

        totalCapturedCount.textContent = total.toLocaleString();
        totalPercentText.textContent = `${percent}%`;
        totalProgressBar.style.width = `${percent}%`;
    }

    // 4. Emotion Selector Handlers
    document.querySelectorAll('.btn-emotion').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.btn-emotion').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            currentEmotion = btn.dataset.emotion;
            galleryEmotionName.textContent = currentEmotion;

            // Update badge in header
            currentEmotionBadge.className = `emotion-pill emotion-${currentEmotion}`;
            const iconMap = { feliz: 'smile', enojado: 'angry', triste: 'sad-tear' };
            currentEmotionBadge.innerHTML = `<i class="fa-solid fa-face-${iconMap[currentEmotion]}"></i> ${currentEmotion.charAt(0).toUpperCase() + currentEmotion.slice(1)}`;

            loadGallery();
        });
    });

    // 5. Capture Image Frame from Video
    function captureFrameBase64() {
        const offCanvas = document.createElement('canvas');
        offCanvas.width = video.videoWidth || 640;
        offCanvas.height = video.videoHeight || 480;
        const ctx = offCanvas.getContext('2d');

        // Flip horizontally to match mirrored video preview
        ctx.translate(offCanvas.width, 0);
        ctx.scale(-1, 1);
        ctx.drawImage(video, 0, 0, offCanvas.width, offCanvas.height);

        return offCanvas.toDataURL('image/jpeg', 0.9);
    }

    // Flash animation effect
    function triggerFlash() {
        flashEffect.classList.add('flash');
        setTimeout(() => flashEffect.classList.remove('flash'), 80);
    }

    // 6. Rapid 100-Burst Engine
    async function start100Burst() {
        if (isCapturing) return;
        isCapturing = true;
        
        btnStartBurst.disabled = true;
        btnSinglePhoto.disabled = true;
        burstOverlay.classList.remove('hidden');

        const delayMs = parseInt(intervalSelect.value) || 120;
        const totalPhotos = 100;

        for (let i = 1; i <= totalPhotos; i++) {
            burstCountNum.textContent = i;
            triggerFlash();

            const imageBase64 = captureFrameBase64();

            // Send payload to backend
            try {
                await fetch('/api/upload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        subject: currentSubject,
                        emotion: currentEmotion,
                        image: imageBase64
                    })
                });
            } catch (err) {
                console.error(`Error uploading frame ${i}:`, err);
            }

            // Delay next shot
            await new Promise(r => setTimeout(r, delayMs));
        }

        // Complete burst
        burstOverlay.classList.add('hidden');
        isCapturing = false;
        btnStartBurst.disabled = false;
        btnSinglePhoto.disabled = false;

        // Refresh stats and gallery
        await loadStatus();
        await loadGallery();
    }

    // Single photo capture
    async function captureSinglePhoto() {
        if (isCapturing) return;
        triggerFlash();
        const imageBase64 = captureFrameBase64();

        try {
            await fetch('/api/upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    subject: currentSubject,
                    emotion: currentEmotion,
                    image: imageBase64
                })
            });
            await loadStatus();
            await loadGallery();
        } catch (err) {
            console.error("Error single upload:", err);
        }
    }

    // 7. Load & Render Gallery
    async function loadGallery() {
        try {
            const res = await fetch(`/api/photos/${currentSubject}/${currentEmotion}`);
            const photos = await res.json();

            galleryCountBadge.textContent = `${photos.length} fotos`;
            galleryGrid.innerHTML = '';

            photos.forEach(photoObj => {
                const item = document.createElement('div');
                item.className = 'gallery-item';

                const imgUrl = typeof photoObj === 'string' ? `/dataset/${currentSubject}/${currentEmotion}/${photoObj}` : (photoObj.url || `/dataset/${currentSubject}/${currentEmotion}/${photoObj.filename}`);
                const photoId = typeof photoObj === 'string' ? photoObj : (photoObj.id || photoObj.filename);

                const img = document.createElement('img');
                img.src = imgUrl;
                img.alt = photoId;

                const delBtn = document.createElement('button');
                delBtn.className = 'btn-delete-photo';
                delBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
                delBtn.title = 'Eliminar foto';

                delBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    deletePhoto(photoId);
                });

                item.appendChild(img);
                item.appendChild(delBtn);
                galleryGrid.appendChild(item);
            });
        } catch (err) {
            console.error("Error loading gallery:", err);
        }
    }

    async function deletePhoto(filename) {
        try {
            await fetch('/api/delete_photo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    subject: currentSubject,
                    emotion: currentEmotion,
                    filename: filename
                })
            });
            await loadStatus();
            await loadGallery();
        } catch (err) {
            console.error("Error deleting photo:", err);
        }
    }

    async function clearCurrentSection() {
        const confirmMsg = `¿Estás seguro de borrar TODAS las fotos de ${currentSubject.toUpperCase()} (${currentEmotion})? Esta acción no se puede deshacer.`;
        if (!confirm(confirmMsg)) return;

        try {
            const res = await fetch('/api/clear_section', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    subject: currentSubject,
                    emotion: currentEmotion
                })
            });
            const data = await res.json();
            if (data.success) {
                await loadStatus();
                await loadGallery();
            }
        } catch (err) {
            console.error("Error clearing section:", err);
        }
    }

    // Event Listeners
    btnStartBurst.addEventListener('click', start100Burst);
    btnSinglePhoto.addEventListener('click', captureSinglePhoto);
    btnRefreshGallery.addEventListener('click', () => { loadStatus(); loadGallery(); });
    document.getElementById('btn-clear-section').addEventListener('click', clearCurrentSection);

    // Initialize
    initWebcam();
    loadStatus();
    loadGallery();
});
