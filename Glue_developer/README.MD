#Notas de uso
# ---------------Construcción de la imagen personalizada:
docker build --platform linux/amd64 -t glue5-custom .
# ----------------Ejecución de un contenedor interactivo:
docker run --platform linux/amd64 -it --rm --name glue5 -v C:/Users/luisH/Documents/glue-workspace:/home/glue_user workspace glue5-custom
# ----------------Ejecución de un contenedor interactivo, enlaza volumen desde donde se ejecuta:
docker run --platform linux/amd64 -it --rm --name glue5 -v "${PWD}:/home/glue_user/workspace" glue5-custom