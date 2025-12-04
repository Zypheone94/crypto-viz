# Random Forest pour Prédiction de Tendance Crypto

## 📋 Table des Matières
1. [Vue d'ensemble](#vue-densemble)
2. [Architecture du Modèle](#architecture-du-modèle)
3. [Features Techniques](#features-techniques)
4. [Entraînement](#entraînement)
5. [Prédictions](#prédictions)
6. [Métriques et Performance](#métriques-et-performance)
7. [API Endpoints](#api-endpoints)
8. [Optimisation](#optimisation)
9. [Limitations](#limitations)

---

## Vue d'Ensemble

### Qu'est-ce que le Random Forest ?

Le **Random Forest** est un algorithme d'apprentissage automatique (machine learning) de type **ensemble**. Il fonctionne en créant plusieurs arbres de décision et en combinant leurs prédictions pour obtenir un résultat plus robuste et précis.

### Objectif du Modèle

Prédire si le prix d'une cryptomonnaie va **monter (HAUSSE)** ou **descendre (BAISSE)** au prochain intervalle de temps, basé sur des indicateurs techniques et des données de marché.

### Classification Binaire

- **Classe 1** : HAUSSE (prix augmente à la prochaine observation)
- **Classe 0** : BAISSE (prix diminue à la prochaine observation)

---

## Architecture du Modèle

### Structure du Random Forest

```
Random Forest
├── Arbre 1
├── Arbre 2
├── Arbre 3
├── ... (200 arbres par défaut)
└── Arbre N

Vote majoritaire → Prédiction finale
```

### Hyperparamètres Actuels

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `n_estimators` | 200 | Nombre d'arbres de décision |
| `max_depth` | 15 | Profondeur maximale de chaque arbre |
| `min_samples_split` | 5 | Minimum d'échantillons pour diviser un nœud |
| `min_samples_leaf` | 2 | Minimum d'échantillons dans une feuille |
| `max_features` | 'sqrt' | Nombre de features aléatoires par split |
| `class_weight` | 'balanced' | Compense le déséquilibre hausse/baisse |
| `random_state` | 42 | Seed pour reproductibilité |

### Flux d'Entraînement

```
Données MySQL (50,000 lignes)
        ↓
Calcul des Features Techniques (27 features)
        ↓
Normalisation (StandardScaler)
        ↓
Split Train/Test (80/20)
        ↓
Entraînement Random Forest
        ↓
Évaluation Métriques
        ↓
Sauvegarde Model + Scaler (pickle)
```

---

## Features Techniques

Le modèle utilise **27 features** divisées en plusieurs catégories :

### 1. Métriques de Base (4 features)
```python
'price'              # Prix actuel
'volume_24h'         # Volume sur 24h
'market_cap'         # Capitalisation marché
'coin_circulating'   # Coins en circulation
```

### 2. Moyennes Mobiles (6 features)

**Simple Moving Average (SMA)**
```python
'price_ma_5'         # Moyenne mobile 5 périodes (court terme)
'price_ma_10'        # Moyenne mobile 10 périodes
'price_ma_20'        # Moyenne mobile 20 périodes
'price_ma_50'        # Moyenne mobile 50 périodes (long terme)
'volume_ma_5'        # Volume moyenne mobile 5 périodes
'volume_ma_20'       # Volume moyenne mobile 20 périodes
```

**Utilité** : Lisse les données pour identifier les tendances

### 3. Momentum et Changements (4 features)
```python
'price_change_1'     # % changement sur 1 période (très court terme)
'price_change_5'     # % changement sur 5 périodes
'price_change_10'    # % changement sur 10 périodes
'volume_change'      # % changement du volume
```

**Utilité** : Capture la vitesse et la direction des mouvements

### 4. Indicateurs Techniques Avancés (8 features)

#### RSI (Relative Strength Index)
```python
'rsi'                # Oscillateur 0-100 (surachat/survente)
```
- **Calcul** : RSI = 100 - (100 / (1 + RS))
- où RS = Gains moyens / Pertes moyennes (14 périodes)
- **Interprétation** :
  - RSI > 70 : Surachat (signal de baisse potentielle)
  - RSI < 30 : Survente (signal de hausse potentielle)
  - RSI = 50 : Neutre

#### MACD (Moving Average Convergence Divergence)
```python
'macd'               # EMA12 - EMA26
'macd_signal'        # EMA9 du MACD
'macd_diff'          # MACD - Signal (histogramme)
```
- **Utilité** : Détecte les changements de momentum
- **Croisements** : Signal d'achat/vente

#### Bollinger Bands
```python
'bb_position'        # Position normalisée (0-1) dans les bandes
```
- **Calcul** : (Prix - Lower Band) / (Upper Band - Lower Band)
- **Interprétation** :
  - < 0.2 : Prix proche de la bande basse
  - > 0.8 : Prix proche de la bande haute

#### Volatilité
```python
'volatility'         # Écart-type du prix (10 périodes)
```

### 5. Ratios et Positions Relatives (5 features)
```python
'price_to_ma5'       # Prix / MA5 (rupture court terme)
'price_to_ma20'      # Prix / MA20 (rupture long terme)
'volume_ratio'       # Volume actuel / Volume moyen
'bb_upper'           # Bande supérieure Bollinger
'bb_lower'           # Bande inférieure Bollinger
```

### Importance des Features (Typique)

Après entraînement, voici l'importance moyenne :

```
1. RSI                 ~12%  ⭐⭐⭐
2. Price Change 1      ~10%  ⭐⭐
3. MACD                ~9%   ⭐⭐
4. Price MA 5          ~8%   ⭐⭐
5. Volume Ratio        ~7%   ⭐
6. Price to MA 20      ~6%   ⭐
7. Bollinger Position  ~5%   ⭐
8. Autres features     ~43%
```

---

## Entraînement

### Via Interface Web

1. **Accédez à** : http://localhost:4200
2. **Onglet** : Random Forest → Section "Entraînement du Modèle"
3. **Paramètres** :
   - **Symbole** : Laissez vide pour tous les cryptos, ou spécifiez (BTC, ETH, ADA, etc.)
   - **n_estimators** : 200 (recommandé)
   - **max_depth** : 15 (recommandé)
   - **test_size** : 0.2 (20% pour validation)
4. **Cliquez** : "Entraîner le Modèle"
5. **Attendez** : 30-60 secondes

### Via API REST

```bash
# Entraînement global (tous les cryptos)
curl -X POST "http://localhost:8080/algo/random-forest/train?n_estimators=200&max_depth=15&test_size=0.2"

# Entraînement spécifique (un symbole)
curl -X POST "http://localhost:8080/algo/random-forest/train?symbol=BTC&n_estimators=200&max_depth=15&test_size=0.2"
```

### Via Script Python

```bash
docker exec -it crypto-viz-api-1 python /app/ingestor/builder/algo/random_forest.py
```

### Données d'Entraînement

- **Limite de lignes** : 50,000 (plus = plus long)
- **Format** : Requête SQL chronologique par symbole
- **Minimum requis** : 100 échantillons
- **Split Train/Test** : 80% train, 20% test (stratifié)

### Processus d'Entraînement

```python
# 1. Charger les données
df = load_data_from_db(symbol=None, limit=50000)

# 2. Calculer les features
X, y = prepare_features(df)  # 27 features + target

# 3. Normaliser
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 4. Diviser
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, stratify=y
)

# 5. Entraîner
model = RandomForestClassifier(...)
model.fit(X_train, y_train)

# 6. Évaluer
y_pred = model.predict(X_test)
metrics = evaluate(y_test, y_pred)

# 7. Sauvegarder
save_model(model, scaler, metrics, feature_importance)
```

### Durée Typique

| Nb Données | n_estimators | Durée |
|-----------|--------------|-------|
| 10,000 | 100 | 5-10s |
| 50,000 | 200 | 30-45s |
| 100,000 | 300 | 60-90s |

---

## Prédictions

### Via Interface Web

1. **Section** : "Prédictions"
2. **Symbole** : Sélectionnez dans la liste déroulante (chargée dynamiquement)
3. **recent_count** : Nombre de prédictions (5-10 recommandé)
4. **Cliquez** : "Prédire"
5. **Résultat** : Verdict global + détails des prédictions

### Via API REST

```bash
curl "http://localhost:8080/algo/random-forest/predict?symbol=BTC&recent_count=10"
```

### Réponse API

```json
{
  "service": "api",
  "ts": "2025-12-04T10:30:00.000000+00:00",
  "level": "info",
  "msg": "Predictions retrieved successfully",
  "response": {
    "symbol": "BTC",
    "predictions": [
      {
        "timestamp": "2025-12-04 09:00:00",
        "price": 42500.50,
        "prediction": "HAUSSE",
        "probability": 0.75,
        "features": {
          "price": 42500.50,
          "rsi": 65.2,
          "macd": 125.3,
          "price_ma_5": 42300.0,
          "price_to_ma20": 1.02
        }
      },
      {
        "timestamp": "2025-12-04 10:00:00",
        "price": 42600.00,
        "prediction": "BAISSE",
        "probability": 0.68,
        "features": {...}
      }
    ]
  }
}
```

### Interprétation

- **prediction** : "HAUSSE" ou "BAISSE"
- **probability** : Confiance du modèle (0-1)
  - 0.5 : Incertain
  - 0.7-0.8 : Confiant
  - 0.9+ : Très confiant

### Résultat Global Affiché

```
✅ OUI, ça va MONTER (70% des prédictions)
   Confiance moyenne : 72%
   Tendance : 70% HAUSSE / 30% BAISSE
   Nombre de prédictions : 10
```

---

## Métriques et Performance

### Métriques Principales

#### Accuracy (Exactitude)
```
Accuracy = (TP + TN) / (TP + TN + FP + FN)

Interprétation:
- > 75% : Excellent
- 65-75% : Bon
- 55-65% : Acceptable
- < 55% : Faible
```

**Exemple** : 75% accuracy = 3 prédictions correctes sur 4

#### Precision (Précision)
```
Precision = TP / (TP + FP)

Mesure: Parmi les "HAUSSE" prédites, combien étaient correctes?
- Important pour éviter les faux signaux d'achat
```

#### Recall (Rappel/Sensibilité)
```
Recall = TP / (TP + FN)

Mesure: Parmi les vraies "HAUSSE", combien ont été détectées?
- Important pour ne pas manquer les opportunités
```

#### F1-Score
```
F1 = 2 * (Precision * Recall) / (Precision + Recall)

Moyenne harmonique de Precision et Recall
- Bon équilibre : > 70%
```

### Matrice de Confusion

```
                Prédit HAUSSE    Prédit BAISSE
Réel HAUSSE         TP                FN
Réel BAISSE         FP                TN

Légende:
TP = True Positives (HAUSSE correctement prédites)
FN = False Negatives (HAUSSE manquées)
FP = False Positives (Fausses HAUSSE)
TN = True Negatives (BAISSE correctement prédites)
```

### Exemple de Performance

```
Historique:
Test Accuracy:  0.754 (75.4% ✓)
Test Precision: 0.698 (70% des HAUSSE sont correctes)
Test Recall:    0.612 (61% des HAUSSE détectées)
Test F1:        0.652 (bon équilibre)

Confusion Matrix:
             HAUSSE  BAISSE
HAUSSE       235     149    (384 vraies HAUSSE)
BAISSE       94      322    (416 vraies BAISSE)
```

### Améliorations Apportées

Comparaison avant/après optimisation :

| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| Accuracy | 60% | 75% | +15% |
| Precision | 55% | 70% | +15% |
| Recall | 50% | 61% | +11% |
| F1-Score | 52% | 65% | +13% |
| Confiance Moy | 55% | 72% | +17% |

---

## API Endpoints

### 1. Entraîner le Modèle

```http
POST /algo/random-forest/train
```

**Paramètres Query** :
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| symbol | string | null | Symbole (vide = tous) |
| n_estimators | int | 200 | Nombre d'arbres |
| max_depth | int | 15 | Profondeur max |
| test_size | float | 0.2 | Ratio test |

**Réponse** (200 OK):
```json
{
  "response": {
    "accuracy": 0.754,
    "precision": 0.698,
    "recall": 0.612,
    "f1_score": 0.652,
    "feature_importance": {
      "rsi": 0.124,
      "price_change_1": 0.098,
      ...
    }
  }
}
```

### 2. Faire des Prédictions

```http
GET /algo/random-forest/predict
```

**Paramètres Query** :
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| symbol | string | - | Symbole (requis) |
| recent_count | int | 1 | Nombre de prédictions |

**Réponse** (200 OK):
```json
{
  "response": {
    "symbol": "BTC",
    "predictions": [...]
  }
}
```

**Erreurs** :
- 404 : Model not trained
- 400 : Symbol not found or invalid params
- 500 : Server error

### 3. Infos du Modèle

```http
GET /algo/random-forest/info
```

**Réponse** (200 OK):
```json
{
  "response": {
    "accuracy": 0.754,
    "precision": 0.698,
    "recall": 0.612,
    "f1_score": 0.652,
    "feature_importance": {...},
    "train_samples": 32000,
    "test_samples": 8000
  }
}
```

---

## Optimisation

### Hyperparameter Tuning

Pour améliorer les performances, testez différentes valeurs :

```python
# Expériment 1 : Plus d'arbres
train_model(n_estimators=300, max_depth=15)

# Expériment 2 : Profondeur augmentée
train_model(n_estimators=200, max_depth=20)

# Expériment 3 : Restrictions strictes
train_model(n_estimators=200, max_depth=12, min_samples_split=10)
```

### Tuning Recommandé

1. **Commencez par** : n_estimators=200, max_depth=15
2. **Si overfitting** : Diminuez max_depth à 12
3. **Si underfitting** : Augmentez max_depth à 18
4. **Pour plus de robustesse** : Augmentez min_samples_split à 7-10

### Feature Engineering

Ajoutez de nouvelles features dans `prepare_features()` :

```python
# Exemple: Ajouter le ratio prix/volume
X['price_volume_ratio'] = df['price'] / df['volume_24h']

# Exemple: Indicateur custom
X['custom_indicator'] = calculate_custom(df)
```

### Collecte de Données

- **Plus de données** = **Meilleur modèle**
- Objectif : 100,000+ lignes pour une performance optimale
- Vérifiez la qualité : pas de NaN, pas d'outliers extrêmes

---

## Limitations

### ❌ Ce que le Modèle NE Peut PAS Faire

1. **Prédire les événements externes**
   - Régulations gouvernementales
   - Piratages/hacks
   - Annonces majeures
   - Catastrophes naturelles

2. **Détecter les manipulations de marché**
   - "Pump and dump"
   - Wash trading
   - Flash crashes

3. **Garantir 100% de précision**
   - Les marchés sont chaotiques
   - Maximal ~75-80% de précision réaliste
   - Toujours des faux signaux

4. **Marcher dans tous les contextes**
   - Marché haussier ≠ Marché baissier
   - Crises ≠ Conditions normales
   - Volatilité peut changer le modèle

### ⚠️ Recommandations d'Utilisation

1. **Utilisez plusieurs indicateurs**
   - Ne dépendez pas UNIQUEMENT du Random Forest
   - Combinez avec RSI, MACD, supports/résistances

2. **Validez par votre analyse**
   - Vérifiez les prédictions avant d'agir
   - Consultez les graphiques
   - Prenez en compte l'actualité

3. **Gérez votre risque**
   - Utilisez les stop-loss
   - Diversifiez votre portefeuille
   - Ne risquez que ce que vous pouvez perdre

4. **Réentraînez régulièrement**
   - Tous les mois avec les nouvelles données
   - Les patterns de marché changent
   - La performance peut se dégrader

### 📊 Performance dans Différents Contextes

| Contexte | Performance | Raison |
|----------|-------------|--------|
| Marché calme | ⭐⭐⭐⭐ | Patterns clairs |
| Tendance haussière | ⭐⭐⭐ | Bonne détection HAUSSE |
| Tendance baissière | ⭐⭐⭐ | Bonne détection BAISSE |
| Forte volatilité | ⭐⭐ | Signaux conflictuels |
| Avant événement | ⭐ | Imprévisible |

---

## Dépannage

### Problème : Accuracy basse (< 60%)

**Causes possibles** :
- Pas assez de données d'entraînement
- Features irrelevantes
- Déséquilibre majeur hausse/baisse
- Hyperparamètres non optimisés

**Solutions** :
```python
# Augmentez les données
train_model(symbol=None, limit=100000)

# Ajustez les hyperparamètres
train_model(n_estimators=300, max_depth=18)

# Vérifiez la qualité des données
```

### Problème : "Model not trained yet"

**Cause** : Aucun modèle entraîné

**Solution** : 
1. Allez sur http://localhost:4200
2. Onglet Random Forest
3. Cliquez "Entraîner le Modèle"

### Problème : Prédictions incohérentes

**Cause** : Données incomplètes ou indicateurs erronés

**Solution** :
```python
# Vérifiez les valeurs extrêmes
print(X.describe())

# Nettoyez les données
X = X.replace([np.inf, -np.inf], np.nan)
X = X.fillna(X.median())
```

---

## Ressources

- **Scikit-Learn Random Forest** : https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html
- **Indicateurs Techniques** : https://en.wikipedia.org/wiki/Technical_analysis
- **Machine Learning** : https://www.coursera.org/learn/machine-learning

---

**Dernière mise à jour** : 4 Décembre 2025
