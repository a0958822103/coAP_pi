// 1. 網頁載入即開始抓取機台資料 (每秒一次)
fetchChargerData();
setInterval(fetchChargerData, 1000);

// 2. 利用資料驅動的方式，優雅地綁定所有 Input 動態文字事件
const inputConfigs = [
    { id: 'volt-chg', btn: 'volt-btn-chg', template: '設定充電電壓為 ${value} mV' },
    { id: 'curr-chg', btn: 'curr-btn-chg', template: '設定充電電流為 ${value} mA' },
    { id: 'volt-max-chg', btn: 'volt-max-btn', template: '設定結束電壓最大為 ${value} mV' },
    { id: 'curr-trig-chg', btn: 'curr-trig-btn-chg', template: '設定結束電流為 ${value} mA' },
    
    { id: 'volt-dis', btn: 'volt-btn-dis', template: '設定放電電壓為 ${value} mV' },
    { id: 'curr-dis', btn: 'curr-btn-dis', template: '設定放電電流為 ${value} mA' },
    { id: 'volt-min-dis', btn: 'volt-min-btn', template: '設定結束電壓最小為 ${value} mV' },
    { id: 'curr-trig-dis', btn: 'curr-trig-btn-dis', template: '設定結束電流為 ${value} mA' },
    
    { id: 'ovp-input', btn: 'volt-prot-btn', template: '設定過/低電壓保護為 ${value} mV' }
];

// 執行綁定迴圈
inputConfigs.forEach(conf => {
    setupInputListener(conf.id, conf.btn, conf.template);
});