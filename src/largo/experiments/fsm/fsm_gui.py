"""
GUI elements for FSM experiments.
"""
from nspyre import ExperimentWidget, HeatMapWidget, DataSink
from pyqtgraph import SpinBox
from pyqtgraph.Qt import QtWidgets
import logging
import numpy as np
import time


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
    """Widget for displaying FSM scan data as a 2D heatmap."""
    
    def __init__(self, parent=None):

        super().__init__(
            parent=parent,
            title='FSM Scan',
            btm_label='X Position (µm)', 
            lft_label='Y Position (µm)', 
        )
        
        # Create dataset selection box/button
        self._create_controls()
        
        # Initialize attributes
        self.sink = None
        self.current_dataset = None
        self._is_connecting = False
        
        # Set size, scaling, padding
        # self.setMinimumSize(800, 800) 
        # self.image_view.view.setAspectLocked(True)
        self.image_view.view.enableAutoRange()
        
        # Scale ticks to microns
        self.image_view.view.getAxis('bottom').setScale(1e6) 
        self.image_view.view.getAxis('left').setScale(1e6)   
        
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding
        )
        
        # Switch to default dataset
        self.switch_dataset('fsm')

    def _create_controls(self):
        """Create and layout the dataset selection controls."""
        # Create control widgets
        control_widget = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        label = QtWidgets.QLabel("Dataset:")
        control_layout.addWidget(label)
        
        self.dataset_input = QtWidgets.QLineEdit("fsm")
        control_layout.addWidget(self.dataset_input)
        
        switch_btn = QtWidgets.QPushButton("Switch Dataset")
        switch_btn.clicked.connect(self._on_switch_clicked)
        control_layout.addWidget(switch_btn)
        

        control_layout.addStretch()

        control_widget.setLayout(control_layout)
        
        # Insert at the top of the main layout
        self.layout.insertWidget(0, control_widget)

    def _on_switch_clicked(self):
        """Handle Switch Sink button clicks."""
        new_dataset = self.dataset_input.text().strip()
        self.switch_dataset(new_dataset)

    def switch_dataset(self, dataset_name: str):
        """Switch to a new dataset."""
        self._is_connecting = True  # Set flag when starting connection
        
        # Stop existing sink if any
        if self.sink is not None:
            try:
                self.sink.stop()
                self.sink = None
            except Exception as e:
                _logger.error(f"Error stopping previous sink: {e}")

        if not dataset_name:
            self.current_dataset = None
            self._is_connecting = False 
            return

        # Create new sink
        try:
            self.sink = DataSink(dataset_name)
            self.sink.start()
            
            # Wait for connection (with timeout)
            start_time = time.time()
            while not self.sink.is_running and (time.time() - start_time) < 5.0:
                time.sleep(0.1)
            
            if not self.sink.is_running:
                _logger.warning(f"Timeout waiting for sink to connect to {dataset_name}")
                self.sink = None
                self.current_dataset = None
                self._is_connecting = False 
                return
                
            self.current_dataset = dataset_name
            _logger.info(f"Switched to dataset: {dataset_name}")
            
        except Exception as e:
            _logger.error(f"Error connecting to dataset {dataset_name}: {e}")
            self.current_dataset = None
            self.sink = None
        finally:
            self._is_connecting = False  # Always clear flag when done

    def set_data(self, x_steps, y_steps, data):
        """Override set_data to ensure proper scaling and centering"""
        # Convert position data to meters for display
        x_steps = np.array(x_steps)
        y_steps = np.array(y_steps)
        
        # Set the data with proper scaling
        super().set_data(x_steps, y_steps, data)
        
        # Auto-range on first data
        if not hasattr(self, '_first_data_shown'):
            self.image_view.view.autoRange()
            x_range = [x_steps.min(), x_steps.max()]
            y_range = [y_steps.min(), y_steps.max()]
            self.image_view.view.setRange(xRange=x_range, yRange=y_range, padding=0.1)
            self._first_data_shown = True

    def update(self):
        """Update the heatmap with new data."""
        # Skip updates while connecting
        if self._is_connecting:
            return
            
        if self.sink is None or not self.sink.is_running:
            return

        try:
            # Try to get new data
            self.sink.pop(timeout=0.1)
            
            # Get the datasets
            datasets = getattr(self.sink, 'datasets', {})
            if not datasets:
                return

            # Get latest frame data
            raw_data = datasets.get('raw', [])
            x_steps = datasets.get('xSteps', [])
            y_steps = datasets.get('ySteps', [])

            # Check if we have valid data arrays
            if (len(raw_data) == 0 or len(x_steps) == 0 or len(y_steps) == 0):
                return

            # Get the latest frame
            latest_frame = raw_data[-1]
            
            # Check if frame contains any valid data (not all NaN)
            if np.all(np.isnan(latest_frame)):
                return
                
            # Update the heatmap
            self.set_data(x_steps, y_steps, latest_frame)

        except TimeoutError:
            # No new data available
            pass
        except Exception as e:
            _logger.error(f"Error updating heatmap: {e}")

    def teardown(self):
        """Clean up resources."""
        if self.sink is not None:
            try:
                self.sink.stop()
                self.sink = None
            except Exception as e:
                _logger.error(f"Error in teardown: {e}")
