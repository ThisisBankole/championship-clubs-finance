import axios from 'axios';

export const STRAPI_BASE_URL = 'https://cms.arrakis.house';

export const strapiApi = axios.create({
  baseURL: STRAPI_BASE_URL,
  timeout: 30000,
});

export const clubDescriptionsApi = {
  // Get all club descriptions
  getAllDescriptions: () => strapiApi.get('/api/club-descriptions'),
  
  // Get description by club slug
  getDescriptionBySlug: (clubSlug) => 
    strapiApi.get(`/api/club-descriptions?filters[club_slug][$eq]=${clubSlug}`),
};