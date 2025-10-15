#!/bin/bash

# Flask Todo App Setup Script
# This script helps set up the project for new users

echo "🚀 Setting up Flask Todo App..."

# Check if pipenv is installed
if ! command -v pipenv &> /dev/null; then
    echo "❌ pipenv is not installed. Installing it now..."
    
    # Check if pipx is available
    if command -v pipx &> /dev/null; then
        echo "📦 Installing pipenv via pipx..."
        pipx install pipenv
    else
        echo "📦 Installing pipx first, then pipenv..."
        # For macOS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            if command -v brew &> /dev/null; then
                brew install pipx
                pipx install pipenv
            else
                echo "❌ Please install Homebrew first, then run: brew install pipx && pipx install pipenv"
                exit 1
            fi
        else
            echo "❌ Please install pipx manually, then run: pipx install pipenv"
            exit 1
        fi
    fi
else
    echo "✅ pipenv is already installed"
fi

# Install project dependencies
echo "📦 Installing project dependencies..."
pipenv install

echo "🎉 Setup complete!"
echo ""
echo "To run the app:"
echo "  pipenv run python app.py"
echo ""
echo "Or activate the virtual environment first:"
echo "  pipenv shell"
echo "  python app.py"
echo ""
echo "The app will be available at: http://localhost:3000"
