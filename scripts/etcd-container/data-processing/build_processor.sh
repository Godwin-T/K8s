# Build the Docker image
docker build -t data-processor:latest -f Dockerfile-data-processor .

# Tag and push the image to your registry
docker tag data-processor:latest ${DOCKER_REGISTRY}/data-processor:latest
docker push ${DOCKER_REGISTRY}/data-processor:latest

# Deploy the processor
kubectl apply -f data-processor-deployment.yaml
