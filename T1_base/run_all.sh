#!/bin/bash

# Carpetas base
BASE_DIR="Public_Proyects"
OUTPUT_BASE="Results"

# Proyectos y sus archivos, como "proyecto:archivo1 archivo2 ...".
# (Lista plana en vez de `declare -A`: el bash por defecto de macOS es 3.2 y no
# soporta arrays asociativos.)
projects=(
    "blackjack:base.py dealer.py judger.py"
    "gin_rummy:base.py action_event.py dealer.py"
    "mahjong:player.py dealer.py game.py"
    "stock4:tableformat.py structure.py validate.py"
    "svm:base.py svm.py"
    "tree:base.py tree.py"
    "fuzzywuzzy:fuzz.py string_processing.py StringMatcher.py utils.py"
)

# Usar el python del venv si existe
PYTHON="python3"
[ -x ".venv/bin/python" ] && PYTHON=".venv/bin/python"

echo "=========================================================="
echo "Iniciando la ejecución del Agente para proyectos públicos"
echo "=========================================================="

# Iterar sobre cada proyecto
for entry in "${projects[@]}"; do
    project="${entry%%:*}"
    # Iterar sobre cada archivo del proyecto actual
    for file in ${entry#*:}; do

        # Quitar la extensión .py para nombrar la carpeta de salida
        class_name="${file%.py}"
        
        # Construir el filepath y la ruta de salida
        filepath="$BASE_DIR/$project/$file"
        output_folder="$OUTPUT_BASE/$project/$class_name"
        
        echo "-> Ejecutando agente para: $filepath"
        
        # Crear la carpeta de salida por si el agente no lo hace automáticamente
        mkdir -p "$output_folder"
        
        # Ejecutar el agente con 2 parámetros: filepath y output_folder
        "$PYTHON" agent.py "$filepath" "$output_folder"
        
        # Pausa de 5 segundos para respetar los límites de la API de Gemini (cambiar si es necesario)
        sleep 5
        
    done
done

echo "=========================================================="
echo "¡Ejecución finalizada! Revisa la carpeta '$OUTPUT_BASE'"
echo "=========================================================="