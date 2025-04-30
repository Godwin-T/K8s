# Kubernetes LSTM Data Pipeline

This repository contains scripts to set up a self-hosted Kubernetes cluster with a data pipeline for collecting and processing metrics for LSTM model training.

## Overview

The setup consists of multiple scripts that handle different aspects of the deployment:

- Kubernetes cluster setup (master and worker nodes)
- Prometheus monitoring installation
- Data collection pipeline deployment
- Docker installation (if needed)

## Prerequisites

- Multiple Linux servers (Ubuntu recommended)
- One server designated as master, others as worker nodes
- Root or sudo access on all servers
- Internet connectivity on all servers

## Repository Structure

```
.
├── README.md
├── setup-master.sh        # Script to set up the Kubernetes master node
├── setup-node.sh          # Script to set up Kubernetes worker nodes
├── setup-prometheus.sh    # Script to deploy Prometheus monitoring
├── setup-datapoint.sh     # Script to set up data collection endpoints
├── setup-container.sh     # Script to build and deploy the data collection container
├── setup-kubetools.sh     # Script to install Kubernetes tools (internal)
├── setup-docker.sh        # Script to install Docker (if needed)
└── k8s-lstm-project/      # Data pipeline project files
    └── data-pipeline/     # Contains Python scripts, Dockerfile, and K8s manifests
```

## Installation Steps

### Step 1: Clone the Repository

Clone this repository to all servers:

```bash
git clone <repository-url>
cd <repository-directory>
```

### Step 2: Set Up Kubernetes Cluster

#### Option A: Set Up a New Kubernetes Cluster

If you don't have a Kubernetes cluster yet:

1. On the master node:

```bash
sudo ./setup-master.sh
```

This will initialize the master node and output a join command similar to:

```
kubeadm join 172.31.36.244:6443 --token anzcjr.hhe8jhhb0slzxw8v \
	--discovery-token-ca-cert-hash sha256:971a889aeb46461dbafb4ccd672e85b361fc279665bf4a79beb13c207e55b338 
```

2. On each worker node:

```bash
sudo ./setup-node.sh
```

3. After running the node setup script, paste the join command from the master node:

```bash
sudo kubeadm join 172.31.36.244:6443 --token anzcjr.hhe8jhhb0slzxw8v \
	--discovery-token-ca-cert-hash sha256:971a889aeb46461dbafb4ccd672e85b361fc279665bf4a79beb13c207e55b338
```

#### Option B: Use Existing Kubernetes Cluster

If you already have a Kubernetes cluster set up, you can skip Step 2 and proceed to Step 3.

### Step 3: Set Up Monitoring and Data Collection

On the master node:

```bash
# Deploy Prometheus monitoring stack
sudo ./setup-prometheus.sh

# Set up data collection endpoints
sudo ./setup-datapoint.sh
```

### Step 4: Set Up Docker (if needed)

If Docker is not already installed:

```bash
sudo ./setup-docker.sh

# After Docker installation, reboot the server
sudo reboot
```

After the server reboots, log in to Docker:

```bash
docker login
# Enter your Docker Hub credentials when prompted
```

### Step 5: Deploy the Data Pipeline

Navigate to your project directory:

```bash
cd k8s-lstm-project/data-pipeline
```

Follow these steps to build and deploy the data collector:

1. Enter your Docker registry information:

```bash
# Prompt for Docker registry
echo -n "Enter your Docker registry URL (e.g., your-registry.com): "
read DOCKER_REGISTRY

# Replace placeholder in yaml file
sed -i "s|your-registry|${DOCKER_REGISTRY}|g" data-collector.yaml
```

2. Create Kubernetes namespace:

```bash
# Create Kubernetes namespace
kubectl create namespace ml-pipeline
```

3. Build and push the Docker image:

```bash
# Build and push Docker image
docker build -t ${DOCKER_REGISTRY}/metrics-collector:latest .
docker push ${DOCKER_REGISTRY}/metrics-collector:latest
```

4. Apply Kubernetes manifests:

```bash
# Apply Kubernetes manifests
kubectl apply -f persistent-volume.yaml
kubectl apply -f persistent-volume-claim.yaml
kubectl apply -f data-collector.yaml
```

5. Verify deployment:

```bash
# Check status of pods
kubectl get pods -n ml-pipeline
```

## Verification

To veify that everything is running correctly:

1. Check Kubernetes nodes:

```bash
kubectl get nodes
```

2. Check Prometheus deployment:

```bash
kubectl get pods -n monitoring
```

3. Check data pipeline:

```bash
kubectl get pods -n ml-pipeline
kubectl logs -n ml-pipeline <pod-name>
```

## Data Collection

The data pipeline will collect the following metrics every 5 minutes:

- CPU usage per pod
- Memory usage per pod
