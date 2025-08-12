import axios from 'axios';

export const API_BASE_URL = 'http://football-finance-api.westeurope.azurecontainer.io:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const clubsApi = {
  getAllClubs: () => api.get('/api/v1/clubs'),
  getClubByName: (clubName) => api.get(`/api/v1/clubs/${clubName}`),
};