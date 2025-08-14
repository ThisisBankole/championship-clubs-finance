import axios from 'axios';

export const API_BASE_URL = 'https://football-finance-api.delightfulflower-2aa1e200.westeurope.azurecontainerapps.io';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const clubsApi = {
  getAllClubs: () => api.get('/api/v1/clubs'),
  getClubByName: (clubName) => api.get(`/api/v1/clubs/${clubName}`),
  
};