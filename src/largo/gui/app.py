#!/usr/bin/env python
"""
This is an example script that demonstrates the basic functionality of nspyre.
"""
import logging
from pathlib import Path

import nspyre.gui.widgets.save
import nspyre.gui.widgets.load
import nspyre.gui.widgets.flex_line_plot
# import nspyre.gui.widgets.subsystem
from nspyre import MainWidget
from nspyre import MainWidgetItem
from nspyre import nspyre_init_logger
from nspyre import nspyreApp

# in order for dynamic reloading of code to work, you must pass the specifc
# module containing your class to MainWidgetItem, since the python reload()
# function does not recursively reload modules
import largo.gui.elements
import largo.experiments.fsm.fsm_gui as fsmgui

from largo.drivers.insmgr import MyInstrumentManager


_HERE = Path(__file__).parent

def main():
    # Log to the console as well as a file inside the logs folder.
    nspyre_init_logger(
        log_level=logging.INFO,
        log_path=_HERE / '../logs',
        log_path_level=logging.DEBUG,
        prefix=Path(__file__).stem,
        file_size=10_000_000,
    )

    with MyInstrumentManager() as insmgr:
        # Create Qt application and apply nspyre visual settings.
        app = nspyreApp()

        # Create the GUI.
        main_widget = MainWidget(
            {
                'ODMR': MainWidgetItem(largo.gui.elements, 'ODMRWidget', stretch=(1, 1)),
                'FSM': {
                    'FSM Scan Exp': MainWidgetItem(fsmgui, 'FSMScanWidget', stretch = (1,1)),
                    'FSM Scan Image': MainWidgetItem(fsmgui, 'FSMHeatmap', stretch=(1,1))
                },
                # 'Subsystems': MainWidgetItem(nspyre.gui.widgets.subsystem, 'SubsystemsWidget', args=[insmgr.subs.subsystems], stretch=(1, 1)),
                'Plots': {
                    'FlexLinePlotDemo': MainWidgetItem(
                        largo.gui.elements,
                        'FlexLinePlotWidgetWithODMRDefaults',
                        stretch=(100, 100),
                    ),
                    'FlexLinePlot': MainWidgetItem(
                        nspyre.gui.widgets.flex_line_plot,
                        'FlexLinePlotWidget',
                        stretch=(100, 100),
                    ),
                },
                'Save': MainWidgetItem(nspyre.gui.widgets.save, 'SaveWidget', stretch=(1, 1)),
                'Load': MainWidgetItem(nspyre.gui.widgets.load, 'LoadWidget', stretch=(1, 1)),
            }
        )
        main_widget.show()

        # Run the GUI event loop.
        app.exec()


# if using the nspyre ProcessRunner, the main code must be guarded with if __name__ == '__main__':
# see https://docs.python.org/2/library/multiprocessing.html#windows
if __name__ == '__main__':
    main()
