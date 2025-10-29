// File upload and processing logic for TQ GenAI Chat
export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch('/upload', {
    method: 'POST',
    body: formData
  });
  return res.json();
}
