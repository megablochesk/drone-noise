# Noise and Environmental Justice in Drone Fleet Delivery Paths (ICRA2023)

By Zewei Zhou and Martim Brandao

This project's objective was to estimate issues of noise and environmental justice in drone delivery fleets.
The work is based on Zewei Zhou's MSc Project, and was published in ICRA2023.

## Citation

If you use this software in your research, please cite:
> Zewei Zhou, Martim Brandao, "Noise and Environmental Justice in Drone Fleet Delivery Paths: A Simulation-Based Audit and Algorithm for Fairer Impact Distribution", ICRA 2023.

## How to run

1. Install required packages
    ```bash
    pip install -r requirements.txt
    ```

2. Configure simulation settings. You can set the number of orders, number of drones, locations of warehouses, prioritizing factor K or P and size of cells in `src/commons/configurations.py`

3. Run the application in `src/application.py`

## Simulation

![Simulation](https://github.com/zewei94yomi/msc-project/blob/master/src/recourses/images/delivery.gif)
