# Deployment Guide - Google Cloud Platform

This guide details how to deploy your Portfolio Agent to Google Cloud Platform (GCP) using Cloud Run and Cloud Scheduler.

## Prerequisites

1.  **Google Cloud CLI (gcloud)**: [Install gcloud CLI](https://cloud.google.com/sdk/docs/install)
2.  **Project ID**: `trading-397212`
3.  **Region**: `asia-south1` (Mumbai)

## Deployment Steps

### 1. Initial Setup (One-time)
Open your terminal in the project directory and run the following commands to enable necessary services:

```bash
# Login to Google Cloud
gcloud auth login

# Set project
gcloud config set project trading-397212

# Enable APIs
gcloud services enable run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    cloudscheduler.googleapis.com
```

### 2. Deploy Services
We have created an automated script to build and deploy both services.

```bash
./deploy.sh
```

This script will:
1.  Build the Backend Docker image.
2.  Deploy the Backend to Cloud Run.
3.  Build the Frontend Docker image.
4.  Deploy the Frontend to Cloud Run (linking it to the Backend).
5.  Output the URLs for both services.

### 3. Configure Scheduled Tasks
To save costs, we use Cloud Scheduler instead of a 24/7 background process.

Go to [Cloud Scheduler Console](https://console.cloud.google.com/cloudscheduler) and create 3 jobs:

#### Job 1: Daily Price Update
- **Frequency**: `45 15 * * 1-5` (3:45 PM IST, Mon-Fri)
- **Timezone**: India Standard Time (IST)
- **Target Type**: HTTP
- **URL**: `[YOUR_BACKEND_URL]/api/scheduler/daily-update`
- **Method**: POST

#### Job 2: Portfolio Manager (AI Agent)
- **Frequency**: `30 17 * * 1-5` (5:30 PM IST, Mon-Fri)
- **Timezone**: India Standard Time (IST)
- **Target Type**: HTTP
- **URL**: `[YOUR_BACKEND_URL]/api/scheduler/portfolio-manager`
- **Method**: POST

#### Job 3: Weekly Cleanup
- **Frequency**: `0 0 * * 0` (Midnight, Sunday)
- **Timezone**: India Standard Time (IST)
- **Target Type**: HTTP
- **URL**: `[YOUR_BACKEND_URL]/api/scheduler/cleanup`
- **Method**: POST

*(Replace `[YOUR_BACKEND_URL]` with the URL output by the deploy script)*

## Supabase Connection
The application connects to your Supabase database. Cloud Run pulls environment variables from your local `.env` file if you configure it, or you can set them manually in the Cloud Run console under "Edit & Deploy New Revision" > "Variables".

**Important**: Ensure your Supabase database allows connections from everywhere (0.0.0.0/0) or configure Network Security if needed. By default, Supabase is accessible from anywhere with the correct credentials.
