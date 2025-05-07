#!/usr/bin/env python3
import os
import json
import time
import logging
import glob
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_selection import chi2
from sklearn.ensemble import IsolationForest
from prometheus_client import start_http_server, Gauge

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("data-processor")

# Configuration
PROCESSING_INTERVAL = int(os.environ.get('PROCESSING_INTERVAL', '600'))
INPUT_DIR = os.environ.get('INPUT_DIR', '/data')
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '/processed_data')
WINDOW_SIZE = int(os.environ.get('WINDOW_SIZE', '12'))  # Number of snapshots to include in time series window

# Prometheus metrics
processed_features_count = Gauge('k8s_processed_features_count', 'Count of processed features')
anomaly_score = Gauge('k8s_anomaly_score', 'Anomaly score from isolation forest', ['resource_type'])
correlation_score = Gauge('k8s_correlation_score', 'Correlation score between metadata fields', ['field_pair'])

def load_snapshots(input_dir, window_size):
    """Load the most recent snapshots"""
    snapshot_files = sorted(glob.glob(os.path.join(input_dir, "metadata_snapshot_*.json")))
    
    if not snapshot_files:
        logger.warning(f"No snapshot files found in {input_dir}")
        return []
    
    # Take the most recent snapshots based on window_size
    recent_snapshots = snapshot_files[-window_size:] if len(snapshot_files) >= window_size else snapshot_files
    
    snapshots = []
    for file_path in recent_snapshots:
        try:
            with open(file_path, 'r') as f:
                snapshot = json.load(f)
                snapshots.append({
                    'timestamp': os.path.basename(file_path).split('_')[1].split('.')[0],
                    'data': snapshot
                })
        except Exception as e:
            logger.error(f"Error loading snapshot {file_path}: {e}")
    
    return snapshots

def calculate_ewma(series, span=3):
    """Calculate Exponentially Weighted Moving Average for trend analysis"""
    return series.ewm(span=span).mean()

def calculate_categorical_correlation(df, cat_columns):
    """Calculate correlation between categorical variables using Cramer's V"""
    correlations = {}
    
    for i, col1 in enumerate(cat_columns):
        for col2 in cat_columns[i+1:]:
            # Create contingency table
            contingency = pd.crosstab(df[col1], df[col2])
            
            # Calculate Cramer's V
            chi2_stat = stats.chi2_contingency(contingency)[0]
            n = contingency.sum().sum()
            phi2 = chi2_stat / n
            r, k = contingency.shape
            phi2corr = max(0, phi2 - ((k-1)*(r-1))/(n-1))
            rcorr = r - ((r-1)**2)/(n-1)
            kcorr = k - ((k-1)**2)/(n-1)
            cramer_v = np.sqrt(phi2corr / min((kcorr-1), (rcorr-1)))
            
            correlations[f"{col1}__{col2}"] = cramer_v
    
    return correlations

def extract_features(snapshots):
    """Extract features from snapshots for anomaly detection"""
    if not snapshots:
        logger.warning("No snapshots available for feature extraction")
        return pd.DataFrame()
    
    # Resource counts over time
    resource_counts = {}
    owner_ref_counts = {}
    resource_versions = {}
    status_changes = {}
    
    for snapshot in snapshots:
        timestamp = snapshot['timestamp']
        
        # Initialize counters for this timestamp
        if timestamp not in resource_counts:
            resource_counts[timestamp] = {}
            owner_ref_counts[timestamp] = {}
            resource_versions[timestamp] = {}
            status_changes[timestamp] = {}
        
        # Process each resource
        for resource in snapshot['data']:
            resource_type = resource['resource_type']
            
            # Count resources by type
            if resource_type not in resource_counts[imestamp]:
                resource_counts[timestamp][resource_type] = 0
            resource_counts[timestamp][resource_type] += 1
            
            # Count owner references
            if resource_type not in owner_ref_counts[timestamp]:
                owner_ref_counts[timestamp][resource_type] = 0
            owner_ref_counts[timestamp][resource_type] += len(resource.get('owner_references', []))
            
            # Track resource versions (for rate of change)
            resource_id = f"{resource_type}_{resource.get('namespace', 'cluster')}_{resource.get('name', 'unknown')}"
            resource_versions[timestamp][resource_id] = resource.get('resource_version', '0')
            
            # Track status changes
            if 'status' in resource:
                status_key = f"{resource_type}_status"
                if status_key not in status_changes[timestamp]:
                    status_changes[timestamp][status_key] = 0
                status_changes[timestamp][status_key] += 1
    
    # Create time series dataframes
    timestamps = sorted(resource_counts.keys())
    
    # Resource count features
    resource_types = set()
    for ts_counts in resource_counts.values():
        resource_types.update(ts_counts.keys())
    
    resource_count_data = []
    for ts in timestamps:
        row = {'timestamp': ts}
        for rt in resource_types:
            row[f"count_{rt}"] = resource_counts[ts].get(rt, 0)
        resource_count_data.append(row)
    
    resource_count_df = pd.DataFrame(resource_count_data)
    
    # Owner reference features
    owner_ref_data = []
    for ts in timestamps:
        row = {'timestamp': ts}
        for rt in resource_types:
            row[f"owner_refs_{rt}"] = owner_ref_counts[ts].get(rt, 0)
        owner_ref_data.append(row)
    
    owner_ref_df = pd.DataFrame(owner_ref_data)
    
    # Resource version change rate
    version_change_data = []
    for i in range(1, len(timestamps)):
        prev_ts = timestamps[i-1]
        curr_ts = timestamps[i]
        
        row = {'timestamp': curr_ts}
        version_changes = 0
        
        for resource_id in set(resource_versions[prev_ts].keys()) | set(resource_versions[curr_ts].keys()):
            prev_version = resource_versions[prev_ts].get(resource_id, '0')
            curr_version = resource_versions[curr_ts].get(resource_id, '0')
            
            if prev_version != curr_version:
                version_changes += 1
        
        row['version_change_rate'] = version_changes
        version_change_data.append(row)
    
    version_change_df = pd.DataFrame(version_change_data) if version_change_data else pd.DataFrame(columns=['timestamp', 'version_change_rate'])
    
    # Status change features
    status_keys = set()
    for ts_status in status_changes.values():
        status_keys.update(ts_status.keys())
    
    status_change_data = []
    for ts in timestamps:
        row = {'timestamp': ts}
        for status_key in status_keys:
            row[status_key] = status_changes[ts].get(status_key, 0)
        status_change_data.append(row)
    
    status_change_df = pd.DataFrame(status_change_data)
    
    # Merge all features
    feature_dfs = [resource_count_df]
    
    if not owner_ref_df.empty:
        feature_dfs.append(owner_ref_df.drop(columns=['timestamp'], errors='ignore'))
    
    if not version_change_df.empty:
        # For the first timestamp, we don't have version change data
        merged_df = pd.merge(
            feature_dfs[0], 
            version_change_df,
            on='timestamp',
            how='left'
        )
        merged_df['version_change_rate'] = merged_df['version_change_rate'].fillna(0)
        feature_dfs[0] = merged_df
    
    if not status_change_df.empty:
        feature_dfs.append(status_change_df.drop(columns=['timestamp'], errors='ignore'))
    
    # Combine all feature sets
    features_df = feature_dfs[0]
    for df in feature_dfs[1:]:
        features_df = pd.concat([features_df, df], axis=1)
    
    # Fill NaN values
    features_df = features_df.fillna(0)
    
    return features_df

def detect_anomalies(features_df):
    """Detect anomalies using Isolation Forest"""
    if features_df.empty or len(features_df) < 2:
        logger.warning("Not enough data for anomaly detection")
        return pd.DataFrame()
    
    # Drop timestamp column for modeling
    X = features_df.drop(columns=['timestamp'], errors='ignore')
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Apply Isolation Forest
    clf = IsolationForest(
        n_estimators=100,
        max_samples='auto',
        contamination=0.1,
        random_state=42
    )
    
    # Fit and predict
    anomaly_scores = clf.fit_predict(X_scaled)
    anomaly_scores = -clf.score_samples(X_scaled)  # Higher score = more anomalous
    
    # Add anomaly scores back to features
    result_df = features_df.copy()
    result_df['anomaly_score'] = anomaly_scores
    result_df['is_anomaly'] = anomaly_scores > np.percentile(anomaly_scores, 90)
    
    # Update Prometheus metrics
    avg_anomaly_score = np.mean(anomaly_scores)
    anomaly_score.labels(resource_type='overall').set(avg_anomaly_score)
    
    return result_df

def save_processed_data(features_df, anomalies_df, output_dir):
    """Save processed data and anomalies to files"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    
    # Save features
    features_path = os.path.join(output_dir, f"features_{timestamp}.csv")
    features_df.to_csv(features_path, index=False)
    logger.info(f"Saved features to {features_path}")
    
    # Save anomalies if any were detected
    if not anomalies_df.empty:
        anomalies_path = os.path.join(output_dir, f"anomalies_{timestamp}.csv")
        anomalies_df.to_csv(anomalies_path, index=False)
        logger.info(f"Saved anomalies to {anomalies_path}")
    
    # Keep a rolling window of processed data
    files_to_keep = 48  # Keep 2 days worth of data assuming processing every 30 minutes
    all_feature_files = sorted(glob.glob(os.path.join(output_dir, "features_*.csv")))
    all_anomaly_files = sorted(glob.glob(os.path.join(output_dir, "anomalies_*.csv")))
    
    if len(all_feature_files) > files_to_keep:
        for old_file in all_feature_files[:-files_to_keep]:
            os.remove(old_file)
            logger.info(f"Removed old feature file {old_file}")
    
    if len(all_anomaly_files) > files_to_keep:
        for old_file in all_anomaly_files[:-files_to_keep]:
            os.remove(old_file)
            logger.info(f"Removed old anomaly file {old_file}")

def main():
    """Main function to run the data processor"""
    # Start Prometheus HTTP server
    start_http_server(8001)
    logger.info("Started Prometheus metrics server on port 8001")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    while True:
        logger.info("Processing Kubernetes metadata snapshots...")
        
        # Load snapshots
        snapshots = load_snapshots(INPUT_DIR, WINDOW_SIZE)
        
        if not snapshots:
            logger.warning("No snapshots available for processing")
            time.sleep(PROCESSING_INTERVAL)
            continue
        
        # Extract features
        features_df = extract_features(snapshots)
        processed_features_count.set(len(features_df.columns) - 1)  # Subtract timestamp column
        
        # Calculate EWMA for trend analysis
        numeric_columns = features_df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col != 'timestamp':
                features_df[f"{col}_ewma"] = calculate_ewma(features_df[col])
        
        # Detect anomalies
        anomalies_df = detect_anomalies(features_df)
        anomalies_df = anomalies_df[anomalies_df['is_anomaly']]
        
        # Calculate categorical correlations
        # This would typically be done for categorical fields, but we're mostly dealing with numeric data
        # Just as an example, if we had categorical columns:
        # cat_columns = ['status_pod', 'status_deployment']
        # correlations = calculate_categorical_correlation(features_df, cat_columns)
        # for field_pair, corr_value in correlations.items():
        #     correlation_score.labels(field_pair=field_pair).set(corr_value)
        
        # Save processed data
        save_processed_data(features_df, anomalies_df, OUTPUT_DIR)
        
        logger.info(f"Processing complete. Found {len(anomalies_df)} potential anomalies.")
        logger.info(f"Sleeping for {PROCESSING_INTERVAL} seconds...")
        time.sleep(PROCESSING_INTERVAL)

if __name__ == "__main__":
    main()t
