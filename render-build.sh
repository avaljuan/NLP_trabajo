#!/usr/bin/env bash
# Detener el proceso si ocurre un error
set -o errexit

STORAGE_DIR=/opt/render/project/.render

if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "...Descargando Google Chrome en la nube"
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  
  # Descargamos el instalador de Linux y lo extraemos en nuestra carpeta privada
  wget -P ./ https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x ./google-chrome-stable_current_amd64.deb $STORAGE_DIR/chrome
  rm ./google-chrome-stable_current_amd64.deb
  
  # Volvemos a la carpeta del proyecto
  cd $HOME/project/src 
else
  echo "...Google Chrome ya está instalado en la caché"
fi

# Por último, instalamos las librerías de Python
pip install -r requirements.txt
