# install Helm

curl https://baltocdn.com/helm/signing.asc | sudo apt-key add -

sudo apt install apt-transport-https --yes
echo "deb https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list

sudo apt update

sudo apt install helm

# install Prometheus

kubectl create namespace monitoring
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring

kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n monitoring

