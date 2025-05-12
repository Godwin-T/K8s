curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash


# Add Helm repositories
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Create monitoring namespace
kubectl create namespace monitoring

# Install Prometheus stack (includes Prometheus, Alertmanager, and node-exporter)
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false

# Install Loki stack for log aggregation
# helm install loki grafana/loki-stack \
#   --namespace monitoring \
#   --set grafana.enabled=false \
#   --set prometheus.enabled=false \
#  --set loki.persistence.enabled=true \
#  --set loki.persistence.size=5Gi

kubectl apply -f pv.yaml
kubectl apply -f loki-pvc.yaml

helm install loki grafana/loki-stack \
  --namespace monitoring \
  --set grafana.enabled=false \
  --set prometheus.enabled=false \
  --set loki.persistence.enabled=true \
  --set loki.persistence.existingClaim=loki-data-pvc
