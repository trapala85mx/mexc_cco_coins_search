# mexc_cco_coins_search

Script para escanear las monedas del exchange Mexc en su sección de futuros para cumplir los requisitos para las CCO o CCD.

## Requisitos
- Tener instalado python 3.10+
- Instalar requirements.txt. Para esto, recomiendo crear un ambiente virtual
  - Activar ambiente virtual si se creo
  - En Linux / WSL2
```shell
pip install requirements.txt
```
## Ejeución / Uso
  Para poder usar el script se debe ejecutar el siguiente comando donde _capital_ es lo que se tiene en la cuenta de futuros para poder calcular el margen mínimo necesario
```shell
python app.py -c capital
```
Otras opciones que se puede colocar son:
```shell
python app.py -c capital -s estrategia -l apalancamiento -k velas -v volatilidad
```
donde:
  - __s__ -> es la estrategia y solo acepta "cco" o "ccd" para calcular ya sea el 0.1% o 0.05% de margen mínimo. Por default está en "ccd"
  - __l__ -> es el apalancamiento mínimo que buscamos. Por default está en 100 y debe ser un número entero
  - __k__ -> es la cantidad de velas que revisará para calcular el promedio de movimiento. Es un número entero. Por default 5.
  - __v__ -> es la volatilidad promedio que buscamos de las velas analizadas. Es un número decimal. Por default 1. El número hace referencia al porcentaje, por ejemplo: 1 es 1%.