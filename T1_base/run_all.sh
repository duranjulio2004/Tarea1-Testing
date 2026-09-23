#!/bin/bash

# Carpetas base
BASE_DIR="Public_Proyects"
OUTPUT_BASE="Results"

# Definir los proyectos y sus respectivos archivos usando un diccionario (array asociativo)
declare -A projects
projects[blackjack]="base.py dealer.py judger.py"
projects[gin_rummy]="base.py action_event.py dealer.py"
projects[mahjong]="player.py dealer.py game.py"
projects[stock4]="tabeformat.py structure.py validate.py"
projects[svm]="base.py svm.py"
projects[tree]="base.py tree.py"
projects[fuzzywuzzy]="fuzz.py string_processing.py StringMatcher.py utils.py"

echo "=========================================================="
echo "Iniciando la ejecución del Agente para proyectos públicos"
echo "=========================================================="

# Iterar sobre cada proyecto
for project in "${!projects[@]}"; do
    # Iterar sobre cada archivo del proyecto actual
    for file in ${projects[$project]}; do
        
        # Quitar la extensión .py para nombrar la carpeta de salida
        class_name="${file%.py}"
        
        # Construir el filepath y la ruta de salida
        filepath="$BASE_DIR/$project/$file"
        output_folder="$OUTPUT_BASE/$project/$class_name"
        
        echo "-> Ejecutando agente para: $filepath"
        
        # Crear la carpeta de salida por si el agente no lo hace automáticamente
        mkdir -p "$output_folder"
        
        # Ejecutar el agente con 2 parámetros: filepath y output_folder
        python3 agent.py "$filepath" "$output_folder"
        
        # Pausa de 5 segundos para respetar los límites de la API de Gemini (cambiar si es necesario)
        sleep 5
        
    done
done

echo "=========================================================="
echo "¡Ejecución finalizada! Revisa la carpeta '$OUTPUT_BASE'"
echo "=========================================================="