# PyFMlab

## Introduction
PyFMlab is a python based open-source software package designed to extract viscoelastic parameters from both conventional force-distance curves and microrheology measurements obtained via Atomic Force Microscopy (AFM).


To enhance readability, maintainability, and reusability, PyFMLab is organized into three self-contained Python libraries

- PyFMReader -  Data import, export and preprocessing of AFM; [Go to PyFMReader](PyFMReader_DyNaMo)
- PyFMRheo -  Data analysis tools and routines; [Go to PyFMRheo](PyFMRheo_DyNaMo)
- PyFMGUI -  A graphical user interface; [Go to PyFMGUI](PyFMGUI_DyNaMo)


If you have any ideas, comments, or run into any issues, feel free to open an issue on this repository: 

https://github.com/DyNaMo-INSERM/PyFMlab_DyNaMo/issues

Alternatively, you can reach out to us at yogesh.saravanan@inserm.fr ou felix.rico@inserm.fr.
We’re always happy to hear from you!


## Documentation

Full usage instructions, examples, and model descriptions are available in the [Wiki](https://github.com/DyNaMo-INSERM/PyFMlab_DyNaMo/wiki).

---

## Run software
A zip containing the frozen GUI application can be found and downloaded here:

https://zenodo.org/records/16942211

To run, extract the contents of the .zip and run the main.exe file.

## To Setup and run from source
- Clone the repository
```
git clone  https://github.com/DyNaMo-INSERM/PyFMlab_DyNaMo.git
```
- Create an environment with python 3.9
```
conda create -n yourenvname python=3.9 
conda activate yourenvname
```

- Install the dependencies from requirements.txt
```
pip install -r ./PyFMlab_DyNaMo/PyFMGUI_DyNaMo/requirements.txt
```
- Installing an **editable** version of PyFMReader and PyFMRheo from a local source
```
python3 -m pip install -e ./PyFMlab_DyNaMo/PyFMReader_DyNaMo
python3 -m pip install -e ./PyFMlab_DyNaMo/PyFMRheo_DyNaMo
```

- Launch the GUI 
```
python ./PyFMlab_DyNaMo/PyFMGUI_DyNaMo/src/main.py
```

## Generate executables
If you wish to do any changes to the code and freeze them. You can use PyInstaller and compile an executable for the GUI (OS/platform specific).
```
pyinstaller --onefile --name "name_your_executable" --windowed ./PyFMLAB/PyFMGUI/src/main.py
```

## To Do
- Generate documentation with examples and tutorials
- Improve multiprocessing
- Improve tree control for files (allow to load multiple directories at once and assign folder as group)
- Allow to save analysis sessions and load them after
- Improve error handling and logging

## Acknowledgements
This project has received funding by the H2020 European Union’s Horizon 2020 research and innovation program under the Marie Sklodowska-Curie (grant agreement No 812772) and from the European Research Council (ERC, grant agreement No 772257).


## Citation

If you use PyFMLab, please cite:

López-Alonso J, Eroles M, Janel S et al. PyFMLab: Open-source software for atomic force microscopy microrheology data analysis . Open Res Europe 2024, 3:187 
(https://doi.org/10.12688/openreseurope.16550.2)

