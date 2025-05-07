# Build the Docker image
docker build -t metadata-collector:latest -f Dockerfile-metadata-collector .

# Tag and push the image to your registry
docker tag metadata-collector:latest ${DOCKER_REGISTRY}/metadata-collector:latest
docker push ${DOCKER_REGISTRY}/metadata-collector:latest

# Deploy the collector
kubectl apply -f metadata-collector-deployment.yaml
