import axios from 'axios';

// Frontend caching system
const cache = new Map();
const CACHE_TIME = 5 * 60 * 1000; 
const MAX_CACHE_SIZE = 50; 

// Cache utilities
const getCachedData = (key) => {
  const cached = cache.get(key);
  if (cached && Date.now() - cached.timestamp < CACHE_TIME) {
    console.log(`🚀 Cache HIT: ${key}`);
    return cached.data;
  }
  if (cached) {
    cache.delete(key); // Remove expired cache
  }
  return null;
};

const setCachedData = (key, data) => {
  // Prevent cache from growing too large
  if (cache.size >= MAX_CACHE_SIZE) {
    const firstKey = cache.keys().next().value;
    cache.delete(firstKey);
  }
  
  cache.set(key, { data, timestamp: Date.now() });
  console.log(`💾 Cache SET: ${key}`);
};

// Clear cache when needed
export const clearCache = () => {
  cache.clear();
  console.log('🧹 Cache cleared');
};

export const API_BASE_URL = 'https://football-finance-api.delightfulflower-2aa1e200.westeurope.azurecontainerapps.io';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Add response interceptor for debugging
api.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error(`❌ API Error: ${error.config?.url}`, error.message);
    return Promise.reject(error);
  }
);

export const clubsApi = {
  getAllClubs: async () => {
    const cacheKey = 'all-clubs';
    const cached = getCachedData(cacheKey);
    if (cached) return cached;
    
    const response = await api.get('/api/v1/clubs');
    setCachedData(cacheKey, response);
    return response;
  },
  
  getClubByName: async (clubName) => {
    const cacheKey = `club-${clubName.toLowerCase()}`;
    const cached = getCachedData(cacheKey);
    if (cached) return cached;
    
    const response = await api.get(`/api/v1/clubs/${clubName}`);
    setCachedData(cacheKey, response);
    return response;
  },
};

export { clubDescriptionsApi } from './cms';

// Cache stats for debugging
export const getCacheStats = () => {
  return {
    size: cache.size,
    keys: Array.from(cache.keys()),
    maxSize: MAX_CACHE_SIZE,
    cacheTime: CACHE_TIME / 1000 / 60 + ' minutes'
  };
};