function getCsrfToken() {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';').map(c => c.trim());
  for (const c of cookies) {
    if (c.startsWith(name + '=')) return decodeURIComponent(c.split('=')[1]);
  }
  return '';
}

const form = document.getElementById('chat-form');
const messages = document.getElementById('messages');
const promptInput = document.getElementById('prompt');

function appendMessage(text, who='assistant'){
  const el = document.createElement('div');
  el.className = 'message ' + (who==='user' ? 'user' : 'assistant');
  el.textContent = text;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

form.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const prompt = promptInput.value.trim();
  if(!prompt) return;
  appendMessage(prompt, 'user');
  promptInput.value = '';
  appendMessage('Thinking...', 'assistant');
  try{
    const res = await fetch('/api/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ prompt }),
      credentials: 'same-origin'
    });
    const data = await res.json();
    // remove the 'Thinking...' placeholder
    const last = messages.querySelectorAll('.message.assistant');
    if(last.length) last[last.length-1].remove();
    if(data.reply){
      appendMessage(data.reply, 'assistant');
    } else if(data.error){
      appendMessage('Error: ' + data.error, 'assistant');
    }
  }catch(err){
    appendMessage('Network error', 'assistant');
  }
});
