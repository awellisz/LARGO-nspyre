"""
This is a basic Fsm Scan Application

Copyright (c) May 2023, C. Egerstrom
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.

Modified by I. Hammock (?)
Modified by A. Wellisz June 2025
"""
import time 
import logging 
from pathlib import Path 

import numpy as np
from nspyre import DataSource
from nspyre import InstrumentGateway
from nspyre import experiment_widget_process_queue
from nspyre import StreamingList
from nspyre import nspyre_init_logger

from largo.drivers.insmgr import MyInstrumentManager

from rpyc.utils.classic import obtain


_HERE = Path(__file__).parent
_logger = logging.getLogger(__name__)

class FSMScanMeasurement:
    """FSM scan measurement"""

    def __init__(self, queue_to_exp = None, queue_from_exp = None):
        """
        Args:
            queue_to_exp: A multiprocessing Queue object used to send messages
                to the experiment from the GUI.
            queue_from_exp: A multiprocessing Queue object used to send messages
                to the GUI from the experiment.
        """
        self.queue_to_exp = queue_to_exp
        self.queue_from_exp = queue_from_exp

    def __enter__(self):
        """Perform experiment setup."""
        nspyre_init_logger(
            log_level=logging.INFO,
            log_path=_HERE / '../logs',
            log_path_level=logging.DEBUG,
            prefix=Path(__file__).stem,
            file_size=10_000_000,
        )
        _logger.info('Created FSMScanMeasurement instance.')

    def __exit__(self):
        """Perform experiment teardown."""
        _logger.info('Destroyed FSMScanMeasurement instance.')

    def fsm_scan(self, 
        dataset: str, 
        x_center: float, 
        y_center: float, 
        x_sweep_dist: float, 
        y_sweep_dist: float, 
        x_num_points: int, 
        y_num_points: int, 
        collects_per_pt: int=100, 
        shots: int = 1, 
        acq_rate = 100
    ):
        
        """Run an FSM (fast-steering mirror) PL (photoluminescence) scan over a specified area.

        Args:  
            dataset: name of the dataset to push data to
            x_center: X position of center of scan (in um) 
            y_center: Y position of center of scan (in um)
            x_sweep_dist: how far to sweep scan in X (from top to bottom, in um)
            y_sweep_dist: how far to sweep scan in Y (from left to right, in um)
            x_num_points: number of points to cover the x_sweep_dist
            y_num_points: number of points to cover the y_sweep_dist
            collects_per_pt: How many reads to do at each (x,y) point. Default: 100
            shots: How many times to repeat the scan. Default: 1 
            acq_rate: The rate at which the FSM is acquiring data, in Hz.
        """

        # connect to the instrument server
        # connect to the data server and create a data set, or connect to an
        # existing one with the same name if it was created earlier.
        with MyInstrumentManager() as mgr, DataSource(dataset) as fsm_scan_data:

            fsmScanCountsAvg = np.zeros(shape = (y_num_points, x_num_points))
            xStepsAvg = np.linspace(x_center-x_sweep_dist/2, x_center+x_sweep_dist/2, x_num_points, endpoint=True)
            yStepsAvg = np.linspace(y_center-y_sweep_dist/2, y_center+y_sweep_dist/2, y_num_points, endpoint=True)

            data = {'Avg': {'xSteps':xStepsAvg, 'ySteps':yStepsAvg, 'ScanCounts': fsmScanCountsAvg}}

            fsm = mgr.fsm_driver

            # Set the FSM acquisition rate
            fsm.setAcqRate(acq_rate)

            scan_rate = acq_rate/(collects_per_pt*x_num_points)
            print(f"Scan Rate: {scan_rate} Hz, Acquisition rate: {acq_rate} Hz")
            if fsm.getAcqRate()/(collects_per_pt*x_num_points) > 200: 
                print(f"FSM acquisition rate too high! Scan rate > 200")
                return 
            
            for s in range(shots): 
                print(f"Beginning FSM scan shot #{s}")
            
                ySteps = np.array([]) #will fill this in as data comes in
                xSteps = xStepsAvg   #not needed for sweeping, but useful for plotting later
                
                fsmScanCounts = np.zeros( (0,x_num_points) )

                for j, yStep in enumerate(yStepsAvg):

                    lineScanData = obtain(fsm.line_scan( {'y': yStep, 'x': x_center-x_sweep_dist/2}, {'y': yStep, 'x': x_center+x_sweep_dist/2},
                                                     x_num_points, collects_per_pt))
                    fsmScanCounts = np.append(fsmScanCounts, lineScanData.reshape( (1,x_num_points) ), axis=0)
                    delta = np.shape(fsmScanCountsAvg)[0]-np.shape(fsmScanCounts)[0] 
                    fsmScanCountsToAvg = fsmScanCounts

                    for r in range(delta):
                        fsmScanCountsToAvg = np.append(fsmScanCountsToAvg, np.zeros((1,x_num_points)), axis=0)

                    data['Avg']['ScanCounts'][j] = data['Avg']['ScanCounts'][j]*(s)/(s+1) + lineScanData.reshape((1,x_num_points))/(s+1)

                    #print(np.shape(fsmScanCountsToAvg))
                    
                   # print(len(fsmScanCounts[0]))
                    ySteps = np.append(ySteps, yStep)
                    #fsmScanCountsT = np.transpose(fsmScanCounts) #since stepping through x need to tranpose so the plotted data matches: data[y][x]

                    data[str(s+1)] = {'xSteps':xSteps, 'ySteps':ySteps, 'ScanCounts': fsmScanCounts}
                    fsm_scan_data.push({'params': {'CenterOfScan': (x_center, y_center), 'sweepRanges': (x_sweep_dist, y_sweep_dist), 
                        'scanPointsPerAxis': (x_num_points, y_num_points), 'collects_per_pt': collects_per_pt, 'shotCount': s+1, 'shots': shots},
                                    'title': 'FsmScan',
                                    'xLabel': 'X Position',
                                    'yLabel': 'Y Position',
                                    'zLabel': 'Counts/s',
                                    'datasets': data, 
                                    "shotnumb": s,
                    })

        fsm.move( (0,0) ) # move to (0,0) after scanning
        print('Moved to (0,0) after scanning') # I'll forget this happens without the print, but at some point I'll align with an offset FSM if I don't do this


if __name__ == '__main__':
    # Just for testing purposes!
    exp = FSMScanMeasurement()
    exp.fsm_scan(
        dataset= 'A', 
        x_center = 0, y_center = 0, 
        x_sweep_dist = 10, y_sweep_dist = 20, 
        x_num_points = 4, y_num_points =8, 
        collects_per_pt = 100, shots=10
        )
