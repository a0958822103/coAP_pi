let currentActiveSection = null;
let outputTimer = null;

function activateSection(secId) {
    currentActiveSection = secId;

    // 1. 隱藏所有區塊內容，並取消按鈕高亮
    document.querySelectorAll('.block-content').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.activate-btn').forEach(el => el.classList.remove('active-section-btn'));
    
    // 防呆機制：切換區塊時取消原本選取的模式，確保使用者重選
    document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active-mode'));

    // 2. 顯示點擊的區塊
    document.getElementById('content-' + secId).style.display = 'block';
    document.getElementById('btn-activate-' + secId).classList.add('active-section-btn');

    // 3. 執行 appendChild 把加入排程按鈕搬過來
    const addBtn = document.getElementById('shared-add-btn');
    const targetContainer = document.getElementById('append-container-' + secId);
    targetContainer.appendChild(addBtn);
    addBtn.style.display = 'inline-block'; 
}

function setMode(btnElement, cmd, isRest = false) {
    document.getElementById('content-' + currentActiveSection).querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.remove('active-mode');
    });
    btnElement.classList.add('active-mode');
    sendCommand(cmd);
}

function startOutputWithTimer() {
    if (!currentActiveSection) return alert("⚠️ 請先啟用並設定一個區塊！");

    const secInput = document.getElementById('time-' + currentActiveSection).value;
    const btnOn = document.getElementById('btn-on');
    const display = document.getElementById('output-countdown');
    const stepDisplay = document.getElementById('val-step'); 
    document.getElementById('val-mode').style.color = "#28a745"

    if (!secInput || secInput <= 0) return alert("⚠️ 請先輸入執行時間 (秒)!");

    const sec = parseInt(secInput);
    const ms = sec * 1000;

    sendCommand(`TIMer:TRIGgered ${ms}`);
    setTimeout(() => { sendCommand('OUTP ON'); }, 500);

    let remain = sec;
    let isRunning = true; 
    let stepHistory = []; 
    
    btnOn.disabled = true;
    btnOn.style.background = "#ccc";
    display.innerText = `輸出中... 剩餘 ${remain} 秒`;
    stepDisplay.innerText = "讀取中..."; 

    if (outputTimer) clearInterval(outputTimer);

    outputTimer = setInterval(() => {
        if (!isRunning) return; 

        fetch(`/api/charger/cmd?cmd=${encodeURIComponent('MEAS:INF:STEP?')}`)
            .then(res => res.json())
            .then(data => {
                if (!isRunning) return; 
                const currentStep = parseInt(data.response);
                if (!isNaN(currentStep)) stepDisplay.innerText = currentStep;

                stepHistory.push(currentStep);
                if (stepHistory.length > 2) stepHistory.shift(); 

                if (stepHistory.length === 2 && stepHistory[0] !== stepHistory[1]) {
                    isRunning = false;
                    clearInterval(outputTimer);
                    sendCommand('OUTP OFF'); 
                    display.innerText = `🛑 觸發條件！步序由 ${stepHistory[0]} 跳至 ${stepHistory[1]}，提早結束！`;
                    btnOn.disabled = false;
                    btnOn.style.background = "#28a745";
                }
            }).catch(err => console.error(err));
        
        remain--;
        
        if (remain <= 0 && isRunning) {
            isRunning = false;
            clearInterval(outputTimer);
            sendCommand('OUTP OFF'); 
            display.innerText = "時間到，執行完畢";
            btnOn.disabled = false;
            btnOn.style.background = "#28a745";
            stepDisplay.innerText = "--"; 
        } else if (isRunning) {
            display.innerText = `輸出中... 剩餘 ${remain} 秒`;
        }
    }, 1000);
}

function forceStopOutput() {
    sendCommand('OUTP OFF');
    sendCommand('PROGram:STATE STOP'); 
    if (outputTimer) clearInterval(outputTimer);
    
    document.getElementById('btn-on').disabled = false;
    document.getElementById('btn-on').style.background = "#28a745";
    document.getElementById('output-countdown').innerText = "🛑 已手動緊急停止";

    document.getElementById('val-mode').style.color = "#6c757d"; // 變成灰色
    document.getElementById('val-step').innerText = "--";
    document.getElementById('val-chg-mah').innerText = "0.0";
    document.getElementById('val-dis-mah').innerText = "0.0";

    
}

function setupInputListener(inputId, btnId, template) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(btnId);
    if(input && btn) {
        input.addEventListener('input', function() { 
            btn.innerText = template.replace('${value}', this.value); 
        });
    }
}