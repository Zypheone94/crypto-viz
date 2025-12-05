"""
Module de corrélation croisée normalisée pour l'analyse crypto.
Utilise numpy.correlate pour calculer la corrélation entre volume et prix.
Utilise MySQL comme base de données.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'api', 'utils'))
from mysql_client import get_mysql_connection, execute_query_pandas


def get_db_connection():
    return get_mysql_connection()


def get_correlation_strength(correlation: float) -> str:
    """Retourne la catégorie de force de corrélation."""
    abs_corr = abs(correlation)
    if abs_corr >= 0.5:
        return "strong"
    elif abs_corr >= 0.3:
        return "moderate"
    elif abs_corr >= 0.1:
        return "weak"
    else:
        return "negligible"


def interpret_correlation(correlation: float, lag: int) -> str:
    """Génère une interprétation humaine de la corrélation."""
    abs_corr = abs(correlation)
    
    if abs_corr < 0.1:
        strength = "négligeable"
    elif abs_corr < 0.3:
        strength = "faible"
    elif abs_corr < 0.5:
        strength = "modérée"
    elif abs_corr < 0.7:
        strength = "forte"
    else:
        strength = "très forte"
    
    direction = "positive" if correlation > 0 else "négative"
    
    if lag > 0:
        timing = f"Le volume précède le prix de {lag} période(s)"
    elif lag < 0:
        timing = f"Le prix précède le volume de {abs(lag)} période(s)"
    else:
        timing = "Volume et prix sont synchronisés"
    
    return f"Corrélation {strength} ({direction}). {timing}."


def analyze_symbol(symbol: str, max_lag: int = 12) -> Dict[str, Any]:
    """
    Analyse la corrélation croisée pour un symbole spécifique.
    Utilise numpy.correlate avec normalisation Z-score.
    """
    try:
        query = """
            SELECT fetched_at, price, volume_24h
            FROM article
            WHERE symbol = %s
            AND price IS NOT NULL
            AND volume_24h IS NOT NULL
            ORDER BY fetched_at ASC
        """
        
        df = execute_query_pandas(query, [symbol.upper()])
        
        if len(df) < 10:
            return {
                "error": f"Données insuffisantes pour {symbol} ({len(df)} points)",
                "symbol": symbol,
                "data_points": len(df)
            }
        
        # Convertir les dates
        df['fetched_at'] = pd.to_datetime(df['fetched_at'])
        
        # Normalisation Z-score
        price_mean = df['price'].mean()
        price_std = df['price'].std()
        volume_mean = df['volume_24h'].mean()
        volume_std = df['volume_24h'].std()
        
        if price_std == 0 or volume_std == 0:
            return {
                "error": f"Pas de variation pour {symbol}",
                "symbol": symbol,
                "data_points": len(df)
            }
        
        df['price_z'] = (df['price'] - price_mean) / price_std
        df['volume_z'] = (df['volume_24h'] - volume_mean) / volume_std
        
        # Corrélation croisée avec numpy.correlate
        corr_full = np.correlate(df['price_z'], df['volume_z'], mode='full')
        corr_normalized = corr_full / len(df)
        
        # Tous les lags possibles
        all_lags = np.arange(-len(df) + 1, len(df))
        
        # Filtrer pour garder seulement les lags dans [-max_lag, +max_lag]
        center = len(df) - 1
        start_idx = center - max_lag
        end_idx = center + max_lag + 1
        
        # S'assurer que les indices sont valides
        start_idx = max(0, start_idx)
        end_idx = min(len(corr_normalized), end_idx)
        
        # Extraire les corrélations pour les lags voulus
        correlations = {}
        for i in range(start_idx, end_idx):
            lag = all_lags[i]
            correlations[int(lag)] = round(float(corr_normalized[i]), 4)
        
        # Trouver le lag optimal (corrélation absolue max)
        optimal_lag = max(correlations.keys(), key=lambda k: abs(correlations[k]))
        optimal_corr = correlations[optimal_lag]
        
        # Interprétation
        interpretation = interpret_correlation(optimal_corr, optimal_lag)
        strength = get_correlation_strength(optimal_corr)
        
        return {
            "symbol": symbol.upper(),
            "data_points": len(df),
            "correlations": correlations,
            "optimal_lag": optimal_lag,
            "optimal_correlation": optimal_corr,
            "correlation_strength": strength,
            "interpretation": interpretation,
            "time_range": {
                "start": str(df['fetched_at'].iloc[0]),
                "end": str(df['fetched_at'].iloc[-1])
            }
        }
        
    except FileNotFoundError as e:
        return {"error": str(e), "symbol": symbol}
    except Exception as e:
        return {"error": f"Erreur d'analyse: {str(e)}", "symbol": symbol}


def analyze_multiple_symbols(symbols: Optional[List[str]] = None, max_lag: int = 12, limit: int = 10) -> List[Dict[str, Any]]:
    """Analyse la corrélation croisée pour plusieurs symboles."""
    try:
        if symbols is None:
            query = """
                SELECT symbol, COUNT(*) as count
                FROM article
                WHERE price IS NOT NULL AND volume_24h IS NOT NULL
                GROUP BY symbol
                HAVING count > 10
                ORDER BY count DESC
                LIMIT %s
            """
            
            df_symbols = execute_query_pandas(query, [limit])
            symbols = df_symbols['symbol'].tolist()
        
        results = []
        for symbol in symbols:
            result = analyze_symbol(symbol, max_lag)
            results.append(result)
        
        return results
        
    except FileNotFoundError as e:
        return [{"error": str(e)}]
    except Exception as e:
        return [{"error": f"Erreur: {str(e)}"}]


def get_available_symbols() -> List[Dict[str, Any]]:
    """Récupère la liste des symboles disponibles pour l'analyse."""
    try:
        query = """
            SELECT symbol, COUNT(*) as data_points
            FROM article
            WHERE price IS NOT NULL AND volume_24h IS NOT NULL
            GROUP BY symbol
            HAVING data_points > 10
            ORDER BY data_points DESC
        """
        
        df_symbols = execute_query_pandas(query)
        return [{"symbol": row[0], "data_points": row[1]} for _, row in df_symbols.iterrows()]
        
    except FileNotFoundError as e:
        return [{"error": str(e)}]
    except Exception as e:
        return [{"error": f"Erreur: {str(e)}"}]


# Pour tester en local
if __name__ == "__main__":
    print("=== Test Corrélation Croisée ===")
    
    # Liste des symboles disponibles
    symbols = get_available_symbols()
    print(f"\nSymboles disponibles: {len(symbols)}")
    for s in symbols[:5]:
        print(f"  - {s['symbol']}: {s['data_points']} points")
    
    # Analyser BTC
    print("\n=== Analyse BTC ===")
    result = analyze_symbol("BTC", max_lag=12)
    if "error" not in result:
        print(f"Points de données: {result['data_points']}")
        print(f"Lag optimal: {result['optimal_lag']}")
        print(f"Corrélation: {result['optimal_correlation']:.4f}")
        print(f"Force: {result['correlation_strength']}")
        print(f"Interprétation: {result['interpretation']}")
    else:
        print(f"Erreur: {result['error']}")
