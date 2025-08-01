#!/bin/bash
# Initial setup script

echo "🔧 Setting up development environment..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file
if [ ! -f .env.development ]; then
    cp .env.template .env.development
    echo "⚠️  Please edit .env.development with your actual configuration values"
fi

echo "✅ Development environment setup complete!"
echo "📝 Next steps:"
echo "   1. Edit .env.development with your API keys"
echo "   2. Run ./scripts/dev-start.sh to start services"
