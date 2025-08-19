
export const clubNameToSlug = (clubName) => {
    return clubName
      .toLowerCase()
      .replace(/\s+/g, '-')          
      .replace(/[^\w-]/g, '')         
      .replace(/^-|-$/g, '');         
  };
  
  // Convert slug back to display name
  export const slugToClubName = (slug) => {
    return slug
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };
  
  // Test the conversion
  // clubNameToSlug("Birmingham City") → "birmingham-city"
  // clubNameToSlug("West Bromwich Albion") → "west-bromwich-albion"