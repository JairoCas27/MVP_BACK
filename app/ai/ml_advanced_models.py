import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from app.models.database import Order

def train_and_evaluate_advanced_models():
    orders = Order.query.all()
    
    data = []
    for o in orders:
        dt = o.created_at or datetime.now()
        is_del = 1 if o.order_type == 'DELIVERY' else 0
        is_wknd = 1 if dt.weekday() >= 5 else 0
        
        delay_score = is_del * 0.4 + (1 if dt.hour >= 20 else 0) * 0.4 + (float(o.total_amount) / 150.0) * 0.2
        delayed = 1 if o.status == 'CANCELADO' or delay_score > 0.5 else 0
        
        data.append({
            'day_of_week': dt.weekday(),
            'hour': dt.hour,
            'is_weekend': is_wknd,
            'is_delivery': is_del,
            'total_amount': float(o.total_amount),
            'is_delayed': delayed
        })
    df = pd.DataFrame(data)

    X = df[['day_of_week', 'hour', 'is_weekend', 'total_amount']]
    y = df['is_delayed']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    models = {
        'SVM': SVC(kernel='rbf', C=1.0, random_state=42),
        'KNN': KNeighborsClassifier(n_neighbors=5),
        'Decision_Tree': DecisionTreeClassifier(max_depth=4, random_state=42),
        'Boosting': GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, random_state=42)
    }

    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        results[name] = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision': float(precision_score(y_test, y_pred, zero_division=0)),
            'recall': float(recall_score(y_test, y_pred, zero_division=0)),
            'f1_score': float(f1_score(y_test, y_pred, zero_division=0))
        }

    return results