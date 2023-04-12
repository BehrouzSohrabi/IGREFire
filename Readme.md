# IGREFire
**Integrated Grid Resilience Evaluation Framework against wildFIREs**

You can read our published paper on the impact of wildfires on power grids [here](https://....).

IGREFire is an Integrated Grid Resilience Evaluation Framework against wildFIREs. It is a Python-based tool that helps to evaluate the impact of wildfires on power grids and assess their resilience.

## Installation
1. Clone the repository to your local machine using the command:<br>
    `git clone https://github.com/BehrouzSohrabi/IGREFire.git`
2. Navigate to the cloned directory:<br>`cd IGREFire`<br>
If you want install it on a separate virtual environment:
    1. Aun the following command:<br>`python -m venv env`
    2. Activate the new environment: 
        - Windows: `env\Scripts\activate.bat`
        - Mac/Linux: `source env/bin/activate`
3. Install the required Python packages:<br>`pip install -r requirements.txt`


## Usage
1. Open the command prompt or terminal.
2. Navigate to the IGREFire directory: `cd IGREFire`
3. Run the command `python main.py` to launch the GUI.
4. Fill in the necessary input fields in the GUI with the required data.
5. Click the "Run Analysis" button to start the analysis process.
6. The progress bar will show the progress of the analysis.
7. The results will be displayed using a visualization tool.


## Contributing
If you want to contribute to IGREFire, please follow the below steps:

1. Fork the IGREFire repository.
2. Create a new branch with a descriptive name:<br>`git checkout -b feature/new-feature or git checkout -b fix/bug-fix`
3. Make your changes and commit them:<br>`git commit -m "Add a new feature" or git commit -m "Fix a bug"`
4. Push the changes to your forked repository:<br>`git push origin feature/new-feature or git push origin fix/bug-fix`.`
5. Open a pull request to the IGREFire repository.


## Citation and Authors
IGREFire was developed by Behrouz Sohrabi as part of KLab's research efforts. If you use IGREFire in your research work, please cite it using the following BibTeX entry:

### Article Paper
    @article{sohrabi2023,
        author = {Sohrabi, Behrouz and Khodaei, Amin and ...},
        title = {The Impact of Wildfires on Power Grids},
        journal = {Journal of Environmental Science},
        volume = {50},
        number = {2},
        pages = {123-137},
        year = {2023},
        doi = {10.12345/jsenvsci.2023.50.2.123}
    }

### Software
    @software{IGREFire,
        author = {[Your Name]},
        title = {IGREFire: Integrated Grid Resilience Evaluation Framework against wildFIREs},
        url = {https://github.com/BehrouzSohrabi/IGREFire},
        version = {0.9.1},
        date = {2023-04-16},
    }


## Authors
- Behrouz Sohrabi - University of Denver
- Amin Khodaei - University of Denver
- Other Authors - Affiliation

## Dependencies
- [PyPower]() - version 1.2.3
- [FARSITE]() - version a.b.c

## References
- [Paper Title]() - Author 1 et al., Journal Name, Year.
- [Book Title]() - Author 1 et al., Publisher, Year.

## License
This project is licensed under the MIT License - see the LICENSE file for details.