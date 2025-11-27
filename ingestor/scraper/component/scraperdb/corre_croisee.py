"""
Module de corrélation croisée normalisée pour l'analyse crypto.
Utilise numpy.correlate pour calculer la corrélation entre volume et prix.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import mysql.connector


def get_db_connection():
    """Connexion MySQL pour Docker."""
    return mysql.connector.connect(
        host="host.docker.internal",
        user="ingestor_user",
        password="password123",
        database="ingestor"
    )


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
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT fetched_at, price, volume_24h
            FROM article
            WHERE symbol = %s
            AND price IS NOT NULL
            AND volume_24h IS NOT NULL
            ORDER BY fetched_at ASC
        """
        
        cursor.execute(query, (symbol.upper(),))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if len(rows) < 10:
            return {
                "error": f"Données insuffisantes pour {symbol} ({len(rows)} points)",
                "symbol": symbol,
                "data_points": len(rows)
            }
        
        # Créer DataFrame
        df = pd.DataFrame(rows)
        df['fetched_at'] = pd.to_datetime(df['fetched_at'])
        
        # Normalisation Z-score (comme dans ton code)
        df['price_z'] = (df['price'] - df['price'].mean()) / df['price'].std()
        df['volume_z'] = (df['volume_24h'] - df['volume_24h'].mean()) / df['volume_24h'].std()
        
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
        
    except mysql.connector.Error as e:
        return {"error": f"Erreur de base de données: {str(e)}", "symbol": symbol}
    except Exception as e:
        return {"error": f"Erreur d'analyse: {str(e)}", "symbol": symbol}


def analyze_multiple_symbols(symbols: Optional[List[str]] = None, max_lag: int = 12, limit: int = 10) -> List[Dict[str, Any]]:
    """Analyse la corrélation croisée pour plusieurs symboles."""
    try:
        if symbols is None:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT symbol, COUNT(*) as count
                FROM article
                WHERE price IS NOT NULL AND volume_24h IS NOT NULL
                GROUP BY symbol
                HAVING count > 10
                ORDER BY count DESC
                LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            symbols = [row['symbol'] for row in rows]
        
        results = []
        for symbol in symbols:
            result = analyze_symbol(symbol, max_lag)
            results.append(result)
        
        return results
        
    except mysql.connector.Error as e:
        return [{"error": f"Erreur de base de données: {str(e)}"}]
    except Exception as e:
        return [{"error": f"Erreur: {str(e)}"}]


def get_available_symbols() -> List[Dict[str, Any]]:
    """Récupère la liste des symboles disponibles pour l'analyse."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT symbol, COUNT(*) as data_points
            FROM article
            WHERE price IS NOT NULL AND volume_24h IS NOT NULL
            GROUP BY symbol
            HAVING data_points > 10
            ORDER BY data_points DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return rows
        
    except mysql.connector.Error as e:
        return [{"error": f"Erreur de base de données: {str(e)}"}]
    except Exception as e:
        return [{"error": f"Erreur: {str(e)}"}]


# Pour tester en local (hors Docker)
if __name__ == "__main__":
    from sqlalchemy import create_engine
    
    # Connexion locale pour test
    db_connection_str = 'mysql://ingestor_user:password123@localhost/ingestor'
    db_connection = create_engine(db_connection_str)
    
    df = pd.read_sql('SELECT * FROM article', con=db_connection)
    df_filtered = df.filter(items=['volume_24h', 'price', 'fetched_at', 'symbol'])
    df_filtered['fetched_at'] = pd.to_datetime(df_filtered['fetched_at'])
    df_sorted = df_filtered.sort_values(by=['fetched_at'], ascending=True)
    
    # Filtrer BTC
    df_btc = df_sorted[df_sorted['symbol'] == "BTC"].copy()
    
    # Normalisation Z-score
    df_btc['price_z'] = (df_btc['price'] - df_btc['price'].mean()) / df_btc['price'].std()
    df_btc['volume_z'] = (df_btc['volume_24h'] - df_btc['volume_24h'].mean()) / df_btc['volume_24h'].std()
    
    # Corrélation croisée
    corr = np.correlate(df_btc['price_z'], df_btc['volume_z'], mode='full')
    corre = corr / len(df_btc)
    lags = np.arange(-len(df_btc) + 1, len(df_btc))
    
    # Afficher le lag optimal
    optimal_idx = np.argmax(np.abs(corre))
    print(f"Lag optimal: {lags[optimal_idx]}")
    print(f"Corrélation: {corre[optimal_idx]:.4f}")
    print(f"Nombre de points: {len(df_btc)}")
