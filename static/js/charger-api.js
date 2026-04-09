// 負責抓取與發送資料
function fetchChargerData() {
    fetch('/api/charger/data')
        .then(response => { if (!response.ok) throw new Error("設備離線"); return response.json(); })
        .then(data => {
            document.getElementById('dev-status').innerText = "連線正常 🟢";
            document.getElementById('dev-status').style.color = "green";
            document.getElementById('val-volt').innerText = data.volt;
            document.getElementById('val-curr').innerText = data.curr;
            document.getElementById('val-dis-mah').innerText = data.discharge_mah;
            document.getElementById('val-chg-mah').innerText = data.charge_mah;
            document.getElementById('val-power').innerText = data.power;
            document.getElementById('val-step').innerText = data.step;
            document.getElementById('val-mode').innerText = data.mode;

            if (typeof updateScheduleHighlight === 'function') {
                updateScheduleHighlight(data.step);
            }
        });
}

function sendCommand(cmd) {
    fetch(`/api/charger/cmd?cmd=${encodeURIComponent(cmd)}`)
        .then(res => res.json())
        .catch(error => { console.error(`指令發送失敗！\n錯誤訊息: ${error}`); });
}

