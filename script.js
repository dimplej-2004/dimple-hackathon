// drag and drop upload handling
let dropArea = document.getElementById('drop-area');
let fileElem = document.getElementById('fileElem');
let fileInfo = document.getElementById('file-info');
let fileNameSpan = document.getElementById('file-name');
let txCountSpan = document.getElementById('tx-count');

;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
  dropArea.addEventListener(eventName, preventDefaults, false)
});

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

;['dragenter', 'dragover'].forEach(eventName => {
  dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false)
});

;['dragleave', 'drop'].forEach(eventName => {
  dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false)
});

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const header = lines[0].split(',').map(h => h.trim());
  const data = [];
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue;
    const cols = lines[i].split(',');
    const obj = {};
    header.forEach((h, idx) => {
      let val = cols[idx] ? cols[idx].trim() : '';
      if (h === 'amount') val = parseFloat(val);
      else if (h === 'arrival_time' || h === 'max_delay' || h === 'priority') val = parseInt(val, 10);
      obj[h] = val;
    });
    data.push(obj);
  }
  return data;
}

function renderJson(data) {
  const output = document.getElementById('json-output');
  output.textContent = JSON.stringify(data, null, 2);
}

function renderChart(data) {
  // count by priority
  const counts = {};
  data.forEach(tx => {
    const p = tx.priority || 0;
    counts[p] = (counts[p] || 0) + 1;
  });
  const labels = Object.keys(counts).sort((a,b)=>a-b);
  const values = labels.map(l => counts[l]);
  const ctx = document.getElementById('chart').getContext('2d');
  if (window.txChart) {
    window.txChart.data.labels = labels;
    window.txChart.data.datasets[0].data = values;
    window.txChart.update();
  } else {
    window.txChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Transactions per priority',
          backgroundColor: '#4a90e2',
          data: values
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true }
        }
      }
    });
  }
}

function renderSummary(data) {
  const summaryDiv = document.getElementById('summary');
  const total = data.length;
  const totalAmount = data.reduce((acc, tx) => acc + (tx.amount||0), 0);
  const avgAmount = total ? (totalAmount / total).toFixed(2) : 0;
  summaryDiv.innerHTML = `
    <p><strong>Total transactions:</strong> ${total}</p>
    <p><strong>Total amount:</strong> ${totalAmount.toFixed(2)}</p>
    <p><strong>Average amount:</strong> ${avgAmount}</p>
  `;
}

let currentTxs = [];

function handleFiles(files) {
  if (!files.length) return;
  const file = files[0];
  fileNameSpan.textContent = file.name;
  const reader = new FileReader();
  reader.onload = function(e) {
    const text = e.target.result;
    const txs = parseCsv(text);
    currentTxs = txs;
    txCountSpan.textContent = txs.length;
    fileInfo.classList.remove('hidden');
    // show results
    document.getElementById('results-section').classList.remove('hidden');
    renderJson(txs);
    renderSummary(txs);
    renderChart(txs);
  };
  reader.readAsText(file);
}

// toggle compact mode
const toggleBtn = document.getElementById('toggle-json-btn');
toggleBtn.addEventListener('click', () => {
  const results = document.getElementById('results-section');
  results.classList.toggle('compact');
  toggleBtn.textContent = results.classList.contains('compact') ? 'Expand JSON view' : 'Toggle JSON view';
});

// scheduling utilities
class Channel {
  constructor(channel_id, latency, capacity, fee) {
    this.channel_id = channel_id;
    this.latency = latency;
    this.capacity = capacity;
    this.fee = fee;
    this.schedule = [];
    this.outages = [];
  }
  _can_schedule_at(start) {
    const end = start + this.latency;
    for (const [o_start, o_end] of this.outages) {
      if (o_start < end && start < o_end) return false;
    }
    let concurrent = 0;
    for (const [s, e] of this.schedule) {
      if (s < end && start < e) {
        concurrent += 1;
        if (concurrent >= this.capacity) return false;
      }
    }
    return true;
  }
  earliest_available_start(arrival, max_delay) {
    const deadline = arrival + max_delay;
    for (let t = arrival; t <= deadline; t++) {
      if (this._can_schedule_at(t)) return t;
    }
    return -1;
  }
  add_transaction(start) {
    this.schedule.push([start, start + this.latency]);
  }
}

function buildChannels() {
  return [
    new Channel('FAST', 1, 2, 5),
    new Channel('STANDARD', 3, 3, 2),
    new Channel('BULK', 6, 5, 1),
  ];
}

function computeDelayPenalty(amount, delay) {
  return 0.001 * amount * delay;
}
function computeFailureCost(tx) {
  return 0.5 * tx.amount;
}
function computeCostForAssignment(tx, start, fee) {
  const delay = start - tx.arrival_time;
  return fee + computeDelayPenalty(tx.amount, delay);
}

function scheduleTransactions(txs) {
  const channels = buildChannels();
  const ordered = txs.slice().sort((a,b) => {
    if (a.arrival_time !== b.arrival_time) return a.arrival_time - b.arrival_time;
    return b.priority - a.priority;
  });
  const assignments = [];
  let total_cost = 0;
  for (const tx of ordered) {
    let bestOption = null;
    let bestCost = Infinity;
    let chosen = null;
    for (const ch of channels) {
      const start = ch.earliest_available_start(tx.arrival_time, tx.max_delay);
      if (start === -1) continue;
      const cost = computeCostForAssignment(tx, start, ch.fee);
      if (
        bestOption === null ||
        start < bestOption.start_time ||
        (start === bestOption.start_time && cost < bestCost)
      ) {
        bestCost = cost;
        bestOption = {tx_id: tx.tx_id, channel_id: ch.channel_id, start_time: start, channel_fee: ch.fee};
        chosen = ch;
      }
    }
    if (chosen) {
      chosen.add_transaction(bestOption.start_time);
      assignments.push(bestOption);
      total_cost += bestCost;
    } else {
      total_cost += computeFailureCost(tx);
      assignments.push({tx_id: tx.tx_id, channel_id: null, start_time: null, channel_fee: 0});
    }
  }
  return {assignments, total_cost};
}

function renderOptTable(assignments) {
  const tbody = document.querySelector('#opt-table tbody');
  tbody.innerHTML = '';
  assignments.forEach(a => {
    const tr = document.createElement('tr');
    const ch = a.channel_id || 'NONE';
    tr.innerHTML = `<td>${a.tx_id}</td><td>${ch}</td><td>${a.start_time === null ? '-' : a.start_time}</td><td>${a.channel_fee.toFixed(2)}</td>`;
    tbody.appendChild(tr);
  });
}

function renderOptSummary(assignments, totalCost) {
  const summaryDiv = document.getElementById('opt-summary');
  const total = assignments.length;
  const byChannel = {};
  assignments.forEach(a => {
    const ch = a.channel_id || 'NONE';
    byChannel[ch] = (byChannel[ch] || 0) + 1;
  });
  let html = `<p><strong>Total transactions:</strong> ${total}</p>`;
  html += '<ul>';
  for (const ch in byChannel) {
    html += `<li>${ch}: ${byChannel[ch]}</li>`;
  }
  html += '</ul>';
  summaryDiv.innerHTML = html;
}

function runOptimization() {
  if (!currentTxs.length) {
    alert('No transactions loaded. Upload a CSV first.');
    return;
  }
  const result = scheduleTransactions(currentTxs);
  document.getElementById('opt-results-section').classList.remove('hidden');
  renderOptSummary(result.assignments, result.total_cost);
  renderOptTable(result.assignments);
  document.getElementById('opt-cost').textContent = result.total_cost.toFixed(2);
}

// connect button interactions

document.getElementById('upload-btn').addEventListener('click', () => fileElem.click());
document.getElementById('run-btn').addEventListener('click', runOptimization);
document.getElementById('start-opt-btn').addEventListener('click', runOptimization);