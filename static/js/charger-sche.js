let scheduleSteps = []; 

function addStepToSchedule() {
    if (!currentActiveSection) return alert("異常：找不到啟用的區塊！");
    
    const activeBlockContent = document.getElementById('content-' + currentActiveSection);
    const activeBtn = activeBlockContent.querySelector('.mode-btn.active-mode');
    
    if (!activeBtn) return alert("請先在區塊內選擇一個模式 (例如 CCC)！");

    const modeText = activeBtn.innerText.split(' ')[0]; 
    let timeVal, volt, curr, voltTrigMax, voltTrigMin, currTrig;

    if (currentActiveSection === 'chg') {
        timeVal = parseInt(document.getElementById('time-chg').value);
        volt = parseInt(document.getElementById('volt-chg').value) || 0;
        curr = parseInt(document.getElementById('curr-chg').value) || 0;
        voltTrigMax = parseInt(document.getElementById('volt-max-chg').value) || 0;
        voltTrigMin = 0; 
        currTrig = parseInt(document.getElementById('curr-trig-chg').value) || 0;
    } else if (currentActiveSection === 'dis') {
        timeVal = parseInt(document.getElementById('time-dis').value);
        volt = parseInt(document.getElementById('volt-dis').value) || 0;
        curr = parseInt(document.getElementById('curr-dis').value) || 0;
        voltTrigMax = 0; 
        voltTrigMin = parseInt(document.getElementById('volt-min-dis').value) || 0;
        currTrig = parseInt(document.getElementById('curr-trig-dis').value) || 0;
    } else if (currentActiveSection === 'rest') {
        timeVal = parseInt(document.getElementById('time-rest').value);
        volt = 0; curr = 0; voltTrigMax = 0; voltTrigMin = 0; currTrig = 0;
    }

    if (!timeVal || timeVal <= 0) return alert("請輸入有效的「執行時間 (秒)」！");

    const newStep = {
        id: Date.now(), 
        mode: modeText,
        timeSec: timeVal,
        volt: volt,
        curr: curr,
        voltTrigMax: voltTrigMax,
        voltTrigMin: voltTrigMin,
        currTrig: currTrig
    };

    scheduleSteps.push(newStep);
    renderScheduleUI(); 
}

function removeStep(id) {
    scheduleSteps = scheduleSteps.filter(step => step.id !== id);
    renderScheduleUI();
}

function clearSchedule() {
    if (scheduleSteps.length === 0) return;
    if (confirm("確定要清空所有的排程步驟嗎？")) {
        scheduleSteps = [];
        renderScheduleUI();
    }
}

// ====== (覆蓋原本的 renderScheduleUI) ======
function renderScheduleUI() {
    const container = document.getElementById('schedule-container');
    const timeDisplay = document.getElementById('total-time-display');
    
    if (scheduleSteps.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #aaa; margin-top: 50px;">目前沒有任何步驟<br>請在左側設定後點擊「加入排程」</div>';
        timeDisplay.innerText = "總需時間: 0 秒";
        return;
    }

    container.innerHTML = ''; 
    let totalTime = 0;

    scheduleSteps.forEach((step, index) => {
        totalTime += step.timeSec;
        let titleColor = step.mode.includes('C') && !step.mode.includes('D') ? '#007bff' : (step.mode === 'REST' ? '#6f42c1' : '#dc3545');
        
        const card = document.createElement('div');
        card.className = 'step-card';
        card.id = `step-card-${index + 1}`; // 🌟 賦予唯一 ID 讓高光追蹤
        
        let detailsHtml = step.mode !== 'REST' 
            ? `<p>V: ${step.volt} mV | I: ${step.curr} mA</p>
               <p style="font-size: 0.8em; color: #999;">觸發條件: V_max(${step.voltTrigMax}) V_min(${step.voltTrigMin}) I_trig(${step.currTrig})</p>`
            : `<p>靜置記錄中...</p>`;

        // 🌟 加入 上移、下移、編輯、刪除 按鈕
        card.innerHTML = `
            <div class="step-actions">
                ${index > 0 ? `<button onclick="moveStep(${index}, -1)" style="background: #6c757d;">↑</button>` : ''}
                ${index < scheduleSteps.length - 1 ? `<button onclick="moveStep(${index}, 1)" style="background: #6c757d;">↓</button>` : ''}
                <button onclick="editStep(${step.id})" style="background: #ffc107; color: #333;">✏️</button>
                <button onclick="removeStep(${step.id})" style="background: #dc3545;">✖</button>
            </div>
            <h4 style="color: ${titleColor};">Step ${index + 1}: ${step.mode}</h4>
            <p style="font-weight: bold; color: #555;">時間: ${step.timeSec} 秒</p>
            ${detailsHtml}
        `;
        container.appendChild(card);
    });

    timeDisplay.innerText = `總需時間: ${totalTime} 秒`;
}

// ====== (在檔案最下方新增以下四個功能) ======

// 1. 移動步驟 (上移/下移)
function moveStep(index, direction) {
    if (index + direction < 0 || index + direction >= scheduleSteps.length) return;
    const temp = scheduleSteps[index];
    scheduleSteps[index] = scheduleSteps[index + direction];
    scheduleSteps[index + direction] = temp;
    renderScheduleUI();
}

// 2. 編輯步驟 (將卡片資料讀回左側面板，並刪除原卡片)
function editStep(id) {
    const stepIndex = scheduleSteps.findIndex(s => s.id === id);
    if (stepIndex === -1) return;
    const step = scheduleSteps[stepIndex];

    // 切換到對應的面板
    let sectionId = 'rest';
    if (step.mode.includes('C') && !step.mode.includes('D')) sectionId = 'chg';
    else if (step.mode.includes('D')) sectionId = 'dis';
    
    if (typeof activateSection === 'function') activateSection(sectionId);

    // 把數值倒回輸入框
    if (sectionId === 'chg') {
        document.getElementById('time-chg').value = step.timeSec;
        document.getElementById('volt-chg').value = step.volt;
        document.getElementById('curr-chg').value = step.curr;
        document.getElementById('volt-max-chg').value = step.voltTrigMax;
        document.getElementById('curr-trig-chg').value = step.currTrig;
    } else if (sectionId === 'dis') {
        document.getElementById('time-dis').value = step.timeSec;
        document.getElementById('volt-dis').value = step.volt;
        document.getElementById('curr-dis').value = step.curr;
        document.getElementById('volt-min-dis').value = step.voltTrigMin;
        document.getElementById('curr-trig-dis').value = step.currTrig;
    } else if (sectionId === 'rest') {
        document.getElementById('time-rest').value = step.timeSec;
    }

    // 移除原卡片 (讓使用者修改後重新加入)
    removeStep(id);
    alert(`💡 已將 Step ${stepIndex + 1} 的參數退回左側面板！\n請修改參數後，重新點擊「加入排程」，您也可以利用 ↑ ↓ 按鈕調整順序。`);
}

// 3. 畫面高光追蹤
let lastHighlightedStep = -1;
function updateScheduleHighlight(currentStepStr) {
    const currentStep = parseInt(currentStepStr);
    
    // 如果不在執行狀態 (NaN 或 <= 0)，清除所有高光
    if (isNaN(currentStep) || currentStep <= 0) {
        document.querySelectorAll('.step-card').forEach(card => card.classList.remove('active-step'));
        lastHighlightedStep = -1;
        return;
    }

    // 只有在步驟跳轉時才進行 DOM 更新 (節省效能)
    if (currentStep !== lastHighlightedStep) {
        document.querySelectorAll('.step-card').forEach(card => card.classList.remove('active-step'));
        const activeCard = document.getElementById(`step-card-${currentStep}`);
        
        if (activeCard) {
            activeCard.classList.add('active-step');
            // 讓網頁自動捲動，永遠追蹤正在執行的步驟
            activeCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        lastHighlightedStep = currentStep;
    }
}

function runFullSchedule() {
    if (scheduleSteps.length === 0) {
        return alert("排程列表是空的！請先在左側設定參數並加入排程。");
    }

    const display = document.getElementById('output-countdown');
    display.innerText = "正在轉換排程並上傳至機台...";

    let scriptName = "WebAutoRun.json";
    let jsonObj = {
        "Machine": "TPT-B4HCR1515A", // ✅ 更新為你成功範例的機型
        "ProcessName": scriptName
    };

    scheduleSteps.forEach((step, index) => {
        let n = index + 1; 
        let nextN = n + 1; 

        let action = "REST";
        let model = "";
        if (step.mode.includes('C') && !step.mode.includes('D')) {
            action = "CHARGE";
            model = step.mode === "CCC" ? "CC" : "CC-CV"; 
        } else if (step.mode.includes('D')) {
            action = "DISCHARGE";
            model = step.mode === "CCD" ? "CC" : "CC-CV";
        }

        let evSet = 0, evComp = "", evCdt = 0;
        if (step.voltTrigMax > 0) {
            evSet = step.voltTrigMax;
            evComp = ">=";
            evCdt = nextN;
        } else if (step.voltTrigMin > 0) {
            evSet = step.voltTrigMin;
            evComp = "<=";
            evCdt = nextN;
        }

        let ecSet = 0, ecCdt = 0;
        if (step.currTrig > 0) {
            ecSet = step.currTrig;
            ecCdt = nextN; 
        }

        // CC 模式電壓強制設為 0
        let safeVolt = step.volt || 0;
        if (model === "CC") safeVolt = 0; 

        // ✅ 完全依照成功範例的順序與型態寫入 (移除多餘的 0.0)
        jsonObj[`Function-${n}`] = "NA"; 
        jsonObj[`LoopST1-${n}`] = 0;
        jsonObj[`LoopST2-${n}`] = 0;
        jsonObj[`LoopEND1-${n}`] = 0;
        jsonObj[`LoopEND2-${n}`] = 0;
        jsonObj[`Jump-${n}`] = 0;
        jsonObj[`STEPAction-${n}`] = action;
        jsonObj[`STEPModel-${n}`] = model;
        jsonObj[`Vset-${n}`] = safeVolt;
        jsonObj[`Iset-${n}`] = step.curr || 0;
        jsonObj[`Pset-${n}`] = 0;
        jsonObj[`Timeset-${n}`] = step.timeSec * 1000; 
        jsonObj[`RecordTimeset-${n}`] = 1000; 
        jsonObj[`mAhset-${n}`] = 0;
        jsonObj[`mAhCdtset-${n}`] = 0;
        jsonObj[`Whset-${n}`] = 0;
        jsonObj[`WhCdtset-${n}`] = 0;
        jsonObj[`EVset-${n}`] = evSet;
        jsonObj[`EVCompset-${n}`] = evComp;
        jsonObj[`EVCdtset-${n}`] = evCdt;
        jsonObj[`ECset-${n}`] = ecSet;
        jsonObj[`ECCdtset-${n}`] = ecCdt;
        jsonObj[`mdVset-${n}`] = 0;
        jsonObj[`mdVCdtset-${n}`] = 0;
        jsonObj[`ETset-${n}`] = 0;
        jsonObj[`ETCompset-${n}`] = "";
        jsonObj[`ETCdtset-${n}`] = 0;
    });

    let endN = scheduleSteps.length + 1;
    
    // ✅ 結束步序 (END) 依照成功範例精準備齊
    jsonObj[`Function-${endN}`] = "END";
    jsonObj[`LoopST1-${endN}`] = 0;
    jsonObj[`LoopST2-${endN}`] = 0;
    jsonObj[`LoopEND1-${endN}`] = 0;
    jsonObj[`LoopEND2-${endN}`] = 0;
    jsonObj[`Jump-${endN}`] = 0;
    jsonObj[`STEPAction-${endN}`] = "";
    jsonObj[`STEPModel-${endN}`] = "";
    jsonObj[`Vset-${endN}`] = 0;
    jsonObj[`Iset-${endN}`] = 0;
    jsonObj[`Pset-${endN}`] = 0;
    jsonObj[`Timeset-${endN}`] = 0;
    jsonObj[`RecordTimeset-${endN}`] = 0;
    jsonObj[`mAhset-${endN}`] = 0;
    jsonObj[`mAhCdtset-${endN}`] = 0;
    jsonObj[`Whset-${endN}`] = 0;
    jsonObj[`WhCdtset-${endN}`] = 0;
    jsonObj[`EVset-${endN}`] = 0;
    jsonObj[`EVCompset-${endN}`] = "";
    jsonObj[`EVCdtset-${endN}`] = 0;
    jsonObj[`ECset-${endN}`] = 0;
    jsonObj[`ECCdtset-${endN}`] = 0;
    jsonObj[`mdVset-${endN}`] = 0;
    jsonObj[`mdVCdtset-${endN}`] = 0;
    jsonObj[`ETset-${endN}`] = 0;
    jsonObj[`ETCompset-${endN}`] = "";
    jsonObj[`ETCdtset-${endN}`] = 0;

    const flatJson = JSON.stringify(jsonObj);

    const ovp = document.getElementById('ovp-input').value || 12000;
    const uvp = document.getElementById('uvp-input').value || 0;
    const protCmd = `PROGram:PROTection ${ovp},${uvp},1500,0,1500,0,60.0,500,500,500,CH`;

    try {
        // 🌟 SCPI 名稱加上雙引號；JSON 上傳時不加引號 (與成功日誌一致)
        sendCommand(`PROGram:SCRipt:NAME "${scriptName}"`);
        
        setTimeout(() => { sendCommand(`PROGram:SCRipt:UPLoad ${flatJson}`); }, 300);
        setTimeout(() => { sendCommand(protCmd); }, 600);
        setTimeout(() => { sendCommand(`PROGram:STATE:NAME "${scriptName}"`); }, 900);
        
        setTimeout(() => { 
            sendCommand(`PROGram:STATE RUN`); 
            display.innerText = `✅ 排程已成功上傳！機台自動執行中...`;
        }, 1200);

    } catch (error) {
        alert("執行排程發生錯誤：" + error);
        display.innerText = "上傳失敗";
    }
}

function handleLocalScriptUpload(event) {
    const file = event.target.files[0];
    if (!file) return; 

    const display = document.getElementById('output-countdown');
    const reader = new FileReader(); 

    reader.onload = function(e) {
        try {
            const content = e.target.result;
            const jsonObj = JSON.parse(content); 

            let scriptName = jsonObj.ProcessName || "UploadedScript.json";
            if (!scriptName.endsWith('.json')) {
                scriptName += '.json';
                jsonObj.ProcessName = scriptName; 
            }

            const flatJson = JSON.stringify(jsonObj);
            display.innerText = `正在解析並上傳腳本: ${scriptName}...`;
            const protCmd = "PROGram:PROTection 12000,2500,1500,0,1500,0,60.0,500,500,500,CH";

            sendCommand(`PROGram:SCRipt:NAME ${scriptName}`);
            setTimeout(() => { sendCommand(`PROGram:SCRipt:UPLoad ${flatJson}`); }, 300);
            setTimeout(() => { sendCommand(protCmd); }, 600);
            setTimeout(() => { sendCommand(`PROGram:STATE:NAME ${scriptName}`); }, 900);
            setTimeout(() => { 
                sendCommand(`PROGram:STATE RUN`); 
                display.innerText = `腳本 [${scriptName}] 已成功上傳並由機台自動執行中！`;
            }, 1200);

        } catch (error) {
            alert("❌ 腳本解析失敗！請確保上傳的檔案是語法正確的 JSON 格式。\n詳細錯誤: " + error);
            display.innerText = "上傳失敗";
        }
        event.target.value = '';
    };
    reader.readAsText(file);
}