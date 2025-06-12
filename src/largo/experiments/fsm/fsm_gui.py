"""
GUI elements for FSM experiments.
"""
from nspyre import ExperimentWidget, HeatMapWidget, DataSink
from pyqtgraph import SpinBox
from pyqtgraph.Qt import QtWidgets
import logging

from pyqtgraph import colormap as pgcm

import largo.experiments.fsm.fsm_scan

_logger = logging.getLogger(__name__)

class FSMScanWidget(ExperimentWidget):
    """
    Widget for starting/stopping the FSM scan experiment with specific parameters.
    """
    def __init__(self):
        params_config = {
            'x_center': {
                'display_text': 'X center',
                'widget': SpinBox(
                    value = 0e-6, 
                    suffix = 'm',
                    siPrefix = True, 
                    bounds = (-100e-6, 100e-6),
                    dec = True,
                ),
            },
            'y_center': {
                'display_text': 'Y center',
                'widget': SpinBox(
                    value = 0e-6, 
                    suffix = 'm',
                    siPrefix = True, 
                    bounds = (-100e-6, 100e-6),
                    dec = True,
                ),
            },
            'x_range': {
                'display_text': 'X range',
                'widget': SpinBox(
                    value = 10e-6, 
                    suffix = 'm',
                    siPrefix = True, 
                    bounds = (0, 200e-6),
                    dec = True,
                ),
            },
            'y_range': {
                'display_text': 'Y range',
                'widget': SpinBox(
                    value = 10e-6, 
                    suffix = 'm',
                    siPrefix = True, 
                    bounds = (0, 200e-6),
                    dec = True,
                ),
            },
            'x_num_points': {
                'display_text': 'Number of X points',
                'widget': SpinBox(value = 200, int = True, bounds = (1, None), dec = True),
            },
            'y_num_points': {
                'display_text': 'Number of Y points',
                'widget': SpinBox(value = 200, int = True, bounds = (1, None), dec = True),
            },
            'collects_per_pt': {
                'display_text': 'Collections per point',
                'widget': SpinBox(value=50, int=True, bounds=(1, None), dec=True),
            },
            'shots': {
                'display_text': 'Iterations',
                'widget': SpinBox(value=1, int=True, bounds=(1, None), dec=True),
            },
            'acq_rate': {
                'display_text': 'Acquisition rate (kHz)',
                'widget': SpinBox(value=50, int=True, bounds=(0, 200), dec=True),
            },
            'dataset': {
                'display_text': 'Data Set',
                'widget': QtWidgets.QLineEdit('fsm'),
            },
        }

        super().__init__(params_config, 
                largo.experiments.fsm.fsm_scan,
                'FSMScanMeasurement',
                'fsm_scan',
                title='FSM Scan')


class FSMHeatmap(HeatMapWidget):
    """
    Heatmap widget that dynamically displays FSM scan data from a DataSource.

    Subclasses nspyre's HeatMapWidget and streams in 'raw' frames as they arrive.
    """
    def __init__(self, dataset: str = "fsm", parent=None):
        # default dataset name
        self.dataset = dataset

        cmap = pgcm.get('viridis')  
        super().__init__(parent=parent,
                         title='FSM Heatmap',
                         btm_label='X Position',
                         lft_label='Y Position',
                         colormap=cmap)

        # add controls for selecting dataset
        self._add_dataset_controls()

        # initialize DataSink on default dataset (scaffolding appears even if no data yet)
        self.setup()

    def _add_dataset_controls(self):
        """Add a horizontal control bar for dataset input and switch button."""
        self.ctrl_layout = QtWidgets.QHBoxLayout()
        self.ds_label = QtWidgets.QLabel("Data Set:")
        self.ds_edit = QtWidgets.QLineEdit(self.dataset)
        self.switch_btn = QtWidgets.QPushButton("Switch sink")
        self.switch_btn.clicked.connect(self._switch_sink)

        self.ctrl_layout.addWidget(self.ds_label)
        self.ctrl_layout.addWidget(self.ds_edit)
        self.ctrl_layout.addWidget(self.switch_btn)

        # insert controls at the top of the existing layout
        # HeatMapWidget exposes its main layout as self.layout
        self.layout.insertLayout(0, self.ctrl_layout)

    def _switch_sink(self):
        """Stop any existing sink and switch to the newly entered dataset."""
        # stop old sink if present
        if hasattr(self, 'sink') and self.sink:
            try:
                self.sink.stop()
                _logger.info(f"Stopped DataSink for '{self.dataset}'")
            except Exception:
                _logger.exception("Error stopping previous DataSink")
            finally:
                self.sink = None

        # update dataset name and restart sink
        new_ds = self.ds_edit.text().strip()
        if new_ds:
            self.dataset = new_ds
        self.setup()

    def setup(self):
        """Initialize or reinitialize the DataSink for the current dataset."""
        # do nothing if already running
        if hasattr(self, 'sink') and self.sink:
            return
        try:
            self.sink = DataSink(self.dataset)
            self.sink.start()
            _logger.info(f"FSMHeatmap connected to dataset '{self.dataset}'")
        except Exception:
            _logger.exception(f"Failed to start DataSink for '{self.dataset}'")
            self.sink = None

    def update(self):  # runs in UpdateLoop thread
        """Poll the DataSink; when a full frame is available, update the heatmap."""
        if not hasattr(self, 'sink') or not self.sink:
            return

        # attempt to pop new data without blocking
        try:
            self.sink.pop(timeout=0)
        except TimeoutError:
            return

        dsets = getattr(self.sink, 'datasets', {}) or {}
        raw = dsets.get('raw')
        x_steps = dsets.get('xSteps')
        y_steps = dsets.get('ySteps')

        # only update if we have a complete frame
        if raw is None or x_steps is None or y_steps is None:
            return

        try:
            frame = raw[-1]
        except Exception:
            _logger.exception("Could not retrieve latest raw frame")
            return

        # pass axes + data to base class for rendering
        self.set_data(x_steps, y_steps, frame)

    def teardown(self):
        """Stop the DataSink when the widget is destroyed or dataset is switched."""
        if hasattr(self, 'sink') and self.sink:
            try:
                self.sink.stop()
                _logger.info(f"DataSink for '{self.dataset}' stopped")
            except Exception:
                _logger.exception("Error stopping DataSink in teardown")
            finally:
                self.sink = None
