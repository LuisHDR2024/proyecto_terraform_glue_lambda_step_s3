import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def resumen_exploratorio(df: pd.DataFrame, decimales: int = 2) -> pd.DataFrame:
    
    resumen = []
    total_filas = len(df)
    
    for col in df.columns:
        serie = df[col]
        
        nulos = serie.isna().sum()
        porcentaje_nulos = round((nulos / total_filas) * 100, decimales)
        
        es_booleana = pd.api.types.is_bool_dtype(serie)
        es_numerica = pd.api.types.is_numeric_dtype(serie) and not es_booleana

        if es_numerica:
            media     = round(serie.mean(), decimales)
            mediana   = round(serie.median(), decimales)
            asimetria = round(serie.skew(), decimales)
            kurtosis  = round(serie.kurt(), decimales)
            desv_std  = round(serie.std(), decimales)
            minimo    = round(serie.min(), decimales)
            maximo    = round(serie.max(), decimales)
        else:
            media     = np.nan
            mediana   = np.nan
            asimetria = np.nan
            kurtosis  = np.nan
            desv_std  = np.nan
            minimo    = np.nan
            maximo    = np.nan
        
        moda = serie.mode().iloc[0] if not serie.mode().empty else np.nan
        
        fila = {
            "columna"  : col,
            "dtype"    : serie.dtype,
            "count"    : serie.count(),
            "nulos"    : nulos,
            "%_nulos"  : porcentaje_nulos,
            "media"    : media,
            "mediana"  : mediana,
            "moda"     : moda,
            "min"      : minimo,
            "max"      : maximo,
            "asimetria": asimetria,
            "kurtosis" : kurtosis,
            "desv_std" : desv_std
        }
        
        resumen.append(fila)
    
    return pd.DataFrame(resumen)

def matriz_correlacion(df: pd.DataFrame, umbral: float):
    # Solo columnas numéricas y no booleanas
    df_num = df.select_dtypes(include='number').loc[
        :, ~df.select_dtypes(include='number').apply(pd.api.types.is_bool_dtype)
    ]
    corr = df_num.corr().round(2)
    filtered_corr = corr.where(np.abs(corr) >= umbral)
    return filtered_corr

def graficar_dispersion(df, path='graficos.png'):
    # Solo columnas numéricas y no booleanas
    columnas = [
        col for col in df.columns
        if pd.api.types.is_numeric_dtype(df[col])
        and not pd.api.types.is_bool_dtype(df[col])
    ]
    n = len(columnas)

    if n == 0:
        print("No hay variables numéricas para graficar.")
        return

    fig, axes = plt.subplots(1, n, figsize=(6 * n, 5))
    
    if n == 1:
        axes = [axes]
    
    for ax, col in zip(axes, columnas):
        ax.scatter(df.index, df[col], alpha=0.7, edgecolors='k', linewidths=0.5)
        ax.set_title(f'Dispersión: {col}')
        ax.set_xlabel('Índice')
        ax.set_ylabel(col)
        ax.grid(True, linestyle='--', alpha=0.5)
    
    plt.suptitle('Gráficos de Dispersión', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'Gráfico guardado en: {path}')

def graficar_dispersion_objetivo(df, objetivo, variables=None, path='graficos.png'):
    # Solo columnas numéricas y no booleanas, excluyendo el objetivo
    if variables is None:
        variables = [
            col for col in df.columns
            if col != objetivo
            and pd.api.types.is_numeric_dtype(df[col])
            and not pd.api.types.is_bool_dtype(df[col])
        ]

    if len(variables) == 0:
        print("No hay variables numéricas para graficar.")
        return

    n = len(variables)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 5))
    
    if n == 1:
        axes = [axes]
    
    for ax, col in zip(axes, variables):
        ax.scatter(df[col], df[objetivo], alpha=0.7, edgecolors='k', linewidths=0.5)
        ax.set_title(f'{col} vs {objetivo}')
        ax.set_xlabel(col)
        ax.set_ylabel(objetivo)
        ax.grid(True, linestyle='--', alpha=0.5)
    
    plt.suptitle(f'Dispersión vs {objetivo}', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'Gráfico guardado en: {path}')

def generar_histogramas(df, output_path, nombre_archivo="histogramas.png", bins=30):

    if df.empty:
        print("El DataFrame está vacío.")
        return None

    # Solo columnas numéricas y no booleanas
    columnas_numericas = [
        col for col in df.columns
        if pd.api.types.is_numeric_dtype(df[col])
        and not pd.api.types.is_bool_dtype(df[col])
    ]
    n = len(columnas_numericas)

    if n == 0:
        print("No hay variables numéricas en el DataFrame.")
        return None

    os.makedirs(output_path, exist_ok=True)

    fig, axes = plt.subplots(1, n, figsize=(5 * n, 4))

    if n == 1:
        axes = [axes]

    for ax, col in zip(axes, columnas_numericas):
        ax.hist(df[col].dropna(), bins=bins, edgecolor="white")
        ax.set_title(col)
        ax.set_xlabel(col)
        ax.set_ylabel("Frecuencia")

    plt.tight_layout()

    file_path = os.path.join(output_path, nombre_archivo)
    plt.savefig(file_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"Histograma guardado en: {file_path}")
    return file_path

def generar_barras_categoricas(df, output_path, nombre_archivo="barras_categoricas.png", top_n=10):
    """
    Genera una sola figura con gráficos de barras para todas las variables
    categóricas u object en una línea horizontal y la guarda como imagen.

    Parámetros:
    - df            : pandas.DataFrame
    - output_path   : ruta donde se guardará la imagen
    - nombre_archivo: nombre del archivo de salida
    - top_n         : máximo de categorías a mostrar por variable (las más frecuentes)

    Retorna:
    - file_path: ruta completa del archivo guardado, o None si no hay columnas categóricas
    """

    if df.empty:
        print("El DataFrame está vacío.")
        return None

    columnas_categoricas = [
        col for col in df.columns
        if df[col].dtype == 'object'
        or str(df[col].dtype) == 'category'
        and not pd.api.types.is_bool_dtype(df[col])
    ]
    n = len(columnas_categoricas)

    if n == 0:
        print("No hay variables categóricas en el DataFrame.")
        return None

    os.makedirs(output_path, exist_ok=True)

    fig, axes = plt.subplots(1, n, figsize=(5 * n, 4))

    if n == 1:
        axes = [axes]

    for ax, col in zip(axes, columnas_categoricas):
        conteo = df[col].value_counts().head(top_n)
        ax.bar(conteo.index.astype(str), conteo.values, edgecolor="white")
        ax.set_title(col)
        ax.set_xlabel(col)
        ax.set_ylabel("Frecuencia")
        ax.tick_params(axis='x', rotation=45)

    plt.tight_layout()

    file_path = os.path.join(output_path, nombre_archivo)
    plt.savefig(file_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"Gráfico de barras guardado en: {file_path}")
    return file_path