import api from './client';

export const login = (identifier, password) =>
  api.post('/auth/login', { identifier, password });
