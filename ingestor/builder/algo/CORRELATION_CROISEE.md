# Corrélation Croisée - Documentation Technique

## 1. Definition

La corrélation croisée est une méthode statistique qui permet de mesurer la relation temporelle entre deux séries de données. Dans notre projet CryptoViz, nous l'utilisons pour analyser si le volume de trading peut prédire les mouvements de prix d'une cryptomonnaie, ou inversement.

Contrairement à une corrélation simple qui mesure la relation au même instant, la corrélation croisée introduit un décalage temporel (appelé "lag") pour voir si une variable influence l'autre avec un retard.

## 2. Pourquoi ce choix pour CryptoViz

Nous avons choisi la corrélation croisée pour plusieurs raisons :

1. Complémentarité avec les autres indicateurs : Le RSI mesure le momentum, l'écart-type mesure la volatilité. La corrélation croisée ajoute une dimension temporelle en analysant les relations entre séries.

2. Question métier pertinente : "Le volume précède-t-il les mouvements de prix ?" est une question classique en analyse financière. Si oui, le volume peut servir de signal prédictif.

3. Complexité moyenne : Plus avancé qu'une simple moyenne mobile, mais plus simple qu'un modèle de machine learning. Facile à expliquer et à visualiser.


## 3. Les Mathematiques Utilisees

### 3.1 Etape 1 : Normalisation Z-score

Avant de calculer la corrélation, nous normalisons les données avec la formule du Z-score :

    Z = (valeur - moyenne) / ecart-type

Pourquoi normaliser ? Le prix du Bitcoin est autour de 90 000 dollars tandis que le volume peut être de 500 millions de dollars. Ces échelles très différentes rendraient la comparaison impossible. La normalisation ramène toutes les valeurs autour de 0 avec un écart-type de 1.

Exemple concret :
- Prix BTC : [90000, 91000, 89000, 92000]
- Moyenne : 90500
- Ecart-type : 1118
- Z-scores resultants : [-0.45, +0.45, -1.34, +1.34]


### 3.2 Etape 2 : Calcul de la correlation croisee

Nous utilisons la fonction numpy.correlate() avec le mode 'full' qui calcule la corrélation pour tous les décalages possibles.

La formule de corrélation de Pearson utilisée est :

    r = somme((xi - moyenne_x) * (yi - moyenne_y)) / (n * ecart_type_x * ecart_type_y)

Le résultat est une valeur entre -1 et +1 :
- +1 : Corrélation parfaite positive (quand l'un augmente, l'autre aussi)
- 0 : Aucune relation linéaire
- -1 : Corrélation parfaite négative (quand l'un augmente, l'autre diminue)


### 3.3 Etape 3 : Analyse des lags (decalages)

Le lag représente le décalage temporel entre les deux séries. Pour chaque valeur de lag, on calcule une corrélation différente.

| Lag    | Ce qu'on compare              | Question posée                                      |
|--------|-------------------------------|-----------------------------------------------------|
| lag -2 | prix[t] vs volume[t-2]        | Le prix actuel est-il lié au volume d'il y a 2 périodes ? |
| lag -1 | prix[t] vs volume[t-1]        | Le prix réagit-il au volume précédent ?             |
| lag 0  | prix[t] vs volume[t]          | Prix et volume bougent-ils ensemble ?               |
| lag +1 | prix[t] vs volume[t+1]        | Le volume réagit-il au prix ?                       |
| lag +2 | prix[t] vs volume[t+2]        | Le prix prédit-il le volume futur ?                 |

Dans notre implémentation, 1 lag correspond à environ 8 minutes (basé sur la fréquence de collecte des données : environ 920 points sur 5 jours).


## 4. Interpretation des Resultats

### 4.1 Force de la correlation

| Valeur absolue | Interpretation |
|----------------|----------------|
| >= 0.7         | Correlation forte - relation très significative |
| 0.5 - 0.7      | Correlation moderee - relation notable |
| 0.3 - 0.5      | Correlation faible - relation existante mais limitée |
| < 0.3          | Correlation negligeable - pas de relation significative |


### 4.2 Signe de la correlation

| Signe    | Signification |
|----------|---------------|
| Positif  | Quand le volume augmente, le prix tend à augmenter |
| Negatif  | Quand le volume augmente, le prix tend à diminuer |


### 4.3 Interpretation du lag optimal

| Lag optimal | Interpretation |
|-------------|----------------|
| > 0         | Le volume PRECEDE le prix. Le volume peut être utilisé comme signal prédictif. |
| = 0         | Volume et prix sont SYNCHRONISES. Ils réagissent en même temps. |
| < 0         | Le prix PRECEDE le volume. Les traders réagissent après les mouvements de prix. |


## 5. Implementation Technique

### 5.1 Architecture des fichiers

Backend (Python) :
- Fichier principal : ingestor/scraper/component/scraperdb/corre_croisee.py
- Ce fichier contient toute la logique de calcul

API (FastAPI) :
- Routes : ingestor/scraper/api/routes/data.py
- Endpoints exposés pour le frontend

Frontend (Angular) :
- Composant : web/src/app/component/analytics/components/cross-correlation.ts
- Template : web/src/app/component/analytics/components/cross-correlation.html
- Styles : web/src/app/component/analytics/components/cross-correlation.css


### 5.2 Fonctions principales du module corre_croisee.py

| Fonction                  | Description |
|---------------------------|-------------|
| get_db_connection()       | Établit la connexion à la base MySQL |
| analyze_symbol()          | Analyse complète pour un symbole donné (BTC, ETH, etc.) |
| get_correlation_strength()| Catégorise la force (strong, moderate, weak, negligible) |
| interpret_correlation()   | Génère l'interprétation en français |
| get_available_symbols()   | Liste les symboles avec assez de données pour l'analyse |


### 5.3 Endpoints API

Analyser un symbole specifique :
    GET /data/cross-correlation?symbol=BTC&max_lag=12

Parametres :
- symbol : Le symbole de la cryptomonnaie (BTC, ETH, SOL, etc.)
- max_lag : Le nombre maximum de périodes de décalage à analyser (défaut : 12)

Lister les symboles disponibles :
    GET /data/cross-correlation/symbols

Retourne la liste des symboles ayant suffisamment de données pour une analyse fiable.


### 5.4 Exemple de reponse API

{
  "symbol": "BTC",
  "data_points": 920,
  "optimal_lag": 0,
  "max_correlation": -0.2173,
  "strength": "weak",
  "interpretation": "Correlation faible (negative). Volume et prix sont synchronises.",
  "correlations": {
    "-12": 0.0234,
    "-11": 0.0312,
    ...
    "0": -0.2173,
    ...
    "11": 0.0198,
    "12": 0.0156
  },
  "date_range": {
    "start": "2025-11-23T10:00:00",
    "end": "2025-11-28T15:30:00"
  }
}


## 6. Limites de la Methode

1. Relations lineaires uniquement : La corrélation de Pearson ne détecte que les relations linéaires. Une relation exponentielle ou quadratique ne sera pas correctement captée.

2. Sensibilité aux outliers : Les valeurs extrêmes peuvent fausser les résultats. C'est pourquoi nous utilisons la normalisation Z-score.

3. Corrélation n'est pas causalité : Une forte corrélation ne prouve pas que le volume CAUSE le mouvement de prix. Il peut y avoir une troisième variable qui influence les deux.

4. Dépendance aux données : L'analyse nécessite suffisamment de points de données (minimum 10) pour être statistiquement significative.


## 7. Questions Frequentes pour l'Oral

Q : Pourquoi normaliser les données ?
R : Pour comparer des séries avec des échelles très différentes. Le prix en dollars et le volume en millions ne peuvent pas être comparés directement.

Q : Que signifie un lag positif ?
R : Un lag positif signifie que le volume précède le prix. Par exemple, lag +2 signifie que le volume d'il y a 2 périodes influence le prix actuel.

Q : Pourquoi utiliser numpy.correlate ?
R : Cette fonction est optimisée en C et calcule toutes les corrélations décalées en une seule opération, ce qui est très performant.

Q : Quelle est la différence avec une corrélation simple ?
R : La corrélation simple mesure la relation au même instant (lag 0). La corrélation croisée analyse la relation à différents décalages temporels.

Q : Comment interpréter une corrélation négative ?
R : Une corrélation négative signifie que quand une variable augmente, l'autre tend à diminuer. Par exemple, si volume augmente et prix diminue.

Q : Pourquoi avons-nous choisi cet indicateur ?
R : Pour compléter les autres indicateurs (RSI, écart-type) avec une analyse de la relation temporelle entre volume et prix, ce qui peut révéler des signaux prédictifs.
