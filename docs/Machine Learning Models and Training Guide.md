# Machine Learning Models and Training Guide
## Comprehensive Guide to Building, Training, and Deploying ML Models for Predictive Maintenance

> [!IMPORTANT]
> **Document Status (June 21, 2026):** This is a **reference guide for future ML work**. None of the models, training pipelines, or deployment procedures described below are currently implemented in the codebase. The current system uses:
> - **Fault detection**: Rule-based threshold checks (see `ai_agent.py` → `FaultDetector`)
> - **RUL estimation**: Linear trend extrapolation over a degradation score (see `ai_agent.py` → `RULEstimator`)
> - **Anomaly scoring**: Not implemented
>
> Before adopting any model from this guide, the requirements in §6 of the *AI Agent Design and ML Pipeline Document* must be met: a versioned labeled dataset, reproducible feature pipeline, train/test split, confusion matrix, and edge latency benchmark.

### 1. Overview
This document details the machine learning models **proposed** for the AI Digital Twin system for fault detection, classification, and Remaining Useful Life (RUL) estimation. It provides guidance on data preparation, model training, validation, and deployment that will apply once labeled field data is available.

> [!NOTE]
> The current prototype validates integration contracts, API behavior, and processing latency with 29 automated tests. It does not validate trained-model accuracy. All accuracy claims in this guide (>90%, <20% MAPE) are **target goals**, not measured results.

### 2. Model Architecture Overview
The system employs an ensemble of complementary models, each optimized for specific predictive maintenance tasks.

| Model | Purpose | Algorithm | Input Features | Output |
| :--- | :--- | :--- | :--- | :--- |
| **Anomaly Detector** | Detect unusual patterns | Isolation Forest | Vibration, Temperature, Current | Anomaly Score (0-1) |
| **Fault Classifier** | Classify fault types | Random Forest | 20+ engineered features | Fault Type + Confidence |
| **RUL Predictor** | Estimate remaining life | LSTM Network | Time-series degradation data | Days to Failure + Confidence |
| **Severity Predictor** | Predict alert severity | Gradient Boosting | Current state + trend | Severity Level |

### 3. Data Preparation and Feature Engineering
High-quality data and well-engineered features are critical for model performance.

#### 3.1 Data Collection Strategy
The training dataset should include diverse machine states and fault conditions:
- **Normal Operation**: At least 1000 readings per machine type
- **Bearing Wear**: 500+ readings showing progressive degradation
- **Misalignment**: 300+ readings with characteristic vibration patterns
- **Overheating**: 300+ readings with temperature rise
- **Electrical Faults**: 200+ readings with current anomalies

#### 3.2 Feature Engineering
Effective features capture the essence of machine health. The following categories of features are extracted:

**Time-Domain Features (Vibration):**
- Root Mean Square (RMS): Overall vibration intensity
- Peak Value: Maximum vibration amplitude
- Crest Factor: Peak / RMS ratio (indicates impulsiveness)
- Kurtosis: Measure of distribution shape (high for bearing faults)
- Skewness: Asymmetry of distribution

**Frequency-Domain Features (FFT-based):**
- Spectral Energy: Total energy in frequency bands
- Peak Frequency: Dominant frequency component
- Bearing Pass Frequency: Characteristic bearing fault frequency
- Sidebands: Modulation around bearing frequencies
- Spectral Entropy: Disorder in frequency distribution

**Statistical Features:**
- Mean, Standard Deviation, Variance
- Min, Max, Range
- Percentiles (25th, 50th, 75th)
- Autocorrelation at lag 1

**Operational Features:**
- Temperature gradient (rate of change)
- Current draw trend
- Machine speed (RPM) if available
- Load factor

**Trend Features:**
- Vibration trend (increasing/decreasing)
- Temperature trend
- Current trend
- Degradation rate

#### 3.3 Feature Normalization
All features must be normalized to comparable scales to prevent bias toward high-magnitude features:

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_normalized = scaler.fit_transform(X_raw)
```

### 4. Anomaly Detection Model
The Isolation Forest algorithm is particularly effective for unsupervised anomaly detection in industrial settings.

#### 4.1 Model Configuration
```python
from sklearn.ensemble import IsolationForest

anomaly_detector = IsolationForest(
    n_estimators=100,
    contamination=0.05,  # Expected proportion of anomalies
    random_state=42,
    n_jobs=-1
)
```

#### 4.2 Training Procedure
```python
# Train on normal operation data
X_normal = load_normal_operation_data()
anomaly_detector.fit(X_normal)

# Generate anomaly scores
anomaly_scores = anomaly_detector.score_samples(X_test)
predictions = anomaly_detector.predict(X_test)  # -1 for anomaly, 1 for normal
```

#### 4.3 Interpretation
- **Anomaly Score**: Ranges from -1 (strong anomaly) to +1 (normal)
- **Threshold**: Typically set at -0.5 to balance sensitivity and specificity
- **Confidence**: Can be derived from distance to decision boundary

### 5. Fault Classification Model
The Random Forest classifier provides robust fault classification with interpretability.

#### 5.1 Model Configuration
```python
from sklearn.ensemble import RandomForestClassifier

fault_classifier = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=5,
    min_samples_leaf=2,
    class_weight='balanced',  # Handle imbalanced classes
    random_state=42,
    n_jobs=-1
)
```

#### 5.2 Training Procedure
```python
# Prepare labeled data
X_train, X_test, y_train, y_test = train_test_split(
    X_features, y_labels, test_size=0.2, random_state=42
)

# Train classifier
fault_classifier.fit(X_train, y_train)

# Evaluate
from sklearn.metrics import classification_report, confusion_matrix
y_pred = fault_classifier.predict(X_test)
print(classification_report(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))
```

#### 5.3 Feature Importance Analysis
Understanding which features are most important for classification helps validate the model's reasoning:

```python
# Get feature importances
importances = fault_classifier.feature_importances_
feature_names = [...]  # List of feature names
sorted_idx = np.argsort(importances)[::-1]

# Plot top 10 features
for i in range(10):
    print(f"{feature_names[sorted_idx[i]]}: {importances[sorted_idx[i]]:.4f}")
```

#### 5.4 Prediction with Confidence
```python
# Get predictions with confidence scores
predictions = fault_classifier.predict(X_new)
probabilities = fault_classifier.predict_proba(X_new)

# Extract confidence for predicted class
confidence = np.max(probabilities, axis=1)
```

### 6. RUL Estimation Model
Long Short-Term Memory (LSTM) networks excel at capturing temporal dependencies in degradation data.

#### 6.1 Data Preparation for LSTM
RUL estimation requires time-series data formatted as sequences:

```python
def create_sequences(data, seq_length=50):
    """Create sequences for LSTM training"""
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:i+seq_length])
        y.append(data[i+seq_length])  # Next value prediction
    return np.array(X), np.array(y)

# Prepare data
degradation_data = load_degradation_history()  # Shape: (n_samples,)
X_seq, y_seq = create_sequences(degradation_data, seq_length=50)
```

#### 6.2 Model Architecture
```python
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

model = Sequential([
    LSTM(64, activation='relu', input_shape=(50, 1), return_sequences=True),
    Dropout(0.2),
    LSTM(32, activation='relu', return_sequences=False),
    Dropout(0.2),
    Dense(16, activation='relu'),
    Dense(1)  # Output: next degradation value
])

model.compile(optimizer='adam', loss='mse', metrics=['mae'])
```

#### 6.3 Training Procedure
```python
# Train model
history = model.fit(
    X_train, y_train,
    epochs=100,
    batch_size=32,
    validation_split=0.2,
    callbacks=[
        tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
    ]
)

# Evaluate
test_loss, test_mae = model.evaluate(X_test, y_test)
```

#### 6.4 RUL Calculation from Predictions
```python
def estimate_rul(degradation_history, model, critical_threshold=0.8):
    """Estimate RUL from degradation history"""
    # Prepare sequence
    seq = degradation_history[-50:].reshape(1, 50, 1)
    
    # Predict future degradation
    rul_days = 0
    current_degradation = degradation_history[-1]
    
    while current_degradation < critical_threshold and rul_days < 365:
        next_degradation = model.predict(seq, verbose=0)[0][0]
        current_degradation = next_degradation
        seq = np.append(seq[0][1:], [[next_degradation]], axis=0).reshape(1, 50, 1)
        rul_days += 1
    
    return rul_days
```

### 7. Model Validation and Evaluation
Rigorous validation ensures models perform well on unseen data.

#### 7.1 Cross-Validation
```python
from sklearn.model_selection import cross_val_score

# K-Fold cross-validation
scores = cross_val_score(
    fault_classifier, X_features, y_labels,
    cv=5, scoring='f1_weighted'
)
print(f"Cross-validation scores: {scores}")
print(f"Mean: {scores.mean():.3f} (+/- {scores.std():.3f})")
```

#### 7.2 Performance Metrics
For fault classification:
- **Accuracy**: Overall correctness
- **Precision**: False positive rate for each class
- **Recall**: False negative rate for each class
- **F1-Score**: Harmonic mean of precision and recall
- **ROC-AUC**: Receiver Operating Characteristic curve

For RUL estimation:
- **Mean Absolute Error (MAE)**: Average prediction error
- **Mean Absolute Percentage Error (MAPE)**: Percentage error
- **Root Mean Squared Error (RMSE)**: Penalizes large errors

#### 7.3 Confusion Matrix Analysis
```python
from sklearn.metrics import confusion_matrix
import seaborn as sns

cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
plt.title('Fault Classification Confusion Matrix')
plt.show()
```

### 8. Model Optimization and Hyperparameter Tuning
Systematic optimization improves model performance.

#### 8.1 Grid Search
```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [10, 15, 20],
    'min_samples_split': [2, 5, 10]
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42),
    param_grid,
    cv=5,
    scoring='f1_weighted',
    n_jobs=-1
)

grid_search.fit(X_train, y_train)
print(f"Best parameters: {grid_search.best_params_}")
print(f"Best score: {grid_search.best_score_:.3f}")
```

#### 8.2 Random Search
For large hyperparameter spaces, random search is more efficient:

```python
from sklearn.model_selection import RandomizedSearchCV

random_search = RandomizedSearchCV(
    RandomForestClassifier(random_state=42),
    param_distributions=param_grid,
    n_iter=20,
    cv=5,
    random_state=42,
    n_jobs=-1
)

random_search.fit(X_train, y_train)
```

### 9. Model Deployment and Inference
Converting trained models to production-ready format.

#### 9.1 Model Serialization
```python
import joblib
import pickle

# Save scikit-learn models
joblib.dump(fault_classifier, 'fault_classifier.pkl')
joblib.dump(anomaly_detector, 'anomaly_detector.pkl')

# Load models
fault_classifier = joblib.load('fault_classifier.pkl')
```

#### 9.2 ONNX Format for Edge Deployment
ONNX (Open Neural Network Exchange) enables efficient inference on edge devices:

```python
import onnx
import skl2onnx
from skl2onnx.common.data_types import FloatTensorType

initial_type = [('float_input', FloatTensorType([None, 20]))]
onnx_model = skl2onnx.convert_sklearn(fault_classifier, initial_types=initial_type)
onnx.save_model(onnx_model, 'fault_classifier.onnx')
```

#### 9.3 Real-time Inference
```python
def predict_fault(sensor_reading, fault_classifier):
    """Predict fault type from sensor reading"""
    # Extract and normalize features
    features = extract_features(sensor_reading)
    features_normalized = scaler.transform([features])
    
    # Predict
    prediction = fault_classifier.predict(features_normalized)[0]
    confidence = fault_classifier.predict_proba(features_normalized)[0]
    
    return {
        'fault_type': prediction,
        'confidence': float(max(confidence))
    }
```

### 10. Continuous Learning and Model Updates
Models must be updated as new data becomes available.

#### 10.1 Incremental Learning
```python
def update_model_with_new_data(model, X_new, y_new):
    """Update model with new labeled data"""
    # For Random Forest, retrain with combined data
    X_combined = np.vstack([X_train, X_new])
    y_combined = np.hstack([y_train, y_new])
    
    model.fit(X_combined, y_combined)
    return model
```

#### 10.2 Model Versioning
Maintain multiple model versions for safe rollback:

```
models/
├── v1.0/
│   ├── fault_classifier.pkl
│   ├── anomaly_detector.pkl
│   └── rul_predictor.h5
├── v1.1/
│   ├── fault_classifier.pkl
│   ├── anomaly_detector.pkl
│   └── rul_predictor.h5
└── current -> v1.1/
```

#### 10.3 A/B Testing for Model Updates
```python
def ab_test_models(old_model, new_model, test_data, test_labels):
    """Compare old and new models"""
    old_score = old_model.score(test_data, test_labels)
    new_score = new_model.score(test_data, test_labels)
    
    improvement = (new_score - old_score) / old_score * 100
    
    if improvement > 2:  # 2% improvement threshold
        return new_model
    else:
        return old_model
```

### 11. Monitoring Model Performance
Continuous monitoring ensures models remain effective in production.

#### 11.1 Performance Tracking
```python
class ModelMonitor:
    def __init__(self, baseline_accuracy=0.95):
        self.baseline_accuracy = baseline_accuracy
        self.predictions_log = []
    
    def log_prediction(self, prediction, actual):
        """Log prediction for monitoring"""
        self.predictions_log.append({
            'timestamp': datetime.now(),
            'prediction': prediction,
            'actual': actual,
            'correct': prediction == actual
        })
    
    def check_model_health(self):
        """Check if model performance has degraded"""
        recent_predictions = self.predictions_log[-100:]
        accuracy = sum(p['correct'] for p in recent_predictions) / len(recent_predictions)
        
        if accuracy < self.baseline_accuracy * 0.9:
            return "Model performance degraded - retraining recommended"
        return "Model performing normally"
```

#### 11.2 Drift Detection
Monitor for data distribution changes that may require model retraining:

```python
from scipy.stats import ks_2samp

def detect_data_drift(old_data, new_data, threshold=0.05):
    """Detect distribution shift using Kolmogorov-Smirnov test"""
    for feature_idx in range(old_data.shape[1]):
        statistic, p_value = ks_2samp(old_data[:, feature_idx], new_data[:, feature_idx])
        if p_value < threshold:
            return True  # Drift detected
    return False
```

### 12. Troubleshooting and Optimization
Common issues and their solutions.

#### 12.1 Overfitting
**Symptoms**: High training accuracy, low test accuracy
**Solutions**:
- Increase regularization (max_depth, min_samples_split)
- Reduce model complexity
- Collect more training data
- Use cross-validation

#### 12.2 Underfitting
**Symptoms**: Low accuracy on both training and test sets
**Solutions**:
- Increase model complexity
- Add more features
- Reduce regularization
- Train for longer

#### 12.3 Class Imbalance
**Symptoms**: Model biased toward majority class
**Solutions**:
- Use class weights: `class_weight='balanced'`
- Oversample minority class
- Undersample majority class
- Use SMOTE (Synthetic Minority Over-sampling Technique)

### 13. Documentation and Reproducibility
Ensure models can be reproduced and understood.

#### 13.1 Model Card
Document key information about each model:
- Model name and version
- Purpose and use case
- Training data characteristics
- Performance metrics
- Known limitations
- Recommended updates frequency

#### 13.2 Training Script Documentation
```python
"""
Fault Classification Model Training Script
=========================================
Purpose: Train Random Forest classifier for bearing fault detection
Data: Industrial vibration sensor data from MSME machinery
Target: Classify faults into 4 categories (Normal, Bearing Wear, Misalignment, Overheating)
"""
```

### 14. References and Further Reading
- Scikit-learn Documentation: https://scikit-learn.org/
- TensorFlow/Keras Documentation: https://www.tensorflow.org/
- ONNX Runtime: https://onnxruntime.ai/
- Predictive Maintenance Research: IEEE Transactions on Industrial Informatics
