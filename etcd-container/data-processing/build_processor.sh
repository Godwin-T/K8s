# Build the Docker image
docker build -t data-processor:latest -f Dockerfile-data-processor .

# Tag and push the image to your registry
docker tag data-processor:latest freshinit/data-processor:latest
docker push freshinit/data-processor:latest

