# Build the Docker image
docker build -t metadata-collector:latest -f Dockerfile-metadata-collector .

# Tag and push the image to your registry
docker tag metadata-collector:latest freshinit/metadata-collector:latest
docker push freshinit/metadata-collector:latest

