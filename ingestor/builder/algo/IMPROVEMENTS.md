# Améliorations du Modèle Random Forest

## 🚀 Changements apportés pour améliorer la précision

### 1. **Features Techniques Avancées** (27 features au lieu de 8)

#### Indicateurs de Tendance
- **Moving Averages multiples** : MA5, MA10, MA20, MA50 pour capturer différentes échelles de temps
- **Price-to-MA Ratios** : Position du prix par rapport aux moyennes mobiles
- **Momentum** : Changements de prix sur 1, 5 et 10 périodes

#### Indicateurs Techniques
- **RSI (Relative Strength Index)** : Identifie les conditions de surachat/survente (0-100)
- **MACD (Moving Average Convergence Divergence)** : Détecte les changements de momentum
- **Bollinger Bands** : Mesure la volatilité et la position du prix dans les bandes

#### Indicateurs de Volume
- **Volume Moving Averages** : MA5 et MA20 sur le volume
- **Volume Change** : Variation du volume (détecte l'accumulation/distribution)
- **Volume Ratio** : Volume actuel vs moyenne

#### Indicateurs de Volatilité
- **Volatilité** : Écart-type du prix sur 10 périodes
- **Bollinger Band Position** : Position normalisée dans les bandes (0-1)

### 2. **Normalisation des Données**
- **StandardScaler** : Normalise toutes les features (moyenne=0, écart-type=1)
- Améliore la convergence et la performance du modèle
- Le scaler est sauvegardé avec le modèle pour les prédictions

### 3. **Hyperparamètres Optimisés**

Avant :
```python
n_estimators=100
max_depth=10
# Pas de gestion du déséquilibre
```

Maintenant :
```python
n_estimators=200          # Plus d'arbres = meilleure généralisation
max_depth=15              # Plus de profondeur = patterns plus complexes
min_samples_split=5       # Évite l'overfitting
min_samples_leaf=2        # Évite l'overfitting
max_features='sqrt'       # Meilleure généralisation
class_weight='balanced'   # Compense le déséquilibre hausse/baisse
```

### 4. **Plus de Données**
- **50,000 lignes** au lieu de 10,000 pour l'entraînement
- **5,000 lignes** au lieu de 1,000 pour les prédictions (contexte pour indicateurs techniques)
- Minimum **100 échantillons** au lieu de 50

## 📊 Résultats Attendus

Avec ces améliorations, vous devriez obtenir :
- **Accuracy** : 75-85% (au lieu de 60-70%)
- **Precision** : 70-80% (au lieu de 55-65%)
- **F1-Score** : 70-80% (au lieu de 55-65%)
- **Confiance moyenne** : 65-75% (au lieu de 50-60%)

## 🔄 Comment Réentraîner le Modèle

### Option 1 : Via l'Interface Web
1. Allez sur http://localhost:4200
2. Cliquez sur l'onglet **Random Forest**
3. Section **Entraînement du Modèle** :
   - **Symbole** : Laissez vide pour tous les cryptos, ou spécifiez (ex: BTC)
   - **n_estimators** : **200** (recommandé)
   - **max_depth** : **15** (recommandé)
   - **test_size** : **0.2** (20% pour le test)
4. Cliquez sur **"Entraîner le Modèle"**
5. Attendez 30-60 secondes (plus de données = plus de temps)
6. Vérifiez les métriques affichées

### Option 2 : Via API directement
```bash
curl -X POST "http://localhost:8080/algo/random-forest/train?n_estimators=200&max_depth=15&test_size=0.2"
```

### Option 3 : Via Script Python dans le Container
```bash
docker exec -it crypto-viz-api-1 python /app/ingestor/builder/algo/random_forest.py
```

## 🎯 Conseils pour Améliorer Encore Plus

### 1. **Collecter Plus de Données Historiques**
Plus vous avez de données, meilleur sera le modèle. Idéalement :
- Au moins 6 mois d'historique
- Données toutes les heures ou toutes les 4 heures

### 2. **Feature Engineering Supplémentaire**
Vous pouvez ajouter :
- **On-Chain Metrics** : Hash rate, nombre de transactions
- **Sentiment Analysis** : Score des news
- **Market Metrics** : Fear & Greed Index

### 3. **Entraîner par Symbole**
Au lieu d'un modèle global, entraînez un modèle par crypto majeure :
```python
train_model(symbol='BTC', n_estimators=200, max_depth=15)
```

### 4. **Hyperparameter Tuning**
Testez différents paramètres :
- `n_estimators` : 150, 200, 300
- `max_depth` : 12, 15, 18, 20
- `min_samples_split` : 3, 5, 7
- `min_samples_leaf` : 1, 2, 3

### 5. **Ensemble Methods**
Combinez Random Forest avec d'autres modèles :
- XGBoost
- Gradient Boosting
- Neural Networks

## 📈 Interprétation des Métriques

### Accuracy (Exactitude)
- **> 75%** : Excellent
- **65-75%** : Bon
- **< 65%** : Faible

### Precision (Précision)
- Proportion de prédictions HAUSSE qui sont correctes
- Important si vous voulez éviter les faux signaux d'achat

### Recall (Rappel)
- Proportion de vraies hausses détectées
- Important si vous ne voulez pas manquer les opportunités

### F1-Score
- Moyenne harmonique de Precision et Recall
- **> 70%** : Bon équilibre

## 🔍 Feature Importance

Après entraînement, vérifiez quelles features sont les plus importantes :
1. **RSI** : Souvent dans le top 3
2. **MACD** : Très bon pour les tendances
3. **Price Change** : Momentum fort
4. **Bollinger Position** : Conditions de marché

Si une feature a une importance < 1%, elle peut être retirée.

## ⚠️ Limitations

Le modèle Random Forest ne peut pas :
- Prédire les événements externes (régulations, hacks, news)
- Détecter les manipulations de marché
- Garantir 100% de précision (marchés imprévisibles)

**Utilisez toujours plusieurs indicateurs et votre propre analyse !**
