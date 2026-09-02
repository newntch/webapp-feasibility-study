import { Router } from 'express';
import { randomBytes } from 'node:crypto';
import bcrypt from 'bcryptjs';
import {
  cookieOptions,
  expiredCookieHeader,
  getCookie,
  isValidEmail,
  normalizeEmail,
  sendHtmlError
} from './httpHelpers.js';

export function createAuthRouter({ config, appStorage, otpDelivery, fetchImpl, sessions }) {
  const router = Router();
  const oauthCookieName = config.auth.oauthState.cookieName;
  const otpTtlMs = config.auth.otp.ttlMinutes * 60 * 1000;
  const maxOtpAttempts = config.auth.otp.maxAttempts;

  router.get('/me', sessions.requireUser, (request, response) => {
    response.json({ user: request.user });
  });

  router.post('/login', async (request, response) => {
    const email = normalizeEmail(request.body?.email);
    const password = String(request.body?.password || '');
    const user = await appStorage.getUserByEmail(email);

    if (!user || !(await bcrypt.compare(password, user.passwordHash))) {
      return response.status(401).json({ error: 'Invalid email or password' });
    }

    const updated = await appStorage.updateUser({
      ...user,
      lastLoginAt: new Date().toISOString()
    });
    const publicUser = createPublicUser(updated, 'credentials');
    await sessions.issueSession(response, publicUser, request);
    return response.json({ user: publicUser });
  });

  router.post('/signup/request', async (request, response) => {
    const email = normalizeEmail(request.body?.email);
    const name = String(request.body?.name || '').trim();
    const password = String(request.body?.password || '');

    if (!isValidEmail(email) || !name || password.length < 8) {
      return response.status(400).json({
        error: 'Name, valid email, and password with at least 8 characters are required.'
      });
    }
    if (await appStorage.getUserByEmail(email)) {
      return response.status(409).json({ error: 'A user with this email already exists.' });
    }

    const otp = createOtp();
    await appStorage.createPendingOtp({
      purpose: 'signup',
      email,
      otpHash: await bcrypt.hash(otp, 10),
      attempts: 0,
      expiresAt: new Date(Date.now() + otpTtlMs).toISOString(),
      payload: { name, passwordHash: await bcrypt.hash(password, 12) }
    });
    const delivery = await otpDelivery.sendOtpEmail({
      to: email,
      subject: 'Cohort Lens account verification',
      otp,
      intro: 'Use this OTP to finish creating your Cohort Lens account.',
      ttlMinutes: config.auth.otp.ttlMinutes
    });
    return response.json({ message: signupOtpMessage(delivery) });
  });

  router.post('/signup/confirm', async (request, response) => {
    const email = normalizeEmail(request.body?.email);
    const otp = String(request.body?.otp || '').trim();
    const pending = await appStorage.getPendingOtp('signup', email);
    const validation = await validatePendingOtp(pending, otp);
    if (!validation.ok) return response.status(validation.status).json({ error: validation.error });

    if (await appStorage.getUserByEmail(email)) {
      await appStorage.deletePendingOtp('signup', email);
      return response.status(409).json({ error: 'A user with this email already exists.' });
    }

    const user = await appStorage.createUser({
      id: `user-${randomBytes(8).toString('hex')}`,
      email,
      name: pending.payload?.name,
      role: 'researcher',
      provider: 'credentials',
      passwordHash: pending.payload?.passwordHash,
      active: true
    });
    await appStorage.deletePendingOtp('signup', email);
    const publicUser = createPublicUser(user, 'credentials');
    await sessions.issueSession(response, publicUser, request);
    return response.status(201).json({ user: publicUser });
  });

  router.post('/password/request', async (request, response) => {
    const email = normalizeEmail(request.body?.email);
    const user = await appStorage.getUserByEmail(email);

    if (user) {
      const otp = createOtp();
      await appStorage.createPendingOtp({
        purpose: 'password',
        email,
        userId: user.id,
        otpHash: await bcrypt.hash(otp, 10),
        attempts: 0,
        expiresAt: new Date(Date.now() + otpTtlMs).toISOString(),
        payload: {}
      });
      const delivery = await otpDelivery.sendOtpEmail({
        to: email,
        subject: 'Cohort Lens password reset OTP',
        otp,
        intro: 'Use this OTP to reset your Cohort Lens password.',
        ttlMinutes: config.auth.otp.ttlMinutes
      });
      if (delivery.mode === 'console') {
        console.warn('[PASSWORD RESET OTP] SMTP delivery was unavailable; OTP was written to the server console.');
      }
    }
    return response.json({ message: 'If the email exists, an OTP has been sent.' });
  });

  router.post('/password/confirm', async (request, response) => {
    const email = normalizeEmail(request.body?.email);
    const otp = String(request.body?.otp || '').trim();
    const password = String(request.body?.password || '');
    if (password.length < 8) {
      return response.status(400).json({ error: 'Password must be at least 8 characters.' });
    }

    const pending = await appStorage.getPendingOtp('password', email);
    const validation = await validatePendingOtp(pending, otp);
    if (!validation.ok) return response.status(validation.status).json({ error: validation.error });

    const user = await appStorage.getUserByEmail(email);
    if (!user) {
      await appStorage.deletePendingOtp('password', email);
      return response.status(404).json({ error: 'User not found.' });
    }
    await appStorage.updateUser({
      ...user,
      passwordHash: await bcrypt.hash(password, 12),
      passwordUpdatedAt: new Date().toISOString()
    });
    await appStorage.deletePendingOtp('password', email);
    return response.json({ message: 'Password updated. You can now sign in.' });
  });

  router.post('/logout', async (request, response) => {
    const sessionId = getCookie(request, sessions.cookieName);
    if (sessionId) await appStorage.deleteSession(sessionId);
    response.append('set-cookie', expiredCookieHeader(config, sessions.cookieName));
    return response.status(204).end();
  });

  router.get('/google', (request, response) => {
    const clientId = config.auth.google.clientId;
    if (!clientId) {
      return sendHtmlError(response, 500, 'Google OAuth is not configured. Update auth.google in config/app.config.json.');
    }

    const state = randomId();
    const authUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
    authUrl.searchParams.set('client_id', clientId);
    authUrl.searchParams.set('redirect_uri', config.auth.google.redirectUri);
    authUrl.searchParams.set('response_type', 'code');
    authUrl.searchParams.set('scope', 'openid email profile');
    authUrl.searchParams.set('state', state);
    authUrl.searchParams.set('prompt', 'select_account');
    response.cookie(
      oauthCookieName,
      state,
      cookieOptions(config, config.auth.oauthState.maxAgeSeconds)
    );
    return response.redirect(authUrl.toString());
  });

  router.get('/google/callback', async (request, response) => {
    const expectedState = getCookie(request, oauthCookieName);
    const { state, code } = request.query;
    if (!expectedState || !state || expectedState !== state || !code) {
      return sendHtmlError(response, 400, 'Invalid Google OAuth callback state.');
    }

    const tokenResponse = await fetchImpl('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        code: String(code),
        client_id: config.auth.google.clientId,
        client_secret: config.auth.google.clientSecret,
        redirect_uri: config.auth.google.redirectUri,
        grant_type: 'authorization_code'
      })
    });
    if (!tokenResponse.ok) return sendHtmlError(response, 502, 'Google token exchange failed.');

    const token = await tokenResponse.json();
    const profileResponse = await fetchImpl('https://www.googleapis.com/oauth2/v3/userinfo', {
      headers: { authorization: `Bearer ${token.access_token}` }
    });
    if (!profileResponse.ok) return sendHtmlError(response, 502, 'Google user profile request failed.');

    const profile = await profileResponse.json();
    if (!profile.email_verified) return sendHtmlError(response, 403, 'Google email must be verified.');
    const allowedEmails = config.auth.google.allowedEmails;
    if (allowedEmails.length > 0 && !allowedEmails.includes(normalizeEmail(profile.email))) {
      return sendHtmlError(response, 403, 'Google account is not allowed for this app.');
    }

    const storedUser = await appStorage.upsertGoogleUser({
      googleSub: profile.sub,
      email: profile.email,
      name: profile.name || profile.email
    });
    const user = createPublicUser(storedUser, 'google');
    response.append('set-cookie', expiredCookieHeader(config, oauthCookieName));
    await sessions.issueSession(response, user, request);
    return response.redirect('/');
  });

  async function validatePendingOtp(pending, otp) {
    if (!pending) return { ok: false, status: 400, error: 'OTP request not found or expired.' };
    if (Date.now() > new Date(pending.expiresAt).getTime()) {
      return { ok: false, status: 400, error: 'OTP expired. Request a new OTP.' };
    }
    if (pending.attempts >= maxOtpAttempts) {
      return { ok: false, status: 429, error: 'Too many OTP attempts. Request a new OTP.' };
    }

    pending.attempts += 1;
    const valid = await bcrypt.compare(otp, pending.otpHash);
    await appStorage.updatePendingOtp(pending);
    if (!valid) return { ok: false, status: 401, error: 'Invalid OTP.' };
    return { ok: true };
  }

  return router;
}

function createPublicUser(user, provider) {
  return {
    id: user.id,
    email: user.email,
    name: user.name || user.email,
    provider,
    role: user.role || 'researcher'
  };
}

function createOtp() {
  return String(Math.floor(100000 + Math.random() * 900000));
}

function randomId() {
  return randomBytes(32).toString('base64url');
}

function signupOtpMessage(delivery) {
  if (delivery.mode === 'console') {
    return delivery.warning || 'OTP delivery is using the server console for local testing.';
  }
  return 'OTP sent to email. Confirm OTP to create the user.';
}
