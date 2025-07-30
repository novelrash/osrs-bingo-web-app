#!/bin/bash

# Pea Kingdom Bingo - Safe Deployment Script
# Supports selective deployment to avoid overwriting critical files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - Update these for your deployment
INSTANCE_IP="your.server.ip"
KEY_FILE="$HOME/your-key.pem"
REMOTE_DIR="/opt/your-app"

echo -e "${BLUE}🚀 Pea Kingdom Bingo - Safe Deployment${NC}"

# Function to show help
show_help() {
    echo "Usage: ./deploy.sh [options]"
    echo ""
    echo "Options:"
    echo "  --templates-only    Deploy only templates (safe for UI changes)"
    echo "  --app-only         Deploy only application code"
    echo "  --static-only      Deploy only static assets"
    echo "  --full             Deploy everything (requires confirmation)"
    echo "  --logs             Show application logs after deployment"
    echo "  --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh --templates-only     # Safe template updates"
    echo "  ./deploy.sh --app-only           # Update application logic"
    echo "  ./deploy.sh --full               # Complete deployment"
}

# Parse command line arguments
TEMPLATES_ONLY=false
APP_ONLY=false
STATIC_ONLY=false
FULL_DEPLOY=false
SHOW_LOGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --templates-only)
            TEMPLATES_ONLY=true
            shift
            ;;
        --app-only)
            APP_ONLY=true
            shift
            ;;
        --static-only)
            STATIC_ONLY=true
            shift
            ;;
        --full)
            FULL_DEPLOY=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Default to templates-only if no option specified
if [ "$TEMPLATES_ONLY" = false ] && [ "$APP_ONLY" = false ] && [ "$STATIC_ONLY" = false ] && [ "$FULL_DEPLOY" = false ]; then
    TEMPLATES_ONLY=true
    echo -e "${YELLOW}⚠️ No deployment type specified, defaulting to --templates-only${NC}"
fi

# Deployment functions
deploy_templates() {
    echo -e "${BLUE}📄 Deploying templates...${NC}"
    scp -i "$KEY_FILE" -o StrictHostKeyChecking=no -r templates/ ec2-user@$INSTANCE_IP:~/templates_new/
    
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ec2-user@$INSTANCE_IP << 'EOF'
        echo "📂 Updating templates..."
        sudo cp -r ~/templates_new/* /opt/your-app/templates/
        sudo chown -R ec2-user:ec2-user /opt/your-app/templates/
        rm -rf ~/templates_new
        
        echo "🔄 Restarting application..."
        sudo systemctl restart your-app
        sleep 3
EOF
}

deploy_app() {
    echo -e "${BLUE}🐍 Deploying application code...${NC}"
    scp -i "$KEY_FILE" -o StrictHostKeyChecking=no app.py auth.py ec2-user@$INSTANCE_IP:~/
    
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ec2-user@$INSTANCE_IP << 'EOF'
        echo "📂 Updating application files..."
        sudo cp ~/app.py /opt/your-app/
        sudo cp ~/auth.py /opt/your-app/
        sudo chown ec2-user:ec2-user /opt/your-app/app.py /opt/your-app/auth.py
        rm ~/app.py ~/auth.py
        
        echo "🔄 Restarting application..."
        sudo systemctl restart your-app
        sleep 3
EOF
}

deploy_static() {
    echo -e "${BLUE}🎨 Deploying static assets...${NC}"
    scp -i "$KEY_FILE" -o StrictHostKeyChecking=no -r static/ ec2-user@$INSTANCE_IP:~/static_new/
    
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ec2-user@$INSTANCE_IP << 'EOF'
        echo "📂 Updating static files..."
        sudo cp -r ~/static_new/* /opt/your-app/static/
        sudo chown -R ec2-user:ec2-user /opt/your-app/static/
        rm -rf ~/static_new
EOF
}

deploy_full() {
    echo -e "${YELLOW}⚠️ Full deployment - this will update all files!${NC}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 1
    fi
    
    echo -e "${BLUE}📦 Creating deployment package...${NC}"
    tar -czf app-deployment.tar.gz \
        --exclude='.git' \
        --exclude='venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='*.pem' \
        --exclude='*.tar.gz' \
        . 2>/dev/null || true

    echo -e "${BLUE}📤 Uploading to server...${NC}"
    scp -i "$KEY_FILE" -o StrictHostKeyChecking=no app-deployment.tar.gz ec2-user@$INSTANCE_IP:~/

    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ec2-user@$INSTANCE_IP << 'EOF'
        set -e
        
        echo "💾 Creating backup..."
        sudo cp -r /opt/your-app /opt/your-app.backup.$(date +%Y%m%d_%H%M%S)
        
        echo "📂 Extracting new version..."
        tar -xzf app-deployment.tar.gz -C /opt/your-app
        
        sudo chown -R ec2-user:ec2-user /opt/your-app
        
        echo "🔄 Restarting services..."
        sudo systemctl restart your-app
        sudo systemctl restart nginx
        sleep 3
EOF

    rm -f app-deployment.tar.gz
}

# Execute deployment based on options
if [ "$TEMPLATES_ONLY" = true ]; then
    deploy_templates
elif [ "$APP_ONLY" = true ]; then
    deploy_app
elif [ "$STATIC_ONLY" = true ]; then
    deploy_static
elif [ "$FULL_DEPLOY" = true ]; then
    deploy_full
fi

# Check deployment status
echo -e "${BLUE}🔍 Checking deployment status...${NC}"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ec2-user@$INSTANCE_IP << 'EOF'
    if sudo systemctl is-active --quiet your-app; then
        echo "✅ Application is running"
    else
        echo "❌ Application failed to start"
        exit 1
    fi
EOF

# Show logs if requested
if [ "$SHOW_LOGS" = true ]; then
    echo -e "${BLUE}📋 Application logs:${NC}"
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ec2-user@$INSTANCE_IP 'sudo journalctl -u your-app --no-pager -n 20'
fi

echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo -e "${BLUE}🌐 Your application should be live at your configured domain${NC}"
