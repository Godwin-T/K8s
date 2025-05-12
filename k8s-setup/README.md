# Self Hosted Kubernetes 

This repository contains scripts to set up a self-hosted Kubernetes cluster 

## Overview

The setup consists of multiple scripts that handle Kubernetes cluster setup (master and worker nodes)

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
├── setup-container.sh     # Script to build and deploy the data collection container
├── setup-kubetools.sh     # Script to install Kubernetes tools (internal)
```

## Installation Steps

### Step 1: Clone the Repository

Clone this repository to all servers:

```bash
git clone <repository-url>
cd <repository-directory>
```

### Step 2: Set Up Kubernetes Cluster

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

