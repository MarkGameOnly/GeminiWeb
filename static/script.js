document.getElementById('gen-form').onsubmit = async function(e) {
  e.preventDefault();
  const prompt = document.getElementById('prompt').value;
  const user_id = document.getElementById('user_id').value;
  const resDiv = document.getElementById('result');
  resDiv.innerHTML = '⏳ Генерация...';

  const formData = new FormData();
  formData.append('prompt', prompt);
  formData.append('user_id', user_id);

  const resp = await fetch('/api/generate-image', {
    method: 'POST',
    body: formData
  });
  const text = await resp.text();
  resDiv.innerHTML = text;

  loadGallery();
};

async function loadGallery() {
  const galleryDiv = document.getElementById('gallery');
  galleryDiv.innerHTML = 'Загрузка...';
  const resp = await fetch('/api/gallery');
  const html = await resp.text();
  galleryDiv.innerHTML = html;
}

window.onload = loadGallery;
