# Kubernetes Data Pipeline

This repository contains scripts to set up data collection pipeline in K8s


### Step 1: Set Up Docker 

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

### Step 2: Set Up Monitoring and Data Collection

On the master node:

```bash
# Deploy Prometheus monitoring stack
sudo ./setup-prometheus.sh

# Set up data collection endpoints
sudo ./setup-datapoint.sh
```

### Step 4: Deploy the Data Pipeline

Navigate to your project directory:

```bash
cd ./data-pipeline
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
kubectl create namespace data-pipeline
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
kubectl get pods -n data-pipeline
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
kubectl get pods -n data-pipeline
kubectl logs -n ml-pipeline <pod-name>
```

## Data Collection

The data pipeline will collect the following metrics every 5 minutes:

- CPU usage per pod
- Memory usage per pod
