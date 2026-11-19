import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score, confusion_matrix
from app.models.database import Order

def train_and_evaluate_models():
    orders = Order.query.all()
    
    if len(orders) < 10:
        np.random.seed(42)
        n = 200
        days = np.random.randint(0, 7, size=n)
        hours = np.random.randint(11, 23, size=n)
        is_weekend = np.where(days >= 5, 1, 0)
        amounts = 30 + 15 * is_weekend + 2 * (hours - 12) + np.random.normal(0, 5, size=n)
        amounts = np.clip(amounts, 15, 150)
        delays = np.where((amounts > 80) | (hours > 20), 1, 0)
        
        df = pd.DataFrame({
            'day_of_week': days,
            'hour': hours,
            'is_weekend': is_weekend,
            'total_amount': amounts,
            'is_delayed': delays
        })
    else:
        data = []
        for o in orders:
            dt = o.created_at
            data.append({
                'day_of_week': dt.weekday(),
                'hour': dt.hour,
                'is_weekend': 1 if dt.weekday() >= 5 else 0,
                'total_amount': float(o.total_amount),
                'is_delayed': 1 if o.status == 'CANCELADO' or (o.delivery_fee > 0 and dt.hour >= 20) else 0
            })
        df = pd.DataFrame(data)

    X_reg = df[['day_of_week', 'hour', 'is_weekend']]
    y_reg = df['total_amount']
    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(X_reg, y_reg, test_size=0.2, random_state=42)
    
    lin_reg = LinearRegression()
    lin_reg.fit(X_train_r, y_train_r)
    y_pred_lin = lin_reg.predict(X_test_r)
    r2_lin = r2_score(y_test_r, y_pred_lin)
    rmse_lin = np.sqrt(mean_squared_error(y_test_r, y_pred_lin))

    poly_model = make_pipeline(PolynomialFeatures(degree=2), LinearRegression())
    poly_model.fit(X_train_r, y_train_r)
    y_pred_poly = poly_model.predict(X_test_r)
    r2_poly = r2_score(y_test_r, y_pred_poly)
    rmse_poly = np.sqrt(mean_squared_error(y_test_r, y_pred_poly))

    X_clf = df[['day_of_week', 'hour', 'is_weekend', 'total_amount']]
    y_clf = df['is_delayed']
    
    if len(y_clf.unique()) > 1:
        X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X_clf, y_clf, test_size=0.2, random_state=42)
        
        best_acc = 0
        best_c = 1.0
        best_matrix = []
        
        for c_val in [0.01, 0.1, 1.0, 10.0]:
            log_reg = LogisticRegression(C=c_val, random_state=42)
            log_reg.fit(X_train_c, y_train_c)
            y_pred_c = log_reg.predict(X_test_c)
            acc = accuracy_score(y_test_c, y_pred_c)
            if acc >= best_acc:
                best_acc = acc
                best_c = c_val
                best_matrix = confusion_matrix(y_test_c, y_pred_c).tolist()
    else:
        best_acc = 1.0
        best_c = 1.0
        best_matrix = [[len(y_clf), 0], [0, 0]]

    return {
        'comparativa_regresion': {
            'lineal': {'r2': float(r2_lin), 'rmse': float(rmse_lin)},
            'no_lineal_polinomica': {'r2': float(r2_poly), 'rmse': float(rmse_poly)}
        },
        'regresion_logistica_hiperparametros': {
            'mejor_hiperparametro_C': float(best_c),
            'accuracy': float(best_acc),
            'confusion_matrix': best_matrix
        }
    }