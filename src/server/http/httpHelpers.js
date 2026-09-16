export function getCookie(request, name) {
  const raw = request.headers.cookie || '';
  const encoded = raw
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`))
    ?.slice(name.length + 1);

  if (encoded === undefined) return undefined;
  try {
    return decodeURIComponent(encoded);
  } catch {
    return encoded;
  }
}

export function cookieOptions(config, maxAgeSeconds) {
  return {
    httpOnly: true,
    maxAge: maxAgeSeconds * 1000,
    path: '/',
    sameSite: 'lax',
    secure: config.server.cookieSecure
  };
}

export function expiredCookieHeader(config, name) {
  const parts = [`${name}=`, 'Path=/', 'HttpOnly', 'SameSite=Lax', 'Max-Age=0'];
  if (config.server.cookieSecure) parts.push('Secure');
  return parts.join('; ');
}

export function escapeHtml(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

export function sendHtmlError(response, status, message) {
  response
    .status(status)
    .type('html')
    .send(`<p>${escapeHtml(message)}</p><p><a href="/login.html">Back to login</a></p>`);
}

export function normalizeEmail(value) {
  return String(value || '').trim().toLowerCase();
}

export function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
