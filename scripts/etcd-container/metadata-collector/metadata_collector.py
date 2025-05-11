#!/usr/bin/env python3
import os
import time
import json
import logging
import datetime
import pandas as pd
from kubernetes import client, config
from prometheus_client import start_http_server, Gauge

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("metadata-collector")

# Collection interval in seconds
COLLECTION_INTERVAL = int(os.environ.get('COLLECTION_INTERVAL', '300'))
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '/data')

# Prometheus metrics
metadata_count = Gauge('k8s_metadata_count', 'Count of Kubernetes resources', ['resource_type'])
metadata_change_rate = Gauge('k8s_metadata_change_rate', 'Rate of changes in Kubernetes resources', ['resource_type'])
owner_reference_count = Gauge('k8s_owner_reference_count', 'Count of owner references', ['resource_type'])

# Previous snapshots for calculating change rates
previous_counts = {}

def collect_namespaces(api):
    """Collect all namespaces metadata"""
    try:
        return api.list_namespace().items
    except Exception as e:
        logger.error(f"Error collecting namespaces: {e}")
        return []

def collect_resources(api, resource_type, namespace=None):
    """Collect resources of a specific type"""
    try:
        if resource_type == "pods":
            if namespace:
                return api.list_namespaced_pod(namespace).items
            else:
                return api.list_pod_for_all_namespaces().items
        elif resource_type == "deployments":
            apps_v1 = client.AppsV1Api()
            if namespace:
                return apps_v1.list_namespaced_deployment(namespace).items
            else:
                return apps_v1.list_deployment_for_all_namespaces().items
        elif resource_type == "services":
            if namespace:
                return api.list_namespaced_service(namespace).items
            else:
                return api.list_service_for_all_namespaces().items
        elif resource_type == "configmaps":
            if namespace:
                return api.list_namespaced_config_map(namespace).items
            else:
                return api.list_config_map_for_all_namespaces().items
        elif resource_type == "secrets":
            if namespace:
                return api.list_namespaced_secret(namespace).items
            else:
                return api.list_secret_for_all_namespaces().items
        elif resource_type == "statefulsets":
            apps_v1 = client.AppsV1Api()
            if namespace:
                return apps_v1.list_namespaced_stateful_set(namespace).items
            else:
                return apps_v1.list_stateful_set_for_all_namespaces().items
        elif resource_type == "daemonsets":
            apps_v1 = client.AppsV1Api()
            if namespace:
                return apps_v1.list_namespaced_daemon_set(namespace).items
            else:
                return apps_v1.list_daemon_set_for_all_namespaces().items
        # Add more resource types as needed
    except Exception as e:
        logger.error(f"Error collecting {resource_type}: {e}")
        return []

def extract_metadata(resource, resource_type):
    """Extract relevant metadata from a resource"""
    metadata = {
        "resource_type": resource_type,
        "name": resource.metadata.name,
        "namespace": resource.metadata.namespace,
        "creation_timestamp": resource.metadata.creation_timestamp.isoformat() if resource.metadata.creation_timestamp else None,
        "resource_version": resource.metadata.resource_version,
        "uid": resource.metadata.uid,
        "labels": resource.metadata.labels if resource.metadata.labels else {},
        "annotations": resource.metadata.annotations if resource.metadata.annotations else {},
        "owner_references": []
    }
    
    # Extract owner references
    if resource.metadata.owner_references:
        for owner in resource.metadata.owner_references:
            metadata["owner_references"].append({
                "kind": owner.kind,
               "name": owner.name,
                "uid": owner.uid
            })
    
    # Extract status if available
    if hasattr(resource, 'status'):
        metadata["status"] = {}
        if resource_type == "pods" and hasattr(resource.status, 'phase'):
            metadata["status"]["phase"] = resource.status.phase
        elif resource_type in ["deployments", "statefulsets", "daemonsets"]:
            if hasattr(resource.status, 'ready_replicas'):
                metadata["status"]["ready_replicas"] = resource.status.ready_replicas
            if hasattr(resource.status, 'replicas'):
                metadata["status"]["replicas"] = resource.status.replicas
    
    return metadata

def collect_all_metadata():
    """Collect metadata from all resources"""
    metadata = []
    
    # Load Kubernetes configuration
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    
    core_v1 = client.CoreV1Api()
    
    # Collect namespaces
    namespaces = collect_namespaces(core_v1)
    for ns in namespaces:
        metadata.append(extract_metadata(ns, "namespaces"))
    
    # Resource types to collect
    resource_types = [
        "pods", "services", "configmaps", "secrets", 
        "deployments", "statefulsets", "daemonsets"
    ]
    
    # Collect resources
    for resource_type in resource_types:
        resources = collect_resources(core_v1, resource_type)
        type_count = 0
        owner_ref_count = 0
        
        for resource in resources:
            resource_metadata = extract_metadata(resource, resource_type)
            metadata.append(resource_metadata)
            type_count += 1
            owner_ref_count += len(resource_metadata["owner_references"])
        
        # Update Prometheus metrics
        metadata_count.labels(resource_type=resource_type).set(type_count)
        owner_reference_count.labels(resource_type=resource_type).set(owner_ref_count)
        
        # Calculate change rate if we have previous data
        if resource_type in previous_counts:
            change_rate = abs(type_count - previous_counts[resource_type])
            metadata_change_rate.labels(resource_type=resource_type).set(change_rate)
        
        # Update previous counts
        previous_counts[resource_type] = type_count
    
    return metadata

def save_metadata_snapshot(metadata):
    """Save metadata snapshot to a file"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{OUTPUT_DIR}/metadata_snapshot_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Saved metadata snapshot to {filename}")
    
    # Keep a rolling window of snapshots (keep last 24 hours assuming 5-min intervals)
    snapshots_to_keep = 100 #24 * 60 // COLLECTION_INTERVAL
    all_snapshots = sorted([f for f in os.listdir(OUTPUT_DIR) if f.startswith("metadata_snapshot_")])
    
    if len(all_snapshots) > snapshots_to_keep:
        for old_snapshot in all_snapshots[:-snapshots_to_keep]:
            os.remove(os.path.join(OUTPUT_DIR, old_snapshot))
            logger.info(f"Removed old snapshot {old_snapshot}")

def main():
    """Main function to run the metadata collector"""
    # Start Prometheus HTTP server
    start_http_server(8000)
    logger.info("Started Prometheus metrics server on port 8000")
    
    while True:
        logger.info("Collecting Kubernetes metadata...")
        metadata = collect_all_metadata()
        save_metadata_snapshot(metadata)
        logger.info(f"Collected metadata for {len(metadata)} resources")
        logger.info(f"Sleeping for {COLLECTION_INTERVAL} seconds...")
        time.sleep(COLLECTION_INTERVAL)

if __name__ == "__main__":
    main() 
