# On your control plane node
sudo mkdir -p /etc/kubernetes/pki/etcd-certs

# Copy etcd certificates
sudo cp /etc/kubernetes/pki/etcd/ca.crt /etc/kubernetes/pki/etcd-certs/
sudo cp /etc/kubernetes/pki/apiserver-etcd-client.crt /etc/kubernetes/pki/etcd-certs/client.crt
sudo cp /etc/kubernetes/pki/apiserver-etcd-client.key /etc/kubernetes/pki/etcd-certs/client.key


sudo chmod 644 /etc/kubernetes/pki/etcd-certs/client.key


# Create a Kubernetes secret with the certificates
kubectl -n monitoring create secret generic etcd-certs \
  --from-file=/etc/kubernetes/pki/etcd-certs/ca.crt \
  --from-file=/etc/kubernetes/pki/etcd-certs/client.crt \
  --from-file=/etc/kubernetes/pki/etcd-certs/client.key
