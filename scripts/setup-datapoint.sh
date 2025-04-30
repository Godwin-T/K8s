#!/bin/bash

# Exit on any error
set -e

echo "Starting K8s LSTM Data Pipeline Setup"

# Create project directory structure
echo "Creating directory structure..."
mkdir -p k8s-lstm-project/data-pipeline
cd k8s-lstm-project/data-pipeline

# Create Python metrics collection script
echo "Creating Python collection script..."
cat > collect_metrics.py << 'EOF'
import requests
import pandas as pd
import time
import os

def collect_prometheus_metrics(query, prometheus_url="http://localhost:9090"):
    response = requests.get(
        f"{prometheus_url}/api/v1/query",
        params={"query": query}
    )
    results = response.json()['data']['result']
    return results

def save_metrics_to_csv(metrics, filename):
    # Convert metrics to DataFrame and save
    df = pd.DataFrame(metrics)
    os.makedirs("data", exist_ok=True)
    df.to_csv(f"data/{filename}", index=False)

# Main collection loop
if __name__ == "__main__":
    while True:
        # CPU usage per pod
        cpu_metrics = collect_prometheus_metrics("sum(rate(container_cpu_usage_seconds_total{container!=''}[5m])) by (pod)")
        
        # Memory usage per pod
        mem_metrics = collect_prometheus_metrics("sum(container_memory_usage_bytes{container!=''}) by (pod)")
        
        # Pod restart count
        restart_metrics = collect_prometheus_metrics("kube_pod_container_status_restarts_total")
        
        # Save with timestamp
        timestamp = int(time.time())
        save_metrics_to_csv(cpu_metrics, f"cpu_metrics_{timestamp}.csv")
        save_metrics_to_csv(mem_metrics, f"mem_metrics_{timestamp}.csv")
        save_metrics_to_csv(restart_metrics, f"restart_metrics_{timestamp}.csv")
        
        # Wait before next collection
        time.sleep(300)  # 5 minutes
EOF

# Create Dockerfile
echo "Creating Dockerfile..."
cat > Dockerfile << 'EOF'
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY collect_metrics.py .
CMD ["python", "collect_metrics.py"]
EOF

# Create requirements.txt
echo "Creating requirements.txt..."
cat > requirements.txt << 'EOF'
pandas
requests
numpy
EOF

# Create Kubernetes manifest files
echo "Creating Kubernetes manifests..."

# Create persistent volume
cat > persistent-volume.yaml << 'EOF'
apiVersion: v1
kind: PersistentVolume
metadata:
  name: my-pv
spec:
  capacity:
    storage: 10Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: standard
  hostPath:
    path: /mnt/data
EOF

# Create persistent volume claim
cat > persistent-volume-claim.yaml << 'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: metrics-data-pvc
  namespace: ml-pipeline
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
EOF

# Create deployment manifest
cat > data-collector.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: metrics-collector
  namespace: ml-pipeline
spec:
  replicas: 1
  selector:
    matchLabels:
      app: metrics-collector
  template:
    metadata:
      labels:
        app: metrics-collector
    spec:
      containers:
      - name: collector
        image: your-registry/metrics-collector:latest
        resources:
          limits:
            cpu: "500m"
            memory: "512Mi"
          requests:
            cpu: "100m"
            memory: "128Mi"
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: metrics-data-pvc
EOF
