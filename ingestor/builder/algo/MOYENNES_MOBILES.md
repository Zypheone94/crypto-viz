# Moyennes Mobiles — Guide Condensé (≤200 lignes)

## But
Lisser les prix pour révéler la tendance, réduire le bruit, et fournir des signaux simples (croisements, supports dynamiques) exploitables seuls ou avec d’autres indicateurs.

## Variantes principales
- SMA (Simple): moyenne arithmétique sur N périodes
  - Formule: `SMA(N) = (P1 + ... + PN) / N`
- EMA (Exponentielle): pondère plus les prix récents
  - Formule: `EMA_t = k*P_t + (1-k)*EMA_{t-1}`, `k=2/(N+1)`
- WMA (Pondérée): poids linéaires décroissants (réactivité entre SMA et EMA)

## Implémentation (extraits)
```python
# SMA/EMA via pandas
df['sma_20'] = df['price'].rolling(20).mean()
df['ema_20'] = df['price'].ewm(span=20, adjust=False).mean()

# MAs utilisées par CryptoViz (groupe par symbole conseillé)
df['price_ma_5']  = df.groupby('symbol')['price'].transform(lambda s: s.rolling(5).mean())
df['price_ma_20'] = df.groupby('symbol')['price'].transform(lambda s: s.rolling(20).mean())
df['price_ma_50'] = df.groupby('symbol')['price'].transform(lambda s: s.rolling(50).mean())
df['volume_ma_5'] = df.groupby('symbol')['volume_24h'].transform(lambda s: s.rolling(5).mean())
```

## Features dérivées (exemples)
```python
df['price_to_ma5']  = df['price'] / df['price_ma_5']
df['price_to_ma20'] = df['price'] / df['price_ma_20']
df['ma_cross_flag'] = (df['price_ma_5'] > df['price_ma_20']).astype(int)
```

## Stratégies simples
1) Croisement de moyennes (EMA10 vs EMA50)
```python
df['ema_10'] = df['price'].ewm(span=10, adjust=False).mean()
df['ema_50'] = df['price'].ewm(span=50, adjust=False).mean()
df['signal'] = (df['ema_10'] > df['ema_50']).astype(int)  # 1=achat, 0=vente
df['crossover'] = df['signal'].diff().fillna(0).ne(0)     # détection croisement
```
Interprétation: EMA10 ↑ croise EMA50 → biais haussier; croisement inverse → biais baissier.

2) Supports/résistances dynamiques (SMA20)
```python
df['sma_20'] = df['price'].rolling(20).mean()
df['is_support']    = (df['price'] < df['sma_20']) & (df['price'].shift(1) > df['sma_20'].shift(1))
df['is_resistance'] = (df['price'] > df['sma_20']) & (df['price'].shift(1) < df['sma_20'].shift(1))
```

3) Suivi de tendance (alignement)
```python
ma20 = df['price'].rolling(20).mean()
ma50 = df['price'].rolling(50).mean()
ma200 = df['price'].rolling(200).mean()
bullish = (df['price'] > ma20) & (ma20 > ma50) & (ma50 > ma200)
bearish = (df['price'] < ma20) & (ma20 < ma50) & (ma50 < ma200)
```

## Périodes recommandées (guides)
- Très court terme: 5–10 (EMA ou SMA) → réactif, plus de faux signaux
- Court/moyen terme: 20–50 (SMA) → équilibre lisibilité/retard
- Long terme: 100–200 (SMA) → tendance structurelle, retard important

## Avantages / Inconvénients
Avantages:
- Simples, rapides, universels; réduisent le bruit; utiles en tendance.
Inconvénients:
- En retard; faux signaux en range; nécessitent calibrage; non prédictif d’événements.

## Intégration CryptoViz & Random Forest
- Les MAs constituent une part majeure des features (≈ 60% cumulées)
- Rôle: encodent la tendance multi-échelles (+ ratios prix/MA)
- Exemples de features: `price_ma_*`, `volume_ma_*`, `price_to_ma*`, croisement MA

Conseils:
- Grouper par symbole avant rolling; gérer `min_periods` si nécessaire
- Remplacer NaN/Inf; éviter fuites de données (rollings causaux)

## Bonnes pratiques
- Combiner MAs avec RSI/MACD/volume pour filtrer faux signaux
- Tester plusieurs fenêtres mais rester parcimonieux (2–4 MAs)
- Adapter les périodes au timeframe (ex. 5/20/50 sur H1 ou D1)

## FAQ rapide
Q: EMA ou SMA ?
- EMA: plus réactive (court terme)
- SMA: plus stable (moyen/long terme)

Q: Combien de MAs ?
- 2 à 4: court + moyen + long; au-delà, complexité ↑ sans gain clair

Q: Pourquoi ça ne marche plus ?
- Marché latéral; périodes mal calibrées; pas assez de données; manque de filtres.

## Check-list d’usage
- [ ] Choisir périodes adaptées au marché/timeframe
- [ ] Valider visuellement les croisements (chart)
- [ ] Combiner avec d’autres signaux (RSI, MACD, volume)
- [ ] Backtester minimalement sur votre dataset

---
Dernière mise à jour: 4 Déc 2025
