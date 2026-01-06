#!/bin/bash
set -e

# Configuration
PROJECT_ID="trading-397212"
REGION="asia-south1"
BACKEND_SERVICE="portfolio-backend"
FRONTEND_SERVICE="portfolio-frontend"

echo "========================================================"
echo "Portfolio Agent Deployment Script - GCP (${REGION})"
echo "========================================================"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed."
    echo "Please install it: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Authenticate if needed (check if active account exists)
if ! gcloud auth print-access-token &> /dev/null; then
    echo "Not authenticated. Opening login..."
    gcloud auth login
fi

echo "Setting project to ${PROJECT_ID}..."
gcloud config set project ${PROJECT_ID}

# Load environment variables from .env
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    # Export variables, ignoring comments
    export $(grep -v '^#' .env | xargs)
fi

# Prepare Env Vars for Cloud Run
# db_service.py expects SUPABASE_URL and SUPABASE_API_KEY
# We prioritize SUPABASE_API_KEY, fallback to SUPABASE_KEY if defined
API_KEY="${SUPABASE_API_KEY:-$SUPABASE_KEY}"
ENV_VARS="SUPABASE_URL=${SUPABASE_URL},SUPABASE_API_KEY=${API_KEY},GOOGLE_API_KEY=${GOOGLE_API_KEY}"

# Parse argument (all, frontend, or backend)
TARGET=${1:-all}

echo "Deploying target: ${TARGET}"

# Initialize URLs
BACKEND_URL=""
FRONTEND_URL=""

# ========================================================
# Deploy Backend
# ========================================================
if [[ "$TARGET" == "all" || "$TARGET" == "backend" ]]; then
    echo "========================================================"
    echo "Deploying Backend..."
    echo "========================================================"

    # Make sure we have the keys
    if [ -z "$SUPABASE_URL" ] || [ -z "$API_KEY" ]; then
        echo "Error: SUPABASE_URL and SUPABASE_API_KEY/SUPABASE_KEY must be set in .env"
        exit 1
    fi

    # Build Backend
    gcloud builds submit --config deployment/cloudbuild-backend.yaml .

    # Deploy Backend
    gcloud run deploy ${BACKEND_SERVICE} \
        --image gcr.io/${PROJECT_ID}/${BACKEND_SERVICE} \
        --platform managed \
        --region ${REGION} \
        --allow-unauthenticated \
        --memory 512Mi \
        --min-instances 0 \
        --max-instances 1 \
        --set-env-vars "${ENV_VARS}"

    # Get Backend URL
    BACKEND_URL=$(gcloud run services describe ${BACKEND_SERVICE} --platform managed --region ${REGION} --format 'value(status.url)')
    echo "Backend deployed at: ${BACKEND_URL}"
fi

# ========================================================
# Deploy Frontend
# ========================================================
if [[ "$TARGET" == "all" || "$TARGET" == "frontend" ]]; then
    echo "========================================================"
    echo "Deploying Frontend..."
    echo "========================================================"

    # Always fetch the latest Backend URL if not just deployed
    if [ -z "$BACKEND_URL" ]; then
        BACKEND_URL=$(gcloud run services describe ${BACKEND_SERVICE} --platform managed --region ${REGION} --format 'value(status.url)')
    fi
    
    if [ -z "$BACKEND_URL" ]; then
        echo "Error: Failed to get Backend URL. Ensure backend is deployed first."
        exit 1
    fi
    echo "Using Backend URL: ${BACKEND_URL}"

    # Build Frontend
    gcloud builds submit --config deployment/cloudbuild-frontend.yaml --substitutions=_NEXT_PUBLIC_API_URL="${BACKEND_URL}" .

    # Deploy Frontend
    gcloud run deploy ${FRONTEND_SERVICE} \
        --image gcr.io/${PROJECT_ID}/${FRONTEND_SERVICE} \
        --platform managed \
        --region ${REGION} \
        --allow-unauthenticated \
        --memory 512Mi \
        --min-instances 0 \
        --max-instances 1 \
        --set-env-vars "NEXT_PUBLIC_API_URL=${BACKEND_URL},SUPABASE_URL=${SUPABASE_URL},SUPABASE_API_KEY=${API_KEY}"
    
    FRONTEND_URL=$(gcloud run services describe ${FRONTEND_SERVICE} --platform managed --region ${REGION} --format 'value(status.url)')
fi

echo "========================================================"
echo "Deployment Complete!"
echo "========================================================"
if [ ! -z "$BACKEND_URL" ]; then
    echo "Backend:  ${BACKEND_URL}"
fi
if [ ! -z "$FRONTEND_URL" ]; then
    echo "Frontend: ${FRONTEND_URL}"
fi
echo ""
echo "Next Steps:"
echo "1. Configure Cloud Scheduler jobs for daily tasks."
echo "   (See DEPLOYMENT.md for details)"
