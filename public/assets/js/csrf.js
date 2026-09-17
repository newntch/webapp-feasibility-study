export function csrfHeaders(extra = {}) {
  const cookie = document.cookie.split('; ')
    .find((part) => part.startsWith('csrftoken='));
  const token = cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : '';
  return { ...extra, 'X-CSRFToken': token };
}
