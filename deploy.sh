#!/bin/bash
echo "🚀 Deploying to football.arrakis.house..."

# Make sure we're on the master branch
git checkout master

# Push to Dokku
git push dokku master

echo "✅ Deployed! Visit https://football.arrakis.house"
