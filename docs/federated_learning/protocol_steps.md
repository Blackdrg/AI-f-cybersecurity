# Federated Learning Protocol Steps

This document details the complete Federated Learning (FL) protocol implementation in AI-f, including the round lifecycle, client usage, and security mechanisms.

## Overview

AI-f implements a privacy-preserving federated learning system that allows organizations to collaboratively train machine learning models without sharing raw data. The system uses:
- **Secure Aggregation**: To protect individual client updates
- **Differential Privacy**: To prevent membership inference attacks
- **Paillier Homomorphic Encryption**: For secure weight aggregation
- **Krum Defense**: To defend against Byzantine (malicious) clients

## Protocol Participants

1. **Federated Server**: Orchestrates the training process, aggregates updates, and maintains the global model
2. **Federated Clients**: Organizations or devices that perform local training on their private data
3. **Client Orchestrator**: Manages client registration, selection, and communication

## Round Lifecycle

Each federated learning round consists of the following phases:

### Phase 1: Round Initialization
1. Server generates a unique `round_id` (UUIDv4)
2. Server loads `RoundConfig` with parameters:
   - `min_clients`: Minimum required participants (default: 3)
   - `max_clients`: Maximum allowed participants (default: 100)
   - `timeout_seconds`: Round duration limit (default: 300 seconds)
   - `aggregation_method`: "fedavg" or "fedprox"
   - `differential_privacy`: Boolean flag (default: true)
   - `noise_multiplier`: DP noise scale (default: 1.0)
   - `max_grad_norm`: Gradient clipping threshold (default: 1.0)
3. Server broadcasts round initiation to all registered clients
4. Server sets round status to "waiting_for_clients"

### Phase 2: Client Registration & Selection
1. Clients register with the orchestrator using `register_client()` with their capabilities
2. Orchestrator maintains a registry of available clients with:
   - Client ID
   - Registration timestamp
   - Capabilities (compute power, data size, supported modalities)
   - Current status (idle/selected/training/completed/failed)
3. For each round, orchestrator selects clients using:
   - Random sampling from idle clients
   - Preference for clients with higher capabilities
   - Constraint: `min_clients` ≤ selected ≤ `max_clients`
4. Selected clients' status updated to "selected"
5. Orchestrator notifies selected clients of round participation

### Phase 3: Local Training (On Client Devices)
Each selected client executes:
1. **Model Download**: Downloads current global model from server
2. **Local Training**:
   - Loads private local dataset (never leaves client device)
   - Trains model for specified epochs (typically 1-5)
   - Uses client's local optimizer (SGD/Adam) and loss function
3. **Gradient Computation**:
   - Computes gradients of local loss w.r.t. model parameters
   - Optionally computes gradients relative to global model (for FedProx)
4. **Update Preparation**:
   - Creates `ClientUpdate` object containing:
     - `client_id`: Unique identifier
     - `round_id`: Current round identifier
     - `gradients`: Dictionary of parameter gradients
     - `num_samples`: Number of training samples used
     - `timestamp`: ISO format timestamp
     - `model_version`: Version of model used for training
5. **Update Submission**: Sends `ClientUpdate` to orchestrator via `receive_update()`

### Phase 4: Secure Aggregation (On Server)
Upon receiving updates or reaching timeout:
1. Server verifies minimum clients: if `len(updates) < min_clients`, round fails
2. Server applies **SecureAggregation** pipeline:
   - **Gradient Clipping**: Limits L2 norm of each client's update to `max_grad_norm`
   - **Weighted Averaging**: Computes FedAvg weighted by `num_samples`
   - **Differential Privacy** (if enabled):
     - Computes sensitivity of aggregated update
     - Adds Gaussian noise scaled by `noise_multiplier * sensitivity`
   - **Homomorphic Encryption** (Paillier):
     - Encrypts aggregated weights using client's public keys
     - Performs aggregation in encrypted space
     - Decrypts only the final result
3. Server updates global model:
   - For FedAvg: `global_model = aggregated_update`
   - For FedProx: Adds proximal term to local objectives
4. Server increments round counter and saves round metadata

### Phase 5: Model Distribution
1. Server makes new global model available for download
2. Orchestrator notifies all clients (participants and observers) of model availability
3. Clients can download updated model for next round or local inference

### Phase 6: Round Completion
1. Server records round results in history:
   - Round ID and number
   - Participant count
   - Average samples per client
   - Aggregation method used
   - DP parameters (if used)
   - Timestamp
2. Server resets client statuses to "idle"
3. Server prepares for next round (if continuing)

## Security Mechanisms

### 1. Paillier Homomorphic Encryption
Used for secure aggregation without revealing individual updates:
- Each client generates a Paillier key pair
- Public keys shared with server, private keys kept client-side
- Gradients encrypted before transmission
- Server computes sum of encrypted values
- Only final decrypted sum revealed to server
- Prevents server from seeing individual client updates

### 2. Differential Privacy
Provides mathematical guarantee of privacy:
- Gaussian noise added to aggregated gradients
- Noise calibrated to sensitivity and privacy budget (ε)
- Implemented via `SecureAggregation.add_noise()`
- Privacy budget tracked across rounds
- Users can specify desired ε, δ values

### 3. Krum Defense (Byzantine Robustness)
Defends against malicious clients submitting harmful updates:
- For each client update, compute distance to all other updates
- Select update with smallest sum of distances to (n-2-closest) neighbors
- Where n = number of clients, f = estimated number of Byzantines
- Parameterized by `krum_f` (max Byzantine clients to tolerate)
- Used when `aggregation_method` includes Byzantine defense

### 4. Secure Communication
- All client-server communication over TLS 1.3
- Client authentication via JWT tokens
- Model updates signed with client keys
- Replay attack prevention via nonce/timestamp

## Client Usage

### For Organizations (Running FL Clients)

1. **Initialization**:
   ```python
   from app.federated_learning import create_federated_client
   
   client = create_federated_client("org-123")
   client.load_model("v1.0")  # Load initial model
   ```

2. **Registration**:
   ```python
   capabilities = {
       "compute_power": "high",  # low/medium/high
       "data_size": 10000,       # Number of training samples
       "modalities": ["face", "voice"],  # Supported data types
       "max_epochs": 10
   }
   orchestrator.register_client(client_id, capabilities)
   ```

3. **Participating in Rounds**:
   - Wait for selection notification from orchestrator
   - Upon selection:
     ```python
     # Get round configuration
     round_config = orchestrator.get_round_config(round_id)
     
     # Compute local update
     update = client.get_model_update(round_config)
     
     # Submit update
     orchestrator.submit_update(update)
     ```

4. **Model Updates**:
   - After each round, download latest global model:
   ```python
   global_model_bytes = orchestrator.get_global_model()
   client.load_model_from_bytes(global_model_bytes)
   ```

### Configuration Parameters

Clients can configure their local training via:
- `local_epochs`: Number of epochs for local training (default: 3)
- `batch_size`: Mini-batch size (default: 32)
- `learning_rate`: Optimizer learning rate (default: 0.01)
- `optimizer`: "sgd" or "adam" (default: "sgd")
- `loss_function`: Task-appropriate loss (default: cross-entropy)

## Round Configuration Examples

### Standard Federated Averaging
```yaml
round_id: "fl-round-001"
min_clients: 5
max_clients: 50
timeout_seconds: 300
aggregation_method: "fedavg"
differential_privacy: true
noise_multiplier: 1.0
max_grad_norm: 1.0
```

### Federated Learning with Byzantine Defense
```yaml
round_id: "fl-round-002"
min_clients: 10
max_clients: 100
timeout_seconds: 600
aggregation_method: "krum"  # Uses Krum defense
krum_f: 3  # Tolerate up to 3 Byzantine clients
differential_privacy: true
noise_multiplier: 0.5
max_grad_norm: 1.0
```

### Federated Proximal (FedProx)
```yaml
round_id: "fl-round-003"
min_clients: 3
max_clients: 20
timeout_seconds: 120
aggregation_method: "fedprox"
proximal_mu: 0.01  # Proximal term coefficient
differential_privacy: false
max_grad_norm: 1.0
```

## Monitoring & Metrics

Each round produces the following metrics:
- **Participation Rate**: `num_clients / max_clients`
- **Average Data Size**: Mean `num_samples` across clients
- **Convergence Speed**: Change in validation accuracy between rounds
- **Privacy Budget Spent**: Accumulated ε from differential privacy
- **Byzantine Resilience**: Number of outliers detected (if using Krum)
- **Communication Cost**: Bytes uploaded/downloaded per client

These metrics are available via:
- `/api/v2/fl/metrics` endpoint
- Grafana dashboard: `k8s/grafana/dashboards/ai-f-federated-learning.json`
- MLflow tracking server

## Error Handling & Recovery

### Client Failures
- If client fails during training: Status set to "failed", not counted for min_clients
- Client can rejoin next round after fixing issues
- Server waits for timeout before proceeding with available clients

### Server Failures
- Round state persisted to database
- On restart, server recovers incomplete rounds
- Clients retransmit updates if acknowledgment not received

### Network Partitions
- Clients queue updates locally during partition
- Updates sent when connectivity restored
- Server accepts late updates within grace period (typically 30 seconds)

## Deployment Considerations

### Client Requirements
- Python 3.8+ with PyTorch or TensorFlow
- Minimum 2GB RAM for model training
- Storage for local dataset and model checkpoints
- Network bandwidth for model upload/download (model size dependent)

### Server Requirements
- PostgreSQL database for round state persistence
- Redis for client coordination and caching
- Sufficient CPU for secure aggregation operations
- Horizontal scaling via load balancer for client connections

### Data Heterogeneity Handling
- Non-IID data addressed via:
  - Personalization layers (fine-tuning global model locally)
  - Adaptive weighting based on data similarity
  - Clustered federated learning (group similar clients)

## References

1. McMahan et al., "Communication-Efficient Learning of Deep Networks from Decentralized Data", AISTATS 2017 (FedAvg)
2. Li et al., "Federated Optimization in Heterogeneous Networks", MLSys 2020 (FedProx)
3. Blanchard et al., "Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent", NeurIPS 2017 (Krum)
4. Abadi et al., "Deep Learning with Differential Privacy", CCS 2016 (DP-SGD)
5. Gentry, "A Fully Homomorphic Encryption Scheme", Stanford Crypto 2009 (Paillier variant)
