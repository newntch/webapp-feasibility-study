import { randomBytes } from 'node:crypto';
import { cookieOptions, getCookie } from './httpHelpers.js';

export function createSessionHelpers({ config, appStorage }) {
  const cookieName = config.auth.session.cookieName;

  async function getSessionUser(request) {
    const sessionId = getCookie(request, cookieName);
    if (!sessionId) return null;
    const session = await appStorage.getSession(sessionId);
    return session?.user || null;
  }

  async function requireUser(request, response, next) {
    try {
      const user = await getSessionUser(request);
      if (!user) return response.status(401).json({ error: 'Not authenticated' });
      request.user = user;
      return next();
    } catch (error) {
      return next(error);
    }
  }

  async function issueSession(response, user, request) {
    const sessionId = randomBytes(32).toString('base64url');
    const maxAgeSeconds = config.auth.session.maxAgeSeconds;
    const expiresAt = new Date(Date.now() + maxAgeSeconds * 1000).toISOString();
    await appStorage.createSession({
      sessionId,
      userId: user.id,
      expiresAt,
      userAgent: request.headers['user-agent'] || '',
      ipAddress: request.socket.remoteAddress || ''
    });
    response.cookie(cookieName, sessionId, cookieOptions(config, maxAgeSeconds));
  }

  return { cookieName, getSessionUser, issueSession, requireUser };
}
