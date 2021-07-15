# Ariadne Dashboard

![alt text](https://raw.githubusercontent.com/ilVecc/ariadne_python_plotter/main/images_doc/evolution_3d_plot.png)

## Utility for plotting and interactive visualization of evolutions and automaton of Ariadne systems.




### Objectives:
Main purpose of this project is to implement a way to visualize polytopes (hybrid enclosures) and graph automatons produced by python-binded version of [Ariadne](https://github.com/ariadne-cps/ariadne) C++ library. This extension of Ariadne will be implemented employing mainly the libraries:
- [plotly](https://plotly.com/) - plotting of evolutions
- [dash](https://dash.plotly.com/) - dashboard interface
- [dash cytoscape](https://dash.plotly.com/cytoscape) - plot of automatons

A serialization tool in [YAML](https://yaml.org/) will also be included. This will permit to export results in a more general way.
At the moment since there are some incompatibilities with MacOS users, this feature is not included yet.

### Installation guide:
- Install [Ariadne](https://www.ariadne-cps.org/installation/) (pyariadne included)
- clone this repo and run:
```
python -m pip install -r requirements.txt
```

## Project for Discrete Hybrid Systems exam @ University of Verona

### People involved:
Students:
- Sebastiano Fregnan - sebastiano.fregnan@studenti.univr.it
- Luigi Palladino - luigi.palladino@studenti.univr.it

Professors:
- Luca Geretti - luca.geretti@univr.it
- Tiziano Villa - tiziano.villa@univr.it