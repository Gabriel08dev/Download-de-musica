const form = document.querySelector('#download-form');
const result = document.querySelector('#result');
const status = document.querySelector('#status');
const progress = document.querySelector('#progress');
const message = document.querySelector('#message');
const files = document.querySelector('#files');
const downloadAll = document.querySelector('#download-all');
const button = form.querySelector('button');

async function apiRequest(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Falha na requisição');
  return data;
}

function showJob(job) {
  status.textContent = job.title || job.status.replaceAll('_', ' ');
  progress.value = job.percent;
  message.textContent = job.error || `${job.status.replaceAll('_', ' ')} · ${job.percent}%`;
  downloadAll.hidden = !job.files.length || !['concluido', 'erro'].includes(job.status);
  downloadAll.href = `/api/jobs/${job.id}/archive`;
  files.replaceChildren();
  for (const name of job.files) {
    const link = document.createElement('a');
    link.href = `/api/jobs/${job.id}/files/${encodeURIComponent(name)}`;
    link.textContent = name;
    link.download = name;
    const item = document.createElement('li');
    item.append(link);
    files.append(item);
  }
}

async function watch(id, failures = 0) {
  try {
    const job = await apiRequest(`/api/jobs/${id}`);
    showJob(job);
    if (job.status === 'concluido' || job.status === 'erro') {
      button.disabled = false;
      return;
    }
    setTimeout(() => watch(id), 1500);
  } catch (error) {
    message.textContent = error.message;
    if (failures < 5) {
      setTimeout(() => watch(id, failures + 1), 3000);
    } else {
      button.disabled = false;
    }
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  button.disabled = true;
  result.hidden = false;
  status.textContent = 'Enviando';
  progress.value = 0;
  message.textContent = '';
  files.replaceChildren();
  downloadAll.hidden = true;
  try {
    const job = await apiRequest('/api/jobs', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        url: document.querySelector('#url').value,
        playlist: document.querySelector('#playlist').checked,
      }),
    });
    watch(job.id);
  } catch (error) {
    message.textContent = error.message;
    button.disabled = false;
  }
});

apiRequest('/api/recent-job').then((job) => {
  if (!result.hidden) return;
  result.hidden = false;
  if (['concluido', 'erro'].includes(job.status)) showJob(job);
  else watch(job.id);
}).catch(() => {});
