async function apiGet(url) {
  const response = await fetch(API + url);
  return response.json();
}

async function apiPost(url, body) {
  const options = { method: 'POST' };
  if (body instanceof FormData) {
    options.body = body;
  } else {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(body);
  }
  return fetch(API + url, options);
}
