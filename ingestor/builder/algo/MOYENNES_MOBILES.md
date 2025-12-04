# Moyennes Mobiles - Guide Complet

## 📋 Table des Matières
1. [Vue d'ensemble](#vue-densemble)
2. [Types de Moyennes Mobiles](#types-de-moyennes-mobiles)
3. [Calcul Mathématique](#calcul-mathématique)
4. [Implémentation dans CryptoViz](#implémentation-dans-cryptoviz)
5. [Stratégies Trading](#stratégies-trading)
6. [Avantages et Inconvénients](#avantages-et-inconvénients)
7. [Cas d'Usage](#cas-dusage)

---

## Vue d'Ensemble

### Qu'est-ce qu'une Moyenne Mobile ?

Une **moyenne mobile** est une technique d'analyse technique qui lisse les données de prix en calculant la moyenne sur une période donnée. Elle aide à :

- **Identifier les tendances** long terme
- **Réduire le bruit** des fluctuations court terme
- **Détecter les supports et résistances**
- **Générer des signaux d'achat/vente**

### Analogie Simple

Imagine le prix d'une crypto comme une rivière turbulente. Une moyenne mobile est comme un **filtre qui lisse l'eau** pour voir la direction générale du courant.

```
Prix brut:    ↑↓↑↑↓↓↑↓↑↓↑↑↑↓↑  (chaotique)
Moyenne 20J:  ↗↗↗↗↗↗→→→→→→→→↘  (tendance claire)
```

### Utilité en Trading Crypto

- **Déterminer la direction** : Hausse ou baisse ?
- **Croiser les moyennes** : Signaux d'achat/vente
- **Identifier le support/résistance** : Niveaux clés
- **Confirmer les patterns** : Triangles, drapeaux, etc.

---

## Types de Moyennes Mobiles

### 1. SMA - Simple Moving Average (Moyenne Mobile Simple)

#### Définition
La moyenne simple de N périodes, où chaque prix a le même poids.

#### Formule
```
SMA(N) = (P1 + P2 + P3 + ... + PN) / N

Où:
- P = Prix de clôture
- N = Nombre de périodes
```

#### Exemple avec N=5
```
Jour 1: Prix = 100
Jour 2: Prix = 102
Jour 3: Prix = 101
Jour 4: Prix = 103
Jour 5: Prix = 105

SMA(5) = (100 + 102 + 101 + 103 + 105) / 5 = 511 / 5 = 102.2
```

#### Implémentation Python
```python
def simple_moving_average(prices, period=20):
    """Calcule la SMA pour une série de prix"""
    return prices.rolling(window=period).mean()

# Utilisation
sma_20 = simple_moving_average(df['price'], period=20)
```

#### Caractéristiques
- ✅ **Simple** à comprendre et calculer
- ✅ **Transparent** : tous les prix ont le même poids
- ❌ **Réactif lentement** aux changements récents
- ❌ **Croise tard** les supports/résistances

---

### 2. EMA - Exponential Moving Average (Moyenne Mobile Exponentielle)

#### Définition
Une moyenne mobile qui **pondère davantage les prix récents**. Les données anciennes ont moins d'impact.

#### Formule
```
EMA = Prix_actuel * (k) + EMA_précédente * (1 - k)

Où:
- k = 2 / (N + 1)
- N = Nombre de périodes
```

#### Exemple avec N=5
```
k = 2 / (5 + 1) = 0.333

Si:
- Prix actuel = 105
- EMA précédente = 102

EMA = 105 * 0.333 + 102 * 0.667 = 34.965 + 68.134 = 103.1
```

#### Implémentation Python
```python
def exponential_moving_average(prices, period=20):
    """Calcule l'EMA pour une série de prix"""
    return prices.ewm(span=period, adjust=False).mean()

# Utilisation
ema_20 = exponential_moving_average(df['price'], period=20)
```

#### Caractéristiques
- ✅ **Réactive** aux changements récents
- ✅ **Croise plus tôt** que SMA
- ✅ **Moins de faux signaux** dans tendance
- ❌ **Plus complexe** à calculer
- ❌ **Peut surréagir** aux pics temporaires

---

### 3. WMA - Weighted Moving Average (Moyenne Mobile Pondérée)

#### Définition
Chaque prix est multiplié par un poids décroissant du plus récent au plus ancien.

#### Formule
```
WMA = (P1*N + P2*(N-1) + P3*(N-2) + ... + PN*1) / (N + (N-1) + ... + 1)
    = (P1*N + P2*(N-1) + ... + PN*1) / (N*(N+1)/2)
```

#### Exemple avec N=3
```
Poids : 3, 2, 1 (total = 6)

Jour 1: Prix = 100, Poids = 3 → 300
Jour 2: Prix = 102, Poids = 2 → 204
Jour 3: Prix = 105, Poids = 1 → 105

WMA = (300 + 204 + 105) / 6 = 609 / 6 = 101.5
```

#### Utilité
Entre SMA et EMA en termes de réactivité.

---

## Calcul Mathématique

### Comparaison Visuelle

```
Prix (points): •
SMA (traits): ―
EMA (courbe): ~

Jour 1-10: Montée
•  •   •    •     •      •       •        •         •          •
 ―    ―     ―      ―       ―        ―         ―          
  ~    ~      ~       ~        ~         ~          (EMA plus haut)

Jour 11-15: Chute
•      •        •         •          •
 ―         ―         ―          ―
  ~          ~           ~           (EMA baisse avant SMA)
```

### Fenêtres Temporelles Courantes

| Période | Type | Timeframe | Utilité |
|---------|------|-----------|---------|
| 5 | SMA/EMA | 4h-1j | Très court terme |
| 10 | SMA/EMA | 1j-1w | Court terme |
| 20 | SMA/EMA | 1w-1mois | Moyen terme |
| 50 | SMA | 1-3 mois | Long terme |
| 200 | SMA | 3-6 mois | Très long terme |

---

## Implémentation dans CryptoViz

### Calcul Automatique

Les moyennes mobiles sont **calculées automatiquement** pour chaque article récupéré :

```python
# Dans load_data_from_db()
df['price_ma_5'] = df.groupby('symbol')['price'].transform(
    lambda x: x.rolling(5, min_periods=1).mean()
)
df['price_ma_10'] = df.groupby('symbol')['price'].transform(
    lambda x: x.rolling(10, min_periods=1).mean()
)
df['price_ma_20'] = df.groupby('symbol')['price'].transform(
    lambda x: x.rolling(20, min_periods=1).mean()
)
df['price_ma_50'] = df.groupby('symbol')['price'].transform(
    lambda x: x.rolling(50, min_periods=1).mean()
)

# Pour le volume aussi
df['volume_ma_5'] = df.groupby('symbol')['volume_24h'].transform(
    lambda x: x.rolling(5, min_periods=1).mean()
)
df['volume_ma_20'] = df.groupby('symbol')['volume_24h'].transform(
    lambda x: x.rolling(20, min_periods=1).mean()
)
```

### Features Dérivées

À partir des moyennes mobiles, on crée des features pour le Random Forest :

```python
# Ratios (prix par rapport aux moyennes)
df['price_to_ma5'] = df['price'] / df['price_ma_5']
df['price_to_ma20'] = df['price'] / df['price_ma_20']

# Écart à la moyenne
df['price_above_ma5'] = (df['price'] - df['price_ma_5']) / df['price_ma_5']
df['price_above_ma20'] = (df['price'] - df['price_ma_20']) / df['price_ma_20']

# Croisement de moyennes (signal)
df['ma_cross_signal'] = (df['price_ma_5'] > df['price_ma_20']).astype(int)
```

### Exemple Réel

Pour BTC avec données horaires :

```
Timestamp           Price   MA5      MA20     MA50     Price/MA20
2025-12-01 10:00   42500   42300    42100    41900    1.0095
2025-12-01 11:00   42600   42400    42150    41950    1.0107
2025-12-01 12:00   42450   42350    42200    42000    1.0059
2025-12-01 13:00   42700   42450    42300    42050    1.0095
2025-12-01 14:00   42550   42430    42350    42100    1.0047
```

---

## Stratégies Trading

### Stratégie 1 : Croisement de Moyennes (MA Crossover)

#### Principe
- **Signal d'achat** : EMA court terme croise au-dessus de EMA long terme
- **Signal de vente** : EMA court terme croise en dessous de EMA long terme

#### Implémentation
```python
def ma_crossover_signal(df):
    df['ema_short'] = df['price'].ewm(span=10, adjust=False).mean()
    df['ema_long'] = df['price'].ewm(span=50, adjust=False).mean()
    
    # Signal: 1 = Achat (EMA court > EMA long), 0 = Vente
    df['signal'] = (df['ema_short'] > df['ema_long']).astype(int)
    
    # Détecte les croisements
    df['crossover'] = df['signal'].diff() != 0
    
    return df

# Affichage
for idx, row in df[df['crossover']].iterrows():
    if row['signal'] == 1:
        print(f"🟢 ACHAT: EMA10 croise au-dessus de EMA50 à {row['price']}")
    else:
        print(f"🔴 VENTE: EMA10 croise en dessous de EMA50 à {row['price']}")
```

#### Exemple Graphique
```
Prix    ╱╲        ╱╲        ╱╲
        │ ╲      ╱  ╲      ╱  
────────┼──╲────╱────╲────╱─── EMA Court (10)
        │   ╲  ╱      ╲  ╱
        │    ╲╱        ╲╱      
════════════════════════════════ EMA Long (50)

🟢 Croisement vers le HAUT = ACHAT
🔴 Croisement vers le BAS = VENTE
```

**Avantages** :
- ✅ Simple et logique
- ✅ Fonctionne bien en tendance
- ✅ Réduit l'effet du bruit

**Inconvénients** :
- ❌ Signaux tardifs en tendance établie
- ❌ Faux signaux en marché latéral

---

### Stratégie 2 : Support/Résistance Dynamique

#### Principe
Les moyennes mobiles agissent comme **supports** (en hausse) et **résistances** (en baisse).

#### Implémentation
```python
def dynamic_support_resistance(df):
    df['sma_20'] = df['price'].rolling(20).mean()
    
    # Support: prix rebondit sur MA20 (hausse)
    df['is_support'] = (
        (df['price'] < df['sma_20']) &  # Prix en dessous
        (df['price'].shift(1) > df['sma_20'].shift(1))  # Rebond depuis le bas
    )
    
    # Résistance: prix casse la MA20 (baisse)
    df['is_resistance'] = (
        (df['price'] > df['sma_20']) &  # Prix au-dessus
        (df['price'].shift(1) < df['sma_20'].shift(1))  # Casse depuis le bas
    )
    
    return df
```

#### Exemple
```
Prix    ╱╲        MA20 agit
        │ ╲ ╲      comme
───────┼──╲─╲─── résistance
        │   ╲ ╱
        │    ╲╱ ↖ Rebond = support
════════════════════════════════

ACHAT:  Prix rebondit sur MA20 (support)
VENTE:  Prix casse la MA20 (résistance)
```

---

### Stratégie 3 : Trend Following (Suivi de Tendance)

#### Principe
- **Montée** : Si prix > MA20 > MA50 > MA200 → TENDANCE HAUSSIÈRE
- **Baisse** : Si prix < MA20 < MA50 < MA200 → TENDANCE BAISSIÈRE

#### Implémentation
```python
def trend_following(df):
    df['ma_20'] = df['price'].rolling(20).mean()
    df['ma_50'] = df['price'].rolling(50).mean()
    df['ma_200'] = df['price'].rolling(200).mean()
    
    # Alignement haussier
    df['bullish_alignment'] = (
        (df['price'] > df['ma_20']) &
        (df['ma_20'] > df['ma_50']) &
        (df['ma_50'] > df['ma_200'])
    )
    
    # Alignement baissier
    df['bearish_alignment'] = (
        (df['price'] < df['ma_20']) &
        (df['ma_20'] < df['ma_50']) &
        (df['ma_50'] < df['ma_200'])
    )
    
    return df

# Signal
df['trend'] = df.apply(lambda row:
    'ACHAT (Haussier)' if row['bullish_alignment'] else
    'VENTE (Baissier)' if row['bearish_alignment'] else
    'NEUTRE',
    axis=1
)
```

---

## Avantages et Inconvénients

### ✅ Avantages des Moyennes Mobiles

1. **Simplifies d'utiliser**
   - Faciles à comprendre
   - Calculs rapides
   - Visualisation claire

2. **Confirmées par la pratique**
   - Utilisées depuis 50 ans
   - Efficaces sur tous les marchés
   - Signaux fiables en tendance

3. **Flexibles**
   - Adaptables à toute période
   - Combinables avec autres indicateurs
   - Personnalisables

4. **Peu de faux signaux**
   - En tendance établie
   - Moins de bruit qu'analyse brute

### ❌ Inconvénients des Moyennes Mobiles

1. **Laguer (Retard)**
   - Suivent les prix, ne les prédisent pas
   - Signaux tardifs
   - Mauvaises en reversals rapides

2. **Faux signaux**
   - Nombreux en marché latéral
   - Whipsaws (va-et-vient)
   - Inefficaces dans la consolidation

3. **Besoin de calibrage**
   - Quelle période utiliser ?
   - N'existe pas de "meilleure" période
   - Dépend du style de trading

4. **Pas prédictif**
   - N'indiquent que la tendance passée
   - Ne détectent pas les reversals
   - Aveugle aux événements externes

---

## Cas d'Usage

### Cas 1 : BTC en Tendance Haussière

```
Jour 1-5: Prix montant (40K → 45K)
- MA5 = 43K (croissante)
- MA20 = 42K (croissante)
- MA50 = 41K (croissante)

→ SIGNAL: ACHAT (tout aligné à la hausse)
→ Probabilité succès: 70%
```

### Cas 2 : ETH en Consolidation

```
Jour 1-10: Prix chaotique (2500 → 2600 → 2500 → 2550)
- MA5 = 2550 (fluctuante)
- MA20 = 2520 (stable)
- MA50 = 2530 (stable)

→ SIGNAL: NEUTRE (pas de tendance claire)
→ Risque faux signal: 60%
→ ACTION: Attendre clarification
```

### Cas 3 : ADA en Tendance Baissière

```
Jour 1-10: Prix baissant (1.5 → 1.0)
- Prix = 1.0 (en baisse)
- MA5 = 1.1 (baissière)
- MA20 = 1.2 (baissière)
- MA50 = 1.3 (baissière)

→ SIGNAL: VENTE (alignement baissier)
→ Probabilité succès: 65%
```

---

## Combinaison avec Random Forest

### Comment Utilisées dans CryptoViz

Les moyennes mobiles sont **17 des 27 features** du Random Forest :

```
Features de Moyenne Mobile:
- price_ma_5, price_ma_10, price_ma_20, price_ma_50 (4 features)
- volume_ma_5, volume_ma_20 (2 features)
- price_change_1, price_change_5, price_change_10 (3 features)
- price_to_ma5, price_to_ma20 (2 features)
- ema_12, ema_26 (MACD - 2 features)
- bb_middle, bb_upper, bb_lower (Bollinger - 3 features)

Total: 17 features sur 27 (63%)
```

### Importance Relative

```
Indicateur      Importance  Contribution
─────────────────────────────────────────
RSI             12%         Critique ⭐⭐⭐
Price MA 5      8%          Importante ⭐⭐
Price Change    10%         Importante ⭐⭐
MACD            9%          Importante ⭐⭐
Volume Ratio    7%          Modérée ⭐
Autres MA       38%         Cumulé
─────────────────────────────────────────
MA Total        63%         Dominante
```

### Pourquoi les MA Sont Importantes

1. **Captent les tendances** → Critiques pour prédictions
2. **Stables** → Moins de bruit que prix brut
3. **Complémentaires** → Différentes échelles de temps
4. **Universelles** → Fonctionnent pour tous les cryptos

---

## Optimisation des Paramètres

### Choix de la Période

#### Court Terme (1-10 jours)
- **Usage** : Scalping, day trading
- **Avantage** : Réactif
- **Inconvénient** : Faux signaux
- **Exemple** : MA5, MA10

#### Moyen Terme (20-50 jours)
- **Usage** : Swing trading
- **Avantage** : Bon équilibre
- **Inconvénient** : Signaux tardifs
- **Exemple** : MA20, MA50

#### Long Terme (100-200 jours)
- **Usage** : Investissement
- **Avantage** : Tendance claire
- **Inconvénient** : Très en retard
- **Exemple** : MA100, MA200

### Configuration Recommandée pour CryptoViz

```python
# Pour prédictions court terme
PERIODS = [5, 10, 20]    # Réactif
TYPE = 'SMA'             # Simple

# Pour prédictions moyen terme
PERIODS = [20, 50, 200]  # Équilibré
TYPE = 'SMA'             # Standard

# Pour maximum réactivité
PERIODS = [10, 30]       # Très réactif
TYPE = 'EMA'             # Exponentielle
```

---

## Ressources et Références

### Lectures
- **Technical Analysis from A to Z** - Jack D. Schwager
- **Analysis of Moving Averages** - CoinMarketCap
- **Indicators Explained** - TradingView

### Sites
- **TradingView** : https://www.tradingview.com/
- **CoinMarketCap Charts** : https://coinmarketcap.com/
- **Investopedia** : https://www.investopedia.com/terms/m/movingaverage.asp

### Formules Mathématiques
- **SMA** : Moyenne arithmétique simple
- **EMA** : Moyenne pondérée exponentiellement
- **WMA** : Moyenne pondérée linéairement

---

## Foire aux Questions (FAQ)

### Q: Quelle moyenne mobile utiliser ?
**R:** Dépend de votre style :
- Scalping: MA5, MA10 (SMA)
- Day Trading: MA20, MA50 (SMA ou EMA)
- Swing: MA20, MA50, MA200 (SMA)
- Investissement: MA50, MA200 (SMA)

### Q: EMA ou SMA ?
**R:** 
- **EMA** : Plus réactive, mieux pour short term
- **SMA** : Plus stable, mieux pour tendances long term

### Q: Pourquoi ma stratégie MA ne fonctionne pas ?
**R:**
- Marché latéral = faux signaux
- Période mal calibrée
- Pas assez de données
- Besoin de filtre supplémentaire (RSI, volume)

### Q: Combien de moyennes mobiles utiliser ?
**R:**
- Minimum: 2 (court + long terme)
- Recommandé: 3-4 (court + moyen + long)
- Maximum: 5-6 (commence à être complexe)

---

**Dernière mise à jour** : 4 Décembre 2025
