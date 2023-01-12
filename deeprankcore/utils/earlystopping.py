from typing import Optional, Callable
import numpy as np


class EarlyStopping:
    def __init__( # pylint: disable=too-many-arguments
        self,
        patience: int = 10,
        delta: Optional[float] = None,
        maxgap: Optional[float] = None,
        verbose: bool = True,
        trace_func: Callable = print,
    ):
        """
        Terminate training if validation loss doesn't improve after a given patience or if a maximum gap between validation and training loss is reached.

        Args:
            patience (int): How long to wait after last time validation loss improved.
                Default: 10
            
            delta (float, optional): Minimum change in the monitored quantity to qualify as an improvement.
                Default: None
            
            maxgap (float, optional): Maximum difference between between training and validation loss.
                Default: None
            
            verbose (bool): If True, prints a message for each validation loss improvement. 
                Default: True
            
            trace_func (function): Function used for recording EarlyStopping status.
                Default: print            
        """

        self.patience = patience
        if delta is None:
            self.delta = 0
        else:
            self.delta = delta
        self.maxgap = maxgap
        self.verbose = verbose
        self.trace_func = trace_func

        self.early_stop = False
        self.counter = 0
        self.best_score = None
        self.val_loss_min = np.Inf

    def __call__(self, epoch, val_loss, train_loss=None):
        score = -val_loss
        
        # initialize
        if self.best_score is None:
            self.best_score = score
        
        # check patience
        elif score < self.best_score + self.delta:
            self.counter += 1
            if self.verbose:
                if self.delta:
                    extra_trace = f'more than {self.delta} '
                else:
                    extra_trace = ''
                self.trace_func(f'Validation loss did not decrease {extra_trace}({self.val_loss_min:.6f} --> {val_loss:.6f}). '+
                                f'EarlyStopping counter: {self.counter} out of {self.patience}')
            if self.counter >= self.patience:
                self.trace_func(f'EarlyStopping activated at epoch # {epoch} because patience of {self.patience} has been reached.')
                self.early_stop = True
        else:
            if self.verbose:
                self.trace_func(f'Validation loss decreased ({self.val_loss_min:.6f} --> {val_loss:.6f}).')
                self.val_loss_min = val_loss
            self.best_score = score
            self.counter = 0
        
        # check maxgap
        if self.maxgap and epoch > 0:
            if train_loss is None:
                raise ValueError("Cannot compute gap because no train_loss is provided to EarlyStopping.")
            gap = val_loss - train_loss
            if gap > self.maxgap:
                self.trace_func(f'EarlyStopping activated at epoch # {epoch} due to overfitting. ' +
                                f'The difference between validation and training loss of {gap} exceeds the maximum allowed ({self.maxgap})')
                self.early_stop = True
                



# This module is modified from https://github.com/Bjarten/early-stopping-pytorch, under the following license:


# MIT License

# Copyright (c) 2018 Bjarte Mehus Sunde

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
