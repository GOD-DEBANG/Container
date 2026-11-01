// Interactive Client App for PULSE & VDC Hub

let cachedDatasets = [];

// 1. Fetch Stored Datasets
async function fetchDatasets() {
  try {
    const res = await fetch('/api/v1/datasets');
    const data = await res.json();
    const tbody = document.getElementById('datasetTableBody');
    const trainSelect = document.getElementById('trainDatasetSelect');
    const inferSelect = document.getElementById('inferDatasetSelect');

    if (!data.payload?.datasets?.length) {
      tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 2rem;">No synthesized datasets found yet. Create one above!</td></tr>';
      return;
    }

    cachedDatasets = data.payload.datasets;

    // Update Datasets Table
    tbody.innerHTML = cachedDatasets.map(d => `
      <tr>
        <td style="font-weight: 500;">
          <span style="color: var(--accent-2); margin-right: 0.5rem;">●</span>${d.name}
        </td>
        <td style="color: var(--text-muted);">${(d.size_bytes / 1024).toFixed(1)} KB</td>
        <td>
          <a class="link-btn" href="${d.download_csv}" download>📥 CSV</a>
          <a class="link-btn" href="${d.download_json}" download>📥 JSON</a>
        </td>
      </tr>
    `).join('');

    // Update Dropdowns for Training & Inference
    const optionsHtml = cachedDatasets.map(d => `<option value="${d.name}">${d.name}</option>`).join('');
    if (trainSelect) trainSelect.innerHTML = optionsHtml;
    if (inferSelect) inferSelect.innerHTML = optionsHtml;

  } catch (err) {
    console.error('Failed to fetch datasets:', err);
  }
}

// 2. Synthesize Dataset
document.getElementById('genForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('genBtn');
  const msg = document.getElementById('genMsg');
  btn.disabled = true;
  btn.innerText = 'Synthesizing...';
  msg.style.display = 'none';

  try {
    const res = await fetch('/api/v1/datasets/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dataset_name: document.getElementById('name').value,
        modality: document.getElementById('modality').value,
        target_records: parseInt(document.getElementById('records').value),
        anomaly_ratio: parseFloat(document.getElementById('anomaly').value),
        drift_factor: parseFloat(document.getElementById('drift').value),
      })
    });
    const result = await res.json();
    msg.style.display = 'block';

    if (result.payload?.records_generated) {
      msg.className = 'alert alert-success';
      msg.innerHTML = `✓ Successfully generated <b>${result.payload.records_generated}</b> records for <b>${result.payload.dataset_name}</b>!`;
      fetchDatasets();
    } else {
      msg.className = 'alert alert-danger';
      msg.innerHTML = `Error: ${result.message || 'Generation failed'}`;
    }
  } catch (err) {
    msg.style.display = 'block';
    msg.className = 'alert alert-danger';
    msg.innerHTML = `Failed: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.innerText = '⚡ Synthesize Dataset';
  }
});

// 3. Train ML Model
document.getElementById('trainForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('trainBtn');
  const msg = document.getElementById('trainMsg');
  btn.disabled = true;
  btn.innerText = 'Training Neural Model...';
  msg.style.display = 'none';

  try {
    const res = await fetch('/api/v1/ml/train', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dataset_name: document.getElementById('trainDatasetSelect').value,
        epochs: parseInt(document.getElementById('trainEpochs').value),
        learning_rate: parseFloat(document.getElementById('trainLr').value),
      })
    });
    const result = await res.json();
    msg.style.display = 'block';

    if (result.payload?.final_accuracy !== undefined) {
      msg.className = 'alert alert-success';
      msg.innerHTML = `
        <div>
          <b>🎯 Model Trained Successfully!</b><br>
          Accuracy: <b>${(result.payload.final_accuracy * 100).toFixed(2)}%</b> | Val Loss: <b>${result.payload.final_val_loss.toFixed(4)}</b><br>
          <span style="font-size:0.8rem; color: #a7f3d0;">Weights saved: ${result.payload.weights_path}</span>
        </div>
      `;
    } else {
      msg.className = 'alert alert-danger';
      msg.innerHTML = `Error: ${result.message || 'Training failed'}`;
    }
  } catch (err) {
    msg.style.display = 'block';
    msg.className = 'alert alert-danger';
    msg.innerHTML = `Failed: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.innerText = '🧠 Train Neural Model';
  }
});

// 4. Run Realtime ML Inference
document.getElementById('inferForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('inferBtn');
  const resBox = document.getElementById('inferResult');
  btn.disabled = true;

  const features = [
    parseFloat(document.getElementById('f_cpu').value),
    parseFloat(document.getElementById('f_mem').value),
    parseFloat(document.getElementById('f_io').value),
    parseFloat(document.getElementById('f_lat').value),
    parseFloat(document.getElementById('f_queue').value),
  ];

  try {
    const res = await fetch('/api/v1/ml/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dataset_name: document.getElementById('inferDatasetSelect').value,
        features: [features]
      })
    });
    const result = await res.json();
    resBox.style.display = 'block';

    if (result.payload?.predictions) {
      const isAnomaly = result.payload.predictions[0] === 1;
      const probs = result.payload.probabilities[0];
      const conf = (Math.max(...probs) * 100).toFixed(1);

      resBox.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div>
            <span class="prediction-badge ${isAnomaly ? 'badge-anomaly' : 'badge-normal'}">
              ${isAnomaly ? '⚠️ ANOMALY DETECTED' : '✓ NORMAL EXECUTION'}
            </span>
          </div>
          <div style="color: var(--text-muted); font-size: 0.9rem;">
            Confidence: <b>${conf}%</b>
          </div>
        </div>
        <div style="margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-muted);">
          Probabilities: [Normal: ${(probs[0]*100).toFixed(1)}%, Anomaly: ${(probs[1]*100).toFixed(1)}%]
        </div>
      `;
    } else {
      resBox.className = 'alert alert-danger';
      resBox.innerHTML = `Inference failed: ${result.message}`;
    }
  } catch (err) {
    resBox.style.display = 'block';
    resBox.className = 'alert alert-danger';
    resBox.innerHTML = `Failed: ${err.message}`;
  } finally {
    btn.disabled = false;
  }
});

// Initial boot
fetchDatasets();

