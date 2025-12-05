# Random Forest — Guide Condensé (≤200 lignes)

## But
Prédire à court terme si le prix d'une crypto va MONTER (1) ou BAISSER (0), avec une probabilité associée.

## Pile & Modèle
- Modèle: `RandomForestClassifier`
- Normalisation: `StandardScaler` (appliqué train et predict)
- Équilibrage: `class_weight='balanced'`
- Persistance: pickle (modèle + scaler + métriques)

## Features (≈27)
- Base: `price`, `volume_24h`, `market_cap`, `coin_circulating`
- MAs: `price_ma_5/10/20/50`, `volume_ma_5/20`
- Momentum: `price_change_1/5/10`, `volume_change`
- Indicateurs: `rsi`, `macd`, `macd_signal`, `macd_diff`, `bb_position`, `volatility`
- Ratios: `price_to_ma5/ma20`, `volume_ratio`, `bb_upper/lower`

## Entraîner le modèle
- Web: `http://localhost:4200` → Analytics → Random Forest → Entraîner
- API: `POST /algo/random-forest/train`
  - Params fréquents: `n_estimators=200`, `max_depth=15`, `test_size=0.2`
- Données: limite ≈ 50k lignes, split 80/20 (stratifié)

Exemple (curl):
```bash
curl -X POST "http://localhost:8080/algo/random-forest/train?n_estimators=200&max_depth=15&test_size=0.2"
```

## Prédire
- Web: sélectionner `symbol` + `recent_count`, cliquer Prédire
- API: `GET /algo/random-forest/predict?symbol=BTC&recent_count=10`

Réponse (extrait):
```json
{
  "symbol": "BTC",
  "predictions": [{
    "timestamp": "2025-12-04 09:00:00",
    "price": 42500.5,
    "prediction": "HAUSSE",
    "probability": 0.75,
    "features": {"rsi": 65.2, "price_ma_5": 42300.0}
  }]
}
```

## Métriques clés (test)
- Accuracy: part de bonnes prédictions (cible ≥ 0.70)
- Precision(HAUSSE): fiabilité des signaux HAUSSE
- Recall(HAUSSE): HAUSSE détectées parmi les vraies HAUSSE
- F1: équilibre Precision/Recall

Ordres de grandeur réalistes: Accuracy ~0.70–0.78, Precision ~0.65–0.72, F1 ~0.62–0.68 (selon période/actif).

## Endpoints API
- `POST /algo/random-forest/train` → Entraîne et sauvegarde (params: `symbol?`, `n_estimators?`, `max_depth?`, `test_size?`)
- `GET  /algo/random-forest/predict` → Prédit (params: `symbol`, `recent_count`)
- `GET  /algo/random-forest/info` → Retourne métriques/test + importance features
- `GET  /api/symbols` → Liste des `symbol` disponibles (dropdown UI)

## Bonnes pratiques d’entraînement
- Suffisamment de données par symbole; sinon entraîner globalement (`symbol` vide)
- Nettoyer NaN/Inf; caper outliers grossiers au besoin
- Semence fixe (`random_state`) pour reproductibilité de debug

## Interpréter la sortie
- `prediction`: "HAUSSE" ou "BAISSE"
- `probability` (0–1): confiance; ≥0.7 considéré comme fort
- L’UI affiche un verdict global (majorité) + confiance moyenne

## Tuning rapide
- Sous-apprentissage: augmenter complexité (ex: `max_depth=18`, `n_estimators=300`)
- Sur-apprentissage: réduire profondeur/contraindre (`max_depth=12`, `min_samples_split`↑)
- Données bruitées: réduire features instables ou lisser davantage (MAs plus longues)

Grille de départ:
```text
n_estimators: 150|200|300
max_depth:   12|15|18
min_samples_split: 2|5|8
```

## Feature engineering (points d’appui)
- Ratios prix/volume et écarts relatifs à MAs
- Volatilité multi-fenêtres (ex: std 10/20)
- Momentum directionnel (delta signe, accélération)
- Signal de croisement (MA courte > MA longue)

## Limites à garder en tête
- Ne prévoit pas les chocs exogènes (news, régulations, hacks)
- Performances dépendantes du régime de marché (haussier/baissier/range)
- Probabilités ≠ certitudes; gestion du risque indispensable

## Dépannage express
- Accuracy faible (<0.6): plus de données, tuning `max_depth`, nettoyer features
- "Model not trained": lancer `POST /algo/random-forest/train` puis réessayer
- JSON/Timestamp: s’assurer que timestamps sont sérialisés en chaînes
- Prédictions incohérentes: vérifier scaler chargé et appliqué côté predict

## Sécurité d’usage (UX)
- Toujours afficher la confiance et le sens (↑/↓) clairement
- Trier les prédictions par probabilité décroissante (fait dans l’UI)
- Afficher importance des features pour transparence du modèle

## Notes d’intégration (backend)
- Sauvegarder: `/app/ingestor/builder/algo/models/random_forest.pkl`
- Charger au démarrage; si absent → 404 sur predict/info jusqu’à train
- MySQL: requêtes paginées; limiter à 50k–100k lignes pour des temps raisonnables

## Check-list avant mise en prod
- [ ] Métriques test ≥ objectifs définis
- [ ] Sérialisation JSON OK (pas de NaN/Timestamp bruts)
- [ ] Scaler et modèle synchronisés (même date d’entraînement)
- [ ] Endpoints couverts par tests minimaux (train/predict/info)

---
Dernière mise à jour: 4 Déc 2025
