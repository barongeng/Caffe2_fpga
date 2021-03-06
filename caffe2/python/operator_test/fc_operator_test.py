from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from caffe2.proto import caffe2_pb2
from caffe2.python import core
from hypothesis import assume, given, settings
import caffe2.python.hypothesis_test_util as hu
import hypothesis.strategies as st
import numpy as np


class TestFcOperator(hu.HypothesisTestCase):

    @settings(max_examples=50)
    @given(n=st.integers(1, 5),
           m=st.integers(0, 5),
           k=st.integers(1, 5),
           multi_dim=st.sampled_from([True, False]),
           dtype=st.sampled_from([np.float32, np.float16]),
           engine=st.sampled_from(['', 'TENSORCORE']),
           **hu.gcs)
    def test_fc(self, n, m, k, multi_dim, dtype, engine, gc, dc):
        if dtype == np.float16:
            # fp16 only supported with CUDA
            assume(gc.device_type == caffe2_pb2.CUDA)
            dc = [d for d in dc if d.device_type == caffe2_pb2.CUDA]

        if engine == 'TENSORCORE':
            # TensorCore only makes sense with CUDA
            assume(gc.device_type == caffe2_pb2.CUDA)
            # ensures TensorCore kernels can be called
            m *= 8
            k *= 8
            n *= 8

        X = np.random.rand(m, k).astype(dtype) - 0.5
        if multi_dim:
            W = np.random.rand(n, k, 1, 1).astype(dtype) - 0.5
        else:
            W = np.random.rand(n, k).astype(dtype) - 0.5
        b = np.random.rand(n).astype(dtype) - 0.5

        def fc_op(X, W, b):
            return [np.dot(X, W.reshape(n, k).transpose()) + b.reshape(n)]

        op = core.CreateOperator(
            'FC',
            ['X', 'W', 'b'],
            'out',
            engine=engine,
        )

        # Check against numpy reference
        self.assertReferenceChecks(
            device_option=gc,
            op=op,
            inputs=[X, W, b],
            reference=fc_op,
        )
        # Check over multiple devices
        self.assertDeviceChecks(dc, op, [X, W, b], [0])

        # Gradient checks
        threshold = 0.5 if dtype == np.float16 else 0.005
        stepsize = 0.5 if dtype == np.float16 else 0.05
        self.assertGradientChecks(gc, op, [X, W, b], 0, [0],
                                  threshold=threshold, stepsize=stepsize)
        self.assertGradientChecks(gc, op, [X, W, b], 1, [0],
                                  threshold=threshold, stepsize=stepsize)
        self.assertGradientChecks(gc, op, [X, W, b], 2, [0],
                                  threshold=threshold, stepsize=stepsize)


if __name__ == "__main__":
    import unittest
    unittest.main()
