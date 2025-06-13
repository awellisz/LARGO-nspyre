"""
This is a basic Fsm Scan Application

Copyright (c) May 2023, C. Egerstrom
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.

Modified by I. Hammock (?)
Modified by A. Wellisz June 2025
"""
import logging
from pathlib import Path

import numpy as np
from nspyre import DataSource, StreamingList, experiment_widget_process_queue, nspyre_init_logger

from largo.drivers.insmgr import MyInstrumentManager
from rpyc.utils.classic import obtain

_HERE = Path(__file__).parent
_logger = logging.getLogger(__name__)


class FSMScanMeasurement:
    """Fast-Steering Mirror (FSM) photoluminescence scan measurement."""

    def __init__(self, queue_to_exp=None, queue_from_exp=None):
        self.queue_to_exp = queue_to_exp
        self.queue_from_exp = queue_from_exp

    def __enter__(self):
        # separate logging for GUI vs. experiment
        nspyre_init_logger(
            log_level=logging.INFO,
            log_path=_HERE / '../logs',
            log_path_level=logging.DEBUG,
            prefix=Path(__file__).stem,
            file_size=10_000_000,
        )
        _logger.info('Created FSMScanMeasurement instance.')

    def __exit__(self):
        # Experiment teardown
        _logger.info('Destroyed FSMScanMeasurement instance.')

    def fsm_scan(
        self,
        dataset: str,
        x_center: float = 0,
        y_center: float = 0,
        x_range: float = 10e-6,
        y_range: float = 10e-6,
        x_num_points: int = 200,
        y_num_points: int = 200,
        collects_per_pt: int = 50,
        shots: int = 1,
        acq_rate: float = 100,
    ):
        """Run an FSM (fast-steering mirror) PL (photoluminescence) scan over a specified area.
        Args:  
            dataset: name of the dataset to push data to
            x_center: X position of center of scan (in um) 
            y_center: Y position of center of scan (in um)
            x_range: how far to sweep scan in X (from top to bottom, in um)
            y_range: how far to sweep scan in Y (from left to right, in um)
            x_num_points: number of points to cover the x_range
            y_num_points: number of points to cover the y_range
            collects_per_pt: How many reads to do at each (x,y) point. Default: 100
            shots: How many times to repeat the scan. Default: 1 
            acq_rate: The rate at which the FSM is acquiring data, in Hz.
        """
        # connect to the instrument server
        # connect to the data server and create a data set, or connect to an
        # existing one with the same name if it was created earlier.
        with MyInstrumentManager() as mgr, DataSource(dataset) as fsm_scan_data:
            # compute X/Y steps to take
            x_steps = np.linspace(
                x_center - x_range/2,
                x_center + x_range/2,
                x_num_points
            )
            y_steps = np.linspace(
                y_center - y_range/2,
                y_center + y_range/2,
                y_num_points
            )

            # prepare streaming containers
            raw_sweeps = StreamingList()
            avg_sweeps = StreamingList()

            # configure FSM
            fsm = mgr.fsm_driver
            fsm.setAcqRate(acq_rate)
            scan_rate = acq_rate / (collects_per_pt * x_num_points)
            _logger.info(f"Scan rate: {scan_rate:.2f} Hz (Acq rate: {acq_rate} Hz)")
            if scan_rate > 200:
                _logger.warning("Scan rate > 200 Hz, aborting scan.")
                return

            # run shots
            for s in range(shots):
                _logger.info(f"Beginning FSM scan shot {s+1}/{shots}")

                # initialize empty frames
                raw_sweeps.append(np.full((y_num_points, x_num_points), np.nan))
                avg_sweeps.append(np.full((y_num_points, x_num_points), np.nan))

                for j, y in enumerate(y_steps):
                    # snake: even rows L->R, odd rows R->L
                    if j % 2 == 0:
                        start = {'x': x_center - x_range/2, 'y': y}
                        end   = {'x': x_center + x_range/2, 'y': y}
                    else:
                        start = {'x': x_center + x_range/2, 'y': y}
                        end   = {'x': x_center - x_range/2, 'y': y}

                    # acquire line
                    line_data = obtain(
                        fsm.line_scan(start, end, x_num_points, collects_per_pt)
                    )
                    # reverse on odd rows
                    if j % 2 == 1:
                        line_data = line_data[::-1]

                    # update raw and notify
                    current_raw = raw_sweeps[-1]
                    current_raw[j, :] = line_data
                    raw_sweeps.updated_item(-1)

                    # update running average and notify
                    current_avg = avg_sweeps[-1]
                    current_avg[j, :] = (current_avg[j, :] * s + line_data) / (s + 1)
                    avg_sweeps.updated_item(-1)

                    # push to DataSource
                    fsm_scan_data.push({
                        'params': {
                            'center': (x_center, y_center),
                            'range': (x_range, y_range),
                            'points': (x_num_points, y_num_points),
                            'collects_per_pt': collects_per_pt,
                            'shot': s+1,
                            'shots': shots,
                            'acq_rate': acq_rate,
                        },
                        'title': 'FSM Scan',
                        'xLabel': 'X Position',
                        'yLabel': 'Y Position',
                        'zLabel': 'Counts/s',
                        'datasets': {
                            'raw': raw_sweeps,
                            'avg': avg_sweeps,
                            'xSteps': x_steps,
                            'ySteps': y_steps,
                        }
                    })

                    # handle GUI stop
                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        return

                # return FSM to center
                fsm.move({'x': x_center, 'y': y_center})
                _logger.info(f"Shot {s+1} complete, FSM returned to (0,0).")

            _logger.info("FSM scan complete.")


if __name__ == '__main__':
    # For testing
    with FSMScanMeasurement() as exp:
        exp.fsm_scan(
            dataset='fsm_test',
            x_center=0.0,
            y_center=0.0,
            x_range=10e-6,
            y_range=10e-6,
            x_num_points=100,
            y_num_points=100,
            collects_per_pt=50,
            shots=2,
            acq_rate=100
        )
