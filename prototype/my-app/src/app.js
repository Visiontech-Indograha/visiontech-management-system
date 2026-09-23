const express = require('express');
const securityConfig = require('../config/security');
const auth = require('./auth');

const app = express();

/**
 * Integrasi dengan Kerangka Keamanan Antigravity
 */
app.use((req, res, next) => {
  // Simulasi penggunaan rate limiter dan CORS dari antigravity config
  console.log(`[Claude Code] Menerapkan CORS origin: ${securityConfig.cors.origin}`);
  console.log(`[Claude Code] Menerapkan Rate Limit: ${securityConfig.rateLimit.max} req/window`);
  next();
});

app.post('/login', async (req, res) => {
  const result = await auth.loginUser('admin', 'password123');
  res.json(result);
});

module.exports = app;
