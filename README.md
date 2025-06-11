# LARGO nspyre
Based on the [experiment template](https://github.com/nspyre-org/template) for [nspyre](https://nspyre.readthedocs.io/en/latest/).

To install, simply:
`pip install -e .`

To run the experiment, first start the instrument server:
`python src/template/drivers/inserv.py`

Run the nspyre data server:
`nspyre-dataserv`

Finally, start the experiment GUI:
`python src/template/gui/app.py`
or
`largo`

Alternatively, if on Windows, modify `launch.bat` to specify your particular Anaconda installation and conda environment name and run `src/largo/launch.bat`.